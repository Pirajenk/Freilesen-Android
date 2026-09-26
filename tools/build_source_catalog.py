#!/usr/bin/env python3
"""Build Freilesen's source discovery catalogue from CC0 OPML feeds.

The catalogue is for discovery only. It does not assert that every article is
free, credible, or written by an independent journalist; access and evidence
markers are assessed per article at runtime.
"""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "source_catalog.json"
API = "https://api.github.com/repos/plenaryapp/awesome-rss-feeds/contents/"
RAW = "https://raw.githubusercontent.com/plenaryapp/awesome-rss-feeds/master/"
HEADERS = {"User-Agent": "Freilesen-source-catalog-builder/1.0"}
LIMIT = 1000

# General topics first because they are useful as alternatives across subjects.
CATEGORY_PRIORITY = [
    "News", "History", "Science", "Environment", "Tech", "Cyber security",
    "Business & Economy", "Personal finance", "Startups", "Programming",
    "Web Development", "Space", "Books", "Nature", "Animal & Wildlife",
    "Architecture", "Photography", "Travel", "Sports", "Android",
    "Android Development", "Apple", "iOS Development", "Food", "Music",
    "Movies", "Fashion", "DIY", "Cars", "Chess", "Football", "Tennis",
    "Cricket", "Gaming", "Cryptocurrency", "Beauty", "Interior design",
    "Television", "Funny", "Memes",
]
COUNTRY_PRIORITY = [
    ("Germany", "de"), ("United Kingdom", "en"), ("United States", "en"),
    ("Canada", "en"), ("Australia", "en"), ("Ireland", "en"),
    ("South Africa", "en"),
]
NOISE_HOSTS = {"youtube.com", "www.youtube.com", "open.spotify.com", "soundcloud.com", "twitter.com", "x.com", "instagram.com", "twitch.tv"}
GERMAN_INDEPENDENT = [
    ("Netzpolitik.org", "https://netzpolitik.org/feed/"),
    ("CORRECTIV", "https://correctiv.org/feed/"),
    ("Volksverpetzer", "https://www.volksverpetzer.de/feed/"),
    ("Übermedien", "https://uebermedien.de/feed/"),
    ("RiffReporter", "https://www.riffreporter.de/de/feed.xml"),
    ("Krautreporter", "https://krautreporter.de/feed"),
    ("Kontext: Wochenzeitung", "https://www.kontextwochenzeitung.de/rss.xml"),
    ("Jungle World", "https://jungle.world/rss.xml"),
    ("nd", "https://www.nd-aktuell.de/rss/all.rss"),
    ("taz", "https://taz.de/!p4608;rss/"),
    ("Deutschlandfunk", "https://www.deutschlandfunk.de/nachrichten-100.rss"),
    ("Deutsche Welle", "https://rss.dw.com/xml/rss-de-all"),
    ("Tagesschau", "https://www.tagesschau.de/xml/rss2"),
    ("heise online", "https://www.heise.de/rss/heise-atom.xml"),
    ("Golem.de", "https://rss.golem.de/rss.php?feed=RSS2.0"),
    ("t3n", "https://t3n.de/rss.xml"),
    ("Table.Briefings", "https://table.media/feed/"),
    ("MedWatch", "https://medwatch.de/feed/"),
]


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()


def list_opmls(folder):
    data = json.loads(get(API + folder))
    return {item["name"]: item for item in data if item["name"].lower().endswith(".opml")}


def parse_opml(folder, filename, language, kind):
    path = folder + "/" + filename
    xml = get(RAW + urllib.parse.quote(path, safe="/" )).decode("utf-8", errors="replace")
    # Some public OPML exports contain bare ampersands in feed names.
    xml = re.sub(r"&(?!#(?:\d+|x[\da-fA-F]+);|(?:amp|lt|gt|apos|quot);)", "&amp;", xml)
    root = ET.fromstring(xml)
    rows = []
    for node in root.iter("outline"):
        attr = node.attrib
        feed = (attr.get("xmlUrl") or "").strip()
        if not feed.startswith(("http://", "https://")):
            continue
        host = (urllib.parse.urlsplit(feed).hostname or "").lower()
        if host in NOISE_HOSTS:
            continue
        rows.append({
            "name": (attr.get("title") or attr.get("text") or host).strip(),
            "feed": feed,
            "website": (attr.get("htmlUrl") or feed).strip(),
            "language": language,
            "topic": filename.removesuffix(".opml") if kind == "topic" else filename.removesuffix(".opml"),
            "kind": kind,
        })
    return rows


def normalize(row):
    row["feed"] = row["feed"].replace("http://", "https://", 1) if row["feed"].startswith("http://") else row["feed"]
    row["website"] = row["website"].replace("http://", "https://", 1) if row["website"].startswith("http://") else row["website"]
    row["accessPolicy"] = "article_level_check_required"
    row["trustPolicy"] = "signals_only_no_editorial_endorsement"
    row["catalogueLicense"] = "CC0-1.0"
    return row


def main():
    category_files = list_opmls("recommended/with_category")
    country_files = list_opmls("countries/with_category")
    selected = {}
    # Preserve a German first set, then broad English-language markets.
    for country, lang in COUNTRY_PRIORITY:
        filename = country + ".opml"
        if filename in country_files:
            for row in parse_opml("countries/with_category", filename, lang, "newsroom_or_blog"):
                row = normalize(row)
                selected.setdefault(row["feed"].lower(), row)
    for name, feed in GERMAN_INDEPENDENT:
        host = (urllib.parse.urlsplit(feed).hostname or "").lower()
        row = normalize({"name": name, "feed": feed, "website": "https://" + host, "language": "de", "topic": "News", "kind": "independent_newsroom_or_blog"})
        selected.setdefault(row["feed"].lower(), row)
    # Include every maintained recommendation category so the searchable set
    # grows beyond the first 500 feeds while retaining the curated ordering.
    ordered_categories = CATEGORY_PRIORITY + [name.removesuffix(".opml") for name in category_files if name.removesuffix(".opml") not in CATEGORY_PRIORITY]
    for category in ordered_categories:
        filename = category + ".opml"
        if filename not in category_files:
            continue
        for row in parse_opml("recommended/with_category", filename, "en", "blog_or_specialist"):
            row = normalize(row)
            selected.setdefault(row["feed"].lower(), row)
    rows = list(selected.values())[:LIMIT]
    for i, row in enumerate(rows, 1):
        row["id"] = f"fs-{i:03d}"
    payload = {
        "version": 1,
        "generated": date.today().isoformat(),
        "count": len(rows),
        "ranking": "curated-recommendations-not-traffic-ranked",
        "upstream": "https://github.com/plenaryapp/awesome-rss-feeds",
        "upstreamLicense": "CC0-1.0",
        "accessNote": "A source feed is a discovery hint, never proof that an individual article is free.",
        "trustNote": "Directory inclusion is not a factuality or editorial-quality rating.",
        "sources": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(rows)} curated source feeds to {OUT}")


if __name__ == "__main__":
    main()
