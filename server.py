#!/usr/bin/env python3
"""Freilesen local preview and link-driven related-news search."""
from __future__ import annotations

import html
import ipaddress
import json
import os
import re
import socket
import time
import threading
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREVIEW = ROOT / "preview"
SOURCE_CATALOG_PATH = ROOT / "data" / "source_catalog.json"
TOKEN = re.compile(r"[\wÄÖÜäöüß]{2,}", re.UNICODE)
ACCESS_CACHE = {}
FEED_CACHE = {}
try:
    SOURCE_CATALOG = json.loads(SOURCE_CATALOG_PATH.read_text()).get("sources", [])
except (OSError, ValueError):
    SOURCE_CATALOG = []
try:
    INDEPENDENT_CATALOG_PATH = ROOT / "data" / "independent_sources.json"
    INDEPENDENT_SOURCES = json.loads(INDEPENDENT_CATALOG_PATH.read_text()).get("sources", [])
except (OSError, ValueError):
    INDEPENDENT_SOURCES = []
SOURCE_CATALOG.extend(INDEPENDENT_SOURCES)
SOURCE_KIND_OVERRIDES = {
    "Deutschlandfunk": "public_service_newsroom",
    "Deutsche Welle": "public_service_newsroom",
    "Tagesschau": "public_service_newsroom",
    "heise online": "specialist_publication",
    "Golem.de": "specialist_publication",
    "t3n": "specialist_publication",
    "Table.Briefings": "specialist_publication",
}
for _source in SOURCE_CATALOG:
    if _source.get("name") in SOURCE_KIND_OVERRIDES:
        _source["kind"] = SOURCE_KIND_OVERRIDES[_source["name"]]
STOP = set("""
a an and are as at be been being but by can could did do does doing down during each few for from further had has have having he her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was we were what when where which while who whom why will with would you your yours yourself yourselves
aber alle als also am an andere auch auf aus bei bin bis bist bitte bleiben dadurch dafür dagegen daher damit danach dann das dass dein deine dem den der des deshalb die dies diese dieser dieses doch dort du durch eigentlich ein eine einem einen einer eines einfach einmal er es etwas euer für gegen gewesen hat hatte hatten haben hier hin hinter ich ihm ihn ihre im immer in ins ist ja jeder jede jedes kann kein keine mit man mehr mein meine mich mir mit muss nach nachdem neben nein nicht nichts noch nun nur ob oder ohne sein seine selbst sich sie sind so über um und uns unser unter vom von vor war waren warum was weiter weil welcher welche welches wenn werden wie wieder wir wo zu zum zur zwischen
artikel report story news latest update video bildplus bild de deutschland deutschlandweit interview spricht sagte sagt laut nun heute gestern wurde worden weitere thema wie geht heißt hiesige us global effort weakened how why what when where who which whose this that these those new latest breaking exclusive says said tells told amid over after before following reveals explains report reports according first second third wins win loss fails failed makes made remains may might could would should will chief major key big top rise rising falls fall world across source sources people people's official statement statements media press updates analysis comment opinion live watch read after amid extends move moves talks call calls
""".split())
# Small bilingual concept map lets German and English feeds share core ideas.
ALIASES = {
    "indien":"india", "indiens":"india", "indische":"india", "indischer":"india", "indischen":"india", "indischem":"india",
    "junge":"boy", "jungen":"boy", "junges":"boy", "junger":"boy", "boy":"boy", "boys":"boy",
    "kind":"child", "kinder":"child", "children":"child", "child":"child",
    "wuchs":"grow", "aufwuchs":"grow", "wachsen":"grow", "aufwachsen":"grow", "grew":"grow", "grows":"grow", "grown":"grow", "growing":"grow",
    "armenviertel":"poverty", "armut":"poverty", "poor":"poverty", "poverty":"poverty",
    "slums":"slum", "slum":"slum", "indian":"india", "india":"india",
    "nazi":"nazi", "nazis":"nazi", "nationalsozialismus":"nazi", "nationalsozialistisch":"nazi", "hitler":"nazi", "wehrmacht":"wehrmacht",
    "nsdap":"nsdap", "mitglied":"membership", "mitgliedschaft":"membership", "membership":"membership", "member_records":"member_records",
    "kartei":"records", "karteikarte":"records", "karteikarten":"records", "akten":"records", "akte":"records", "archive":"records", "archives":"records", "archiv":"records", "archiviert":"records", "records":"records", "files":"records", "file":"records",
    "familie":"family", "familien":"family", "family":"family", "families":"family",
    "geschichte":"history", "geschichten":"history", "history":"history", "histories":"history",
    "legitimiert":"legitimize", "legitimieren":"legitimize", "legitimize":"legitimize", "legitimized":"legitimize", "legitimising":"legitimize",
    "parteigenosse":"party_member", "parteigenossen":"party_member", "party_member":"party_member", "party_members":"party_member",
}
GERMAN_FOR_ENGLISH = {"india":"indien", "boy":"junge", "child":"kind", "grow":"wuchs", "poverty":"armut", "slum":"slum", "nazi":"nationalsozialismus", "nsdap":"nsdap", "membership":"mitgliedschaft", "member_records":"mitgliederkartei", "records":"akten", "family":"familie", "history":"geschichte", "legitimize":"legitimiert", "party_member":"parteigenosse", "worldwar2":"zweiter weltkrieg"}
ENGLISH_FOR_GERMAN = {"india":"india", "boy":"boy", "child":"child", "grow":"grew", "poverty":"poverty", "slum":"slum", "nazi":"nazi", "nsdap":"nsdap", "membership":"membership", "member_records":"membership records", "records":"records", "family":"family", "history":"history", "legitimize":"legitimized", "party_member":"party member", "worldwar2":"world war ii"}
# Common reporting beats are normalized across German and English before query
# construction and relevance scoring. This is a compact bridge, not machine
# translation; proper names and article metadata remain the strongest signals.
BILINGUAL_TOPICS = {
    "government": (("government", "governments"), ("regierung", "regierungen", "regierungspolitik")),
    "election": (("election", "elections", "vote", "voting"), ("wahl", "wahlen", "wahlkampf", "abstimmung")),
    "parliament": (("parliament", "parliamentary", "legislator", "lawmakers"), ("parlament", "parlamente", "abgeordnete", "gesetzgeber")),
    "migration": (("migration", "migrant", "migrants", "immigration"), ("migration", "migrant", "migranten", "zuwanderung", "einwanderung")),
    "refugee": (("refugee", "refugees", "asylum seeker", "asylum"), ("flüchtling", "flüchtlinge", "geflüchtete", "asyl")),
    "war": (("war", "warfare", "conflict"), ("krieg", "kriege", "konflikt", "bewaffneter konflikt")),
    "military": (("military", "defence", "defense", "armed forces"), ("militär", "streitkräfte", "verteidigung", "bundeswehr")),
    "investigation": (("investigation", "investigations", "probe", "inquiry"), ("recherche", "recherchen", "untersuchung", "ermittlung")),
    "artificial_intelligence": (("artificial intelligence", "ai", "machine learning"), ("künstliche intelligenz", "ki", "maschinelles lernen")),
    "ai_regulation": (("ai regulation", "regulate ai", "ai governance", "artificial intelligence regulation", "govern artificial intelligence"), ("ki-regulierung", "ki regulierung", "regulierung künstlicher intelligenz", "ki-governance")),
    "autonomous_weapons": (("killer ai", "killer robots", "autonomous weapons", "lethal autonomous weapons", "military ai", "weaponized ai"), ("killer-roboter", "autonome waffen", "tödliche autonome waffen", "militärische ki", "waffenfähige ki")),
    "corruption": (("corruption", "bribery", "fraud"), ("korruption", "bestechung", "betrug")),
    "police": (("police", "policing", "law enforcement"), ("polizei", "polizeiarbeit", "ermittler")),
    "court": (("court", "courts", "trial", "lawsuit"), ("gericht", "gerichte", "prozess", "klage")),
    "climate": (("climate", "climate change", "global warming"), ("klima", "klimawandel", "erderwärmung")),
    "environment": (("environment", "environmental", "pollution"), ("umwelt", "umweltschutz", "verschmutzung")),
    "energy": (("energy", "electricity", "power"), ("energie", "strom", "elektrizität")),
    "renewable": (("renewable", "renewables", "wind power", "solar power"), ("erneuerbar", "erneuerbare", "windkraft", "solarenergie")),
    "health": (("health", "healthcare", "medicine"), ("gesundheit", "gesundheitswesen", "medizin")),
    "research": (("research", "study", "studies", "scientific"), ("forschung", "studie", "studien", "wissenschaftlich")),
    "economy": (("economy", "economic", "inflation", "recession"), ("wirtschaft", "wirtschaftlich", "inflation", "rezession")),
    "housing": (("housing", "rent", "rents", "real estate"), ("wohnen", "wohnung", "miete", "immobilien")),
    "education": (("education", "school", "university"), ("bildung", "schule", "schulen", "universität")),
    "human_rights": (("human rights", "civil rights", "rights"), ("menschenrechte", "grundrechte", "rechte")),
    "democracy": (("democracy", "democratic"), ("demokratie", "demokratisch")),
    "privacy": (("privacy", "data protection", "surveillance"), ("datenschutz", "privatsphäre", "überwachung")),
    "journalism": (("journalism", "journalist", "media"), ("journalismus", "journalist", "medien")),
    "disinformation": (("disinformation", "misinformation", "propaganda"), ("desinformation", "fehl-­information", "propaganda")),
}
for _topic, (_english_forms, _german_forms) in BILINGUAL_TOPICS.items():
    for _word in _english_forms + _german_forms:
        ALIASES[_word] = _topic
    ENGLISH_FOR_GERMAN[_topic] = _english_forms[0]
    GERMAN_FOR_ENGLISH[_topic] = _german_forms[0]
ALIASES.update({
    "ai":"artificial_intelligence", "artificial":"artificial_intelligence", "intelligence":"artificial_intelligence", "ki":"artificial_intelligence",
    "regulate":"ai_regulation", "regulates":"ai_regulation", "regulation":"ai_regulation", "regulatory":"ai_regulation", "governance":"ai_regulation", "govern":"ai_regulation", "regulierung":"ai_regulation",
    "killer":"autonomous_weapons", "robot":"autonomous_weapons", "robots":"autonomous_weapons", "autonomous":"autonomous_weapons", "weapon":"autonomous_weapons", "weapons":"autonomous_weapons", "waffen":"autonomous_weapons",
})
# Broad concepts help discovery, but cannot alone justify an alternative.
BROAD_TOPICS = {"nazi", "family", "history", "records", "regime", "war", "politics", "government", "membership", "party_member", "worldwar2", "wehrmacht"}
TOPIC_LABELS = {
    "artificial_intelligence": "Künstliche Intelligenz", "ai_regulation": "KI-Regulierung", "autonomous_weapons": "Autonome Waffen",
    "human_rights": "Menschenrechte", "worldwar2": "Zweiter Weltkrieg", "member_records": "Mitgliederkartei",
}
def topic_label(topic: str):
    return TOPIC_LABELS.get(topic, topic.replace("_", " ").replace("-", " ").title())
RELEVANT_TOPIC_PAIRS = ({"nazi", "worldwar2"}, {"nazi", "wehrmacht"}, {"nazi", "membership"}, {"nazi", "party_member"}, {"nsdap", "membership"}, {"nsdap", "party_member"}, {"nsdap", "member_records"}, {"falter", "member_records"})
FEED_TOPIC_MAP = {
    "News": {"news", "politics", "government", "war", "world", "election", "crime", "membership", "nazi", "history"},
    "History": {"history", "nazi", "war", "records", "membership", "family", "archive"},
    "Science": {"science", "health", "research", "climate", "space", "medicine", "study"},
    "Environment": {"environment", "climate", "energy", "nature", "pollution", "wildlife"},
    "Nature": {"nature", "animal", "wildlife", "climate", "environment"},
    "Tech": {"tech", "technology", "ai", "internet", "software", "cyber", "computer", "programming"},
    "Cyber security": {"security", "cyber", "privacy", "hacking", "data"},
    "Programming": {"programming", "developer", "software", "code", "technology"},
    "Web Development": {"web", "internet", "software", "technology", "programming"},
    "Business & Economy": {"business", "economy", "finance", "company", "market", "industry"},
    "Personal finance": {"finance", "money", "bank", "housing", "tax", "invest"},
    "Startups": {"startup", "business", "technology", "company", "founder"},
    "Space": {"space", "astronomy", "nasa", "planet", "science"},
    "Books": {"book", "author", "literature", "history", "culture"},
    "Sports": {"sport", "football", "soccer", "tennis", "cricket", "athlete"},
    "Food": {"food", "recipe", "restaurant", "cooking", "nutrition"},
    "Travel": {"travel", "tourism", "city", "culture"},
}
NEWSROOM_REGIONS = {"Germany", "United States", "Canada", "United Kingdom", "Australia", "Ireland", "South Africa"}
PUBLISHER_DOMAINS = {"sueddeutsche.de":"sueddeutsche.de", "sz.de":"sueddeutsche.de"}

def same_publisher(host: str, source_host: str):
    clean = lambda value: (value or "").lower().removeprefix("www.")
    host, source_host = clean(host), clean(source_host)
    if host == source_host or host.endswith("." + source_host) or source_host.endswith("." + host): return True
    return PUBLISHER_DOMAINS.get(host, host) == PUBLISHER_DOMAINS.get(source_host, source_host)

class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta = {}; self.meta_values = {}; self.title = ""; self.in_title = False; self.text = []; self._skip = 0; self.article_depth = 0; self.article_text = []; self.main_depth = 0; self.main_text = []; self.paywall_markup = False; self.author_present = False; self.article_hrefs = []; self.page_hrefs = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = a.get("property") or a.get("name") or a.get("itemprop")
            if key and a.get("content"):
                self.meta[key.lower()] = a["content"].strip()
                self.meta_values.setdefault(key.lower(), []).append(a["content"].strip())
                if key.lower() in ("author", "article:author", "parsely-author", "citation_author", "dc.creator"): self.author_present = True
        elif tag == "title": self.in_title = True
        if a.get("itemprop", "").lower() in ("author", "creator"): self.author_present = True
        if tag == "a" and a.get("href"):
            self.page_hrefs.append(a["href"])
            if self.article_depth: self.article_hrefs.append(a["href"])
        if tag == "article": self.article_depth += 1
        if tag == "main": self.main_depth += 1
        if tag in ("div", "section", "aside", "article") and re.search(r"pay.?wall|subscriber.?only|premium.?content|paid.?content|metered.?content|registration.?wall|article.?gate|content.?gate", (a.get("id", "") + " " + a.get("class", "")).lower()): self.paywall_markup = True
        elif tag in ("script", "style", "nav", "header", "footer", "aside"): self._skip += 1
    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False
        if tag == "article" and self.article_depth: self.article_depth -= 1
        if tag == "main" and self.main_depth: self.main_depth -= 1
        elif tag in ("script", "style", "nav", "header", "footer", "aside") and self._skip: self._skip -= 1
    def handle_data(self, data):
        if self.in_title: self.title += data
        if not self._skip and data.strip():
            self.text.append(data.strip())
            if self.article_depth: self.article_text.append(data.strip())
            if self.main_depth: self.main_text.append(data.strip())

def quality_signals(parser, page_url, page):
    """Report observable reporting/transparency cues, never a truth rating."""
    signals = []
    if parser.author_present or re.search(r'"author"\s*:\s*\{', page, re.I):
        signals.append("Autorenschaft im Quelltext genannt")
    base_host = (urllib.parse.urlsplit(page_url).hostname or "").lower().removeprefix("www.")
    external_refs = set()
    for href in parser.article_hrefs:
        try:
            host = (urllib.parse.urlsplit(urllib.parse.urljoin(page_url, href)).hostname or "").lower().removeprefix("www.")
            if host and host != base_host and not host.endswith("." + base_host): external_refs.add(host)
        except Exception:
            continue
    if len(external_refs) >= 2:
        signals.append("Mehrere externe Quellen verlinkt")
    policy_hrefs = " ".join(parser.page_hrefs).lower()
    if re.search(r"correction|errata|richtigstellung|korrektur|editorial.?standards|ethics.?policy", policy_hrefs):
        signals.append("Korrektur-/Redaktionshinweis verlinkt")
    if re.search(r"methodology|methodik|how.?we.?report|how.?we.?verify|quellen|sources|fact.?check|verification", policy_hrefs):
        signals.append("Methodik-/Quellenseite verlinkt")
    if re.search(r"about|imprint|impressum|transparen|masthead|funding|finanzierung|contact|kontakt|editorial.?team", policy_hrefs):
        signals.append("Transparenz-/Kontaktseite verlinkt")
    return signals

PAYWALL_TEXT = re.compile(r"(?:subscribe\s+to\s+(?:read|continue)|subscription\s+(?:required|only)|sign\s+in\s+to\s+(?:continue\s+)?reading|log\s*in\s+to\s+read\s+(?:the\s+)?full\s+article|this\s+article\s+is\s+for\s+subscribers|only\s+available\s+to\s+subscribers|already\s+a\s+subscriber|subscriber.?only|premium\s+(?:article|content)|metered\s+(?:article|paywall)|register\s+to\s+(?:read|continue)|nur\s+für\s+abonnenten|exklusiv\s+für\s+abonnenten|abo\s+(?:erforderlich|abschließen)|weiterlesen\s+mit\s+(?:ihrem|deinem)\s+abo|plus-artikel|plus\s+freischalten|artikel\s+ist\s+kostenpflichtig|zahlungspflichtig|kostenpflichtig\s+lesen|zum\s+weiterlesen\s+abo|jetzt\s+(?:abonnieren|mitglied\s+werden)|registrieren\s+zum\s+weiterlesen)", re.I)

def verify_free_access(url: str, source_host: str = ""):
    """Use publisher markup and readable article content; cache short-lived results."""
    cached = ACCESS_CACHE.get(url)
    if cached and cached[0] > time.monotonic():
        access, final_url, signals = cached[1], cached[2], cached[3]
        if access == "same_source" or not same_publisher(urllib.parse.urlsplit(final_url).hostname or "", source_host):
            return access, final_url, signals
    def verdict(access, final_url, signals=None):
        signals = signals or []
        if access != "same_source":
            ACCESS_CACHE[url] = (time.monotonic() + 900, access, final_url, signals)
            if len(ACCESS_CACHE) > 512: ACCESS_CACHE.pop(next(iter(ACCESS_CACHE)))
        return access, final_url, signals
    try:
        # Publisher metadata and paywall selectors live in the document head;
        # cap transfer size and time to avoid downloading whole articles.
        final_url, page = fetch(url, 320_000, timeout=5)
        final_host = urllib.parse.urlsplit(final_url).hostname or ""
        if same_publisher(final_host, source_host): return verdict("same_source", final_url)
        parser = MetadataParser(); parser.feed(page)
        lowered = page.lower()
        signals = quality_signals(parser, final_url, page)
        # Structured signals include Google's Schema.org paywall markup.
        if re.search(r'"isaccessibleforfree"\s*:\s*false|isaccessibleforfree\s*["\']?\s*content\s*=\s*["\']false|"(?:contenttier|accesslevel)"\s*:\s*"(?:premium|subscriber|paid)"', lowered):
            return verdict("paywall", final_url)
        page_text = html.unescape(" ".join(parser.text))
        if PAYWALL_TEXT.search(page_text) or parser.paywall_markup: return verdict("paywall", final_url)
        if re.search(r'"isaccessibleforfree"\s*:\s*true', lowered):
            return verdict("verified_free", final_url, signals)
        structured_body = re.search(r'"articleBody"\s*:\s*"((?:\\.|[^"\\]){1200,})"', page, re.I | re.S)
        if structured_body:
            try:
                if len(json.loads('"' + structured_body.group(1) + '"').strip()) >= 1200:
                    return verdict("likely_free", final_url, signals)
            except ValueError:
                pass
        # A page shell, teaser, or access-denied response is not evidence of free access.
        article_text = re.sub(r"\s+", " ", " ".join(parser.article_text)).strip()
        main_text = re.sub(r"\s+", " ", " ".join(parser.main_text)).strip()
        if len(article_text) >= 1200: return verdict("likely_free", final_url, signals)
        if len(main_text) >= 1800: return verdict("likely_free", final_url, signals)
        if len(page_text) >= 3200 and parser.meta.get("og:type", "").lower() in ("article", "newsarticle"):
            return verdict("likely_free", final_url, signals)
        return verdict("unknown", final_url, signals)
    except urllib.error.HTTPError as e:
        return verdict("paywall" if e.code in (401, 402, 403) else "unavailable", url)
    except Exception:
        return verdict("unavailable", url)

def public_url(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname: raise ValueError("Bitte einen gültigen HTTP- oder HTTPS-Artikellink eingeben.")
    try: addrs = {x[4][0] for x in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except OSError: raise ValueError("Die Artikeladresse konnte nicht aufgelöst werden.")
    if not addrs or any(not ipaddress.ip_address(a).is_global for a in addrs): raise ValueError("Diese Artikeladresse ist nicht erreichbar.")
    return url

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

OPENER = urllib.request.build_opener(SafeRedirect)
def fetch(url: str, limit: int = 1_500_000, timeout: int = 12):
    url = public_url(url)
    req = urllib.request.Request(url, headers={"User-Agent":"FreilesenPreview/0.2 (link metadata and related headlines)","Accept":"text/html,application/xhtml+xml,application/rss+xml,application/xml;q=0.9,*/*;q=0.5"})
    with OPENER.open(req, timeout=timeout) as resp:
        final_url = public_url(resp.geturl())
        body = resp.read(limit)
        charset = resp.headers.get_content_charset() or "utf-8"
        return final_url, body.decode(charset, errors="replace")

def source_categories(topic_words):
    preferred = []
    for category, keywords in FEED_TOPIC_MAP.items():
        if topic_words & keywords:
            preferred.append(category)
    # Keep a general news fallback, but do not spend most of the feed budget
    # on unrelated default buckets such as science/history for every query.
    if "News" not in preferred:
        preferred.insert(0, "News")
    return preferred

def feed_items(source):
    feed_url = source["feed"]
    cached = FEED_CACHE.get(feed_url)
    if cached and cached[0] > time.monotonic(): return cached[1]
    items = []
    try:
        _, xml = fetch(feed_url, 220_000, timeout=4)
        root = ET.fromstring(xml)
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1].lower() not in ("item", "entry"): continue
            fields = {}
            for child in list(node):
                name = child.tag.rsplit("}", 1)[-1].lower()
                if name == "link":
                    value = child.attrib.get("href") or "".join(child.itertext())
                else:
                    value = " ".join(child.itertext())
                if name in ("title", "description", "summary", "encoded", "content", "pubdate", "published", "updated", "date") and value:
                    fields[name] = value
            title = html.unescape(re.sub(r"<[^>]+>", " ", fields.get("title", ""))).strip()
            link = fields.get("link", "").strip()
            if not title or not link or urllib.parse.urlsplit(link).scheme not in ("http", "https"): continue
            description = fields.get("description") or fields.get("summary") or fields.get("encoded") or fields.get("content") or ""
            description = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", description))).strip()
            source_domain = urllib.parse.urlsplit(source.get("website") or feed_url).hostname or ""
            items.append({"title":title, "url":link, "source":source["name"], "sourceDomain":source_domain, "description":description[:500], "published":fields.get("pubdate") or fields.get("published") or fields.get("updated") or fields.get("date", ""), "language":source.get("language", "en"), "sourceKind":source.get("kind", "blog_or_specialist"), "sourceTopic":source.get("topic", "News"), "catalogued":True})
            if len(items) >= 15: break
    except Exception:
        items = []
    FEED_CACHE[feed_url] = (time.monotonic() + 1200, items)
    if len(FEED_CACHE) > 800: FEED_CACHE.pop(next(iter(FEED_CACHE)))
    return items

def search_curated_feeds(topic_words):
    preferred = source_categories(topic_words)
    priorities = {category: i for i, category in enumerate(preferred)}
    # The catalogue tags most English-language publishers by country rather
    # than by subject. Treat those regional desks as broad news sources, then
    # deliberately sample both languages so the input link's language does not
    # decide which feeds are searched.
    candidates = [
        s for s in SOURCE_CATALOG
        if (s.get("topic") in priorities or s.get("topic") == "Germany"
            or ("News" in priorities and s.get("topic") in NEWSROOM_REGIONS))
        and s.get("language") in ("de", "en")
        and not re.search(r"\b(?:podcasts?|reddit|memes?|funny|music|videos?|youtube|streams?)\b", s.get("name", ""), re.I)
    ]
    by_topic = {category: {"de": [], "en": []} for category in preferred}
    for source in candidates:
        category = source.get("topic")
        if category in NEWSROOM_REGIONS:
            category = "News"
        if category not in by_topic:
            category = "News"
        by_topic[category][source["language"]].append(source)
    for languages in by_topic.values():
        for sources in languages.values():
            # Explicitly vetted independent writers and investigative outlets
            # get sampled before the much larger generic feed dump.
            kind_rank = {"independent_blog": 0, "independent_newsroom_or_blog": 1, "blog_or_specialist": 2, "specialist_publication": 3, "public_service_newsroom": 4, "newsroom_or_blog": 5}
            sources.sort(key=lambda s: (kind_rank.get(s.get("kind", ""), 4), s.get("name", "").lower()))
    # Round-robin topics and languages. This keeps English and German feeds in
    # the discovery pool even when the source catalogue tags English outlets by
    # country or the incoming article is written in only one language.
    picked = []
    indexes = {category: {"de": 0, "en": 0} for category in preferred}
    while len(picked) < 48:
        added = False
        for category in preferred:
            for language in ("de", "en"):
                index = indexes[category][language]
                sources = by_topic[category][language]
                if index < len(sources):
                    picked.append(sources[index]); indexes[category][language] += 1; added = True
                    if len(picked) >= 48: break
            if len(picked) >= 48: break
        if not added: break
    with ThreadPoolExecutor(max_workers=24) as pool:
        groups = list(pool.map(feed_items, picked))
    return [item for group in groups for item in group]

def terms(text: str):
    return [t.lower() for t in TOKEN.findall(text) if t.lower() not in STOP and not t.isdigit()]
def canonical(token: str): return ALIASES.get(token, token)
def canonical_terms(text: str):
    # Treat this unambiguous phrase as one concept without matching generic
    # "family members" or "members of the public" to political membership.
    text = re.sub(r"\bparty\s+members?\b", " party_member ", text, flags=re.I)
    text = re.sub(r"\b(?:national\s+socialism|national\s+socialist(?:s|ic)?)\b", " nazi ", text, flags=re.I)
    text = re.sub(r"\bnsdap[-\s](?:mitglied(?:er)?)?(?:kartei(?:en)?|datei)\b", " nsdap member_records ", text, flags=re.I)
    text = re.sub(r"\b(?:mitglied(?:er|s)?(?:kartei(?:en)?|datei|datenbank)|membership\s+(?:card\s+)?(?:index|file|records?|database))\b", " member_records ", text, flags=re.I)
    text = re.sub(r"\b(?:zweiter\s+weltkrieg|world\s+war\s*(?:ii|2)|wwii)\b", " worldwar2 ", text, flags=re.I)
    return [canonical(t) for t in terms(text)]
def slug_title(url: str):
    path = urllib.parse.unquote(urllib.parse.urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1])
    path = re.sub(r"\.(html?|amp)$", "", path, flags=re.I)
    path = re.sub(r"(?:-li)?\.\d+$", "", path, flags=re.I)
    path = re.sub(r"-[a-z0-9]{5,}$", "", path, flags=re.I)
    return re.sub(r"[-_]+", " ", path).strip()[:220]

def read_metadata(url: str):
    canonical_url = url
    try:
        final, page = fetch(url)
        parser = MetadataParser(); parser.feed(page)
        title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or parser.meta.get("headline") or parser.title.strip()
        description = parser.meta.get("og:description") or parser.meta.get("description") or parser.meta.get("twitter:description") or ""
        keywords = []
        for key in ("news_keywords", "keywords", "article:tag", "article:section", "parsely-tags", "sailthru.tags"):
            for value in parser.meta_values.get(key, []):
                keywords.extend(part.strip() for part in re.split(r"[,;|]", value) if part.strip())
        article_body = ""
        for match in re.finditer(r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", page, re.I | re.S):
            try:
                structured = json.loads(html.unescape(match.group(1)))
            except (ValueError, TypeError):
                continue
            stack = structured if isinstance(structured, list) else [structured]
            while stack:
                node = stack.pop()
                if isinstance(node, list):
                    stack.extend(node)
                elif isinstance(node, dict):
                    stack.extend(value for value in node.values() if isinstance(value, (dict, list)))
                    for field in ("keywords", "articleSection", "about", "mentions"):
                        value = node.get(field)
                        if isinstance(value, list):
                            keywords.extend(str(item.get("name", "")) if isinstance(item, dict) else str(item) for item in value)
                        elif value:
                            keywords.extend(part.strip() for part in re.split(r"[,;|]", str(value)) if part.strip())
                    if not title and node.get("headline"): title = str(node["headline"])
                    if not description and node.get("description"): description = str(node["description"])
                    if not article_body and node.get("articleBody"): article_body = str(node["articleBody"])[:5000]
        canonical_match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', page, re.I)
        if canonical_match: canonical_url = urllib.parse.urljoin(final, html.unescape(canonical_match.group(1)))
        snippet = re.sub(r"\s+", " ", html.unescape(description)).strip()
        if not snippet: snippet = re.sub(r"\s+", " ", " ".join(parser.text)).strip()[:320]
        keywords = list(dict.fromkeys(re.sub(r"\s+", " ", item).strip() for item in keywords if item.strip()))[:30]
        return {"url": canonical_url, "title": re.sub(r"\s+", " ", html.unescape(title)).strip() or slug_title(url), "description": snippet[:900], "keywords": keywords, "articleBody": article_body, "publisher": parser.meta.get("og:site_name") or urllib.parse.urlsplit(final).hostname or "", "published": parser.meta.get("article:published_time") or parser.meta.get("datepublished") or parser.meta.get("date", "")}
    except Exception:
        return {"url": url, "title": slug_title(url), "description": "", "publisher": urllib.parse.urlsplit(url).hostname or "", "published": ""}

def topic_weights(meta):
    weights = Counter()
    # Headline, publisher tags, and URL slug are strong evidence; description
    # and the article's own structured body add important names and context.
    for text, weight in ((meta.get("title", ""), 6), (" ".join(meta.get("keywords", [])), 5), (slug_title(meta.get("url", "")), 4), (meta.get("description", ""), 3), (meta.get("articleBody", "")[:2200], 1)):
        counts = Counter(canonical_terms(text))
        for word, count in counts.items():
            if len(word) >= 2: weights[word] += weight * min(count, 2)
    return weights

def search_news(meta):
    weights = topic_weights(meta)
    if not weights: return [], []
    ranked = sorted(weights, key=lambda w: (-weights[w], -len(w), w))[:14]
    # Search both language editions and send both language variants to GDELT.
    # These independent queries run concurrently below to keep broad discovery
    # responsive rather than adding their network time together.
    de_terms = list(dict.fromkeys(GERMAN_FOR_ENGLISH.get(w, w) for w in ranked[:10]))
    en_terms = list(dict.fromkeys(ENGLISH_FOR_GERMAN.get(w, w) for w in ranked[:10]))
    source_title = meta.get("title", "")[:180]
    def detect_language(text, fallback="en"):
        """Best-effort label for short headlines; feeds/GDELT remain primary signals."""
        value = " " + re.sub(r"[^a-zäöüß]+", " ", (text or "").lower()) + " "
        if re.search(r"[äöüß]", value):
            return "de"
        words = set(value.split())
        german = {"der", "die", "das", "und", "ist", "mit", "von", "für", "im", "auf", "über", "auch", "nicht", "nach", "bei", "wird", "sind", "einer", "einem", "zum", "zur"}
        english = {"the", "and", "is", "with", "from", "for", "in", "on", "also", "not", "after", "at", "will", "are", "has", "have", "this", "that", "their", "was"}
        de_hits, en_hits = len(words & german), len(words & english)
        if de_hits != en_hits and max(de_hits, en_hits) >= 1:
            return "de" if de_hits > en_hits else "en"
        return fallback

    blog_sites = "(site:substack.com OR site:medium.com OR site:ghost.io OR site:wordpress.com OR site:buttondown.email OR site:beehiiv.com OR site:write.as OR site:blogspot.com OR site:blogger.com OR site:patreon.com)"
    # Preserve short but high-value concepts such as AI when constructing queries.
    def or_query(words):
        terms_for_query = [w for w in words if len(w) > 2 or w in {"ai", "ki"}]
        return "(" + " OR ".join('"' + w.replace('"', '') + '"' for w in terms_for_query) + ")"
    queries = [
        ("google", or_query(de_terms), "de", {"hl":"de", "gl":"DE", "ceid":"DE:de"}),
        ("google", or_query(en_terms), "en", {"hl":"en-US", "gl":"US", "ceid":"US:en"}),
        ("google", source_title, "de", {"hl":"de", "gl":"DE", "ceid":"DE:de"}),
        ("google", source_title, "en", {"hl":"en-US", "gl":"US", "ceid":"US:en"}),
        # Search self-publishing and independent blog platforms directly.
        # This reaches far beyond the fixed RSS list, including small authors
        # whose sites are not present in any directory.
        ("google_blog", or_query(de_terms) + " " + blog_sites, "de", {"hl":"de", "gl":"DE", "ceid":"DE:de"}),
        ("google_blog", or_query(en_terms) + " " + blog_sites, "en", {"hl":"en-US", "gl":"US", "ceid":"US:en"}),
        ("gdelt", or_query(en_terms[:10]), "all", {}),
        ("gdelt", or_query(de_terms[:10]), "all", {}),
        # Focused general topic searches add precision without binding discovery
        # to any subject; all query terms come from this submitted article.
        ("google", or_query(de_terms[:6]), "de", {"hl":"de", "gl":"DE", "ceid":"DE:de"}),
        ("google", or_query(en_terms[:6]), "en", {"hl":"en-US", "gl":"US", "ceid":"US:en"}),
        ("google_blog", or_query(de_terms[:6]) + " " + blog_sites, "de", {"hl":"de", "gl":"DE", "ceid":"DE:de"}),
        ("google_blog", or_query(en_terms[:6]) + " " + blog_sites, "en", {"hl":"en-US", "gl":"US", "ceid":"US:en"}),
    ]
    source_host = (urllib.parse.urlsplit(meta.get("url", "")).hostname or "").lower()
    source_title_words = set(canonical_terms(meta.get("title", "")))
    # Compare against the ten strongest extracted concepts. One-off descriptive
    # words add context but should not drown out the actual headline topic.
    core_topics = ranked[:10]
    total_topic_weight = sum(weights[w] for w in core_topics) or 1
    matches = {}
    candidates = {}
    def consider(item, provider):
        title, link = item.get("title", ""), item.get("url", "")
        if not title or not link: return
        host = (urllib.parse.urlsplit(link).hostname or "").lower()
        if same_publisher(host, source_host) or (item.get("sourceDomain") and same_publisher(item["sourceDomain"], source_host)): return
        text = title + " " + item.get("description", "")
        result_words = set(canonical_terms(text))
        title_words = set(canonical_terms(title))
        core = set(ranked[:16])
        overlap = core & result_words
        title_overlap = core & title_words
        distinctive = overlap - BROAD_TOPICS
        paired_topic = any(pair.issubset(overlap) for pair in RELEVANT_TOPIC_PAIRS)
        source_specific = set(ranked) - BROAD_TOPICS
        # A topic-heavy source requires more evidence than an incidental shared
        # entity. A focused one-concept source may still match one strong term,
        # while multi-topic articles need two independent subject signals.
        required_specific = 2 if len(source_specific) >= 3 else 1
        if len(distinctive) < required_specific and not paired_topic: return
        if len(source_specific) >= 2 and len(distinctive) < 2 and not paired_topic: return
        paywall_marker = bool(re.search(r"bild\s*plus|bildplus|sz\s*plus|plus-abo|paywall|abo-artikel|subscription required|subscribe to read|\(\s*s\+\s*\)|(?<!\w)s\+(?!\w)", (title + " " + item.get("source", "")).lower()))
        if paywall_marker: return
        key = re.sub(r"[^a-z0-9]", "", title.lower())
        body_words = set(canonical_terms(item.get("description", "")))
        matched_weight = sum(weights[w] * (1.0 if w in title_overlap else 0.55 if w in body_words else 0.25 if w in overlap else 0.0) for w in core_topics)
        raw_score = min(94, round(100 * matched_weight / total_topic_weight))
        if {"nsdap", "member_records"}.issubset(title_overlap):
            raw_score = max(raw_score, 70)
        score = min(99, round(raw_score + (100 - raw_score) * 0.08))
        if source_title_words and source_title_words == title_words: score = 100
        result_kind = item.get("sourceKind") or ("independent_blog_candidate" if provider == "google_blog" else "newsroom")
        result = {"title":title, "description":item.get("description", "")[:360], "url":link, "source":item.get("source") or host, "lang":item.get("language", "en"), "published":item.get("published", ""), "score":score, "matchedTopics":[topic_label(word) for word in sorted(overlap)], "provider":provider, "sourceKind":result_kind, "sourceTopic":item.get("sourceTopic", ""), "catalogued":bool(item.get("catalogued") or provider == "google_blog")}
        current = candidates.get(key)
        if current is None or score > current["score"] or (result["catalogued"] and not current.get("catalogued")): candidates[key] = result
    def search_provider(spec):
        provider, query, requested_lang, extras = spec
        if not query.strip(): return provider, []
        try:
            if provider in ("google", "google_blog"):
                params = urllib.parse.urlencode({"q":query, **extras})
                _, response = fetch("https://news.google.com/rss/search?" + params, 1_000_000, timeout=8)
                root = ET.fromstring(response)
                records = []
                for item in root.findall(".//item"):
                    desc = item.findtext("description", "")
                    records.append({
                        "title":item.findtext("title", "").strip(),
                        "url":item.findtext("link", "").strip(),
                        "source":item.findtext("source", "").strip(),
                        "sourceDomain":urllib.parse.urlsplit(item.find("source").attrib.get("url", "")).hostname or "" if item.find("source") is not None else "",
                        "description":re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", desc))).strip(),
                        "published":item.findtext("pubDate", "").strip(),
                        "language":detect_language(item.findtext("title", "") + " " + desc, requested_lang)
                    })
            else:
                params = urllib.parse.urlencode({"query":query, "mode":"artlist", "format":"json", "maxrecords":"100", "timespan":"1year", "sort":"HybridRel"})
                _, response = fetch("https://api.gdeltproject.org/api/v2/doc/doc?" + params, 2_000_000, timeout=8)
                data = json.loads(response)
                records = []
                for item in data.get("articles", []):
                    lang = (item.get("language") or "").lower()
                    if lang.startswith("german"): lang = "de"
                    elif lang.startswith("english"): lang = "en"
                    else: continue
                    records.append({"title":item.get("title", "").strip(), "url":item.get("url", "").strip(), "source":item.get("domain", "").strip(), "sourceDomain":item.get("domain", "").strip(), "description":"", "published":item.get("seendate", ""), "language":lang})
        except Exception:
            records = []
        return provider, records
    with ThreadPoolExecutor(max_workers=len(queries) + 1) as pool:
        jobs = [pool.submit(search_provider, spec) for spec in queries]
        feeds_job = pool.submit(search_curated_feeds, set(ranked))
        for job in jobs:
            provider, records = job.result()
            for item in records: consider(item, provider)
        feed_records = feeds_job.result()
    for item in feed_records:
        consider(item, "kuratiert")
    # Check only the highest relevance candidates. Explicit paywall and failed
    # requests are excluded; successfully opened pages without enough evidence
    # remain visible as "possibly free" so readers can verify them themselves.
    matches = {}
    by_score = sorted(candidates.items(), key=lambda item: -item[1]["score"])
    independent_keys = {
        key for key, item in candidates.items()
        if item.get("sourceKind") in ("independent_blog", "independent_newsroom_or_blog", "independent_blog_candidate", "blog_or_specialist")
    }
    independent_top = [item for item in by_score if item[0] in independent_keys][:24]
    other_top = [item for item in by_score if item[0] not in independent_keys][:48 - len(independent_top)]
    top = sorted(independent_top + other_top, key=lambda item: -item[1]["score"])
    with ThreadPoolExecutor(max_workers=24) as pool:
        checked = list(pool.map(lambda pair: verify_free_access(pair[1]["url"], source_host), top))
    access_counts = Counter(access for access, _, _ in checked)
    for (key, result), (access, final_url, signals) in zip(top, checked):
        if access in ("verified_free", "likely_free", "unknown"):
            result["access"] = access
            result["url"] = final_url
            result["qualitySignals"] = signals
            matches[key] = result
    print("Zugriffsprüfung: %d Kandidaten; Zugriffsstatus %s; %d verwertbare Alternativen." % (len(candidates), dict(access_counts), len(matches)), flush=True)
    results = sorted(matches.values(), key=lambda x: (-x["score"], x["title"].lower()))
    # Keep a result from one publisher from filling the page. Preserve each
    # article's real topic score; this only diversifies the visible selection.
    independent = [r for r in results if r.get("sourceKind") in ("independent_blog", "independent_newsroom_or_blog", "independent_blog_candidate", "blog_or_specialist")]
    newsroom = [r for r in results if r not in independent]
    chosen = []
    publisher_counts = Counter()
    queues = [independent, newsroom]
    while len(chosen) < 12 and any(queues):
        for queue in queues:
            while queue:
                item = queue.pop(0)
                host = (urllib.parse.urlsplit(item.get("url", "")).hostname or item.get("source", "")).lower().removeprefix("www.")
                if publisher_counts[host] < 2:
                    chosen.append(item); publisher_counts[host] += 1; break
            if len(chosen) >= 12: break
        queues = [q for q in queues if q]
    return chosen, ranked

class Handler(SimpleHTTPRequestHandler):
    rate_lock = threading.Lock()
    rate_buckets = {}
    search_slots = threading.BoundedSemaphore(2)
    max_request_bytes = 4096
    rate_limit_per_minute = 10

    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(PREVIEW), **kwargs)
    def do_GET(self):
        if self.path == "/healthz":
            self._json_response(200, {"ok": True})
            return
        if self.path == "/api/search":
            self.send_response(405); self.send_header("Allow", "POST"); self.end_headers(); return
        super().do_GET()

    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path != "/api/search":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json_response(400, {"ok": False, "error": "Ungültige Anfrage."})
            return
        if length <= 0 or length > self.max_request_bytes:
            self._json_response(413 if length > self.max_request_bytes else 400, {"ok": False, "error": "Die Anfrage ist leer oder zu groß."})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            target = payload.get("url", "") if isinstance(payload, dict) else ""
            if not isinstance(target, str) or not target.strip():
                raise ValueError("Füge zuerst einen Artikellink ein.")
            if len(target) > 2048:
                raise ValueError("Der Artikellink ist zu lang.")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json_response(400, {"ok": False, "error": "Ungültiges JSON."})
            return
        except ValueError as e:
            self._json_response(400, {"ok": False, "error": str(e)})
            return

        if self._rate_limited():
            self._json_response(429, {"ok": False, "error": "Zu viele Suchanfragen. Bitte warte einen Moment."})
            return
        if not self.search_slots.acquire(blocking=False):
            self._json_response(503, {"ok": False, "error": "Der Suchdienst ist gerade ausgelastet. Bitte versuche es gleich erneut."})
            return
        try:
            try:
                meta = read_metadata(target)
                results, topics = search_news(meta)
                payload = {"ok":True,"metadata":meta,"topics":[topic_label(topic) for topic in topics],"results":results,"message":"" if results else "Keine passenden Artikel gefunden. Versuche es später mit mehr Kontext oder einer anderen Suchanfrage."}
            except ValueError as e:
                payload = {"ok":False,"error":str(e)}
            except Exception:
                payload = {"ok":False,"error":"Metadaten oder thematische Suche konnten gerade nicht ausgewertet werden."}
            self._json_response(200, payload)
        finally:
            self.search_slots.release()

    def _rate_limited(self):
        # Render overwrites CF-Connecting-IP at its edge; never trust a generic
        # client-supplied forwarding header for rate-limit identity.
        client_ip = (self.headers.get("CF-Connecting-IP") or self.client_address[0]).strip()
        now = time.monotonic()
        with self.rate_lock:
            bucket = self.rate_buckets.setdefault(client_ip, deque())
            while bucket and now - bucket[0] >= 60:
                bucket.popleft()
            if len(bucket) >= self.rate_limit_per_minute:
                return True
            bucket.append(now)
            if len(self.rate_buckets) > 4096:
                stale = [ip for ip, requests in self.rate_buckets.items() if not requests or now - requests[-1] >= 60]
                for ip in stale:
                    self.rate_buckets.pop(ip, None)
        return False

    def _json_response(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/search"):
            print("API-Suche (Artikellink nicht protokolliert)", flush=True)
        else:
            print("HTTP-Anfrage an Vorschau", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST", "0.0.0.0")
    print("Freilesen-Suchdienst auf %s:%d" % (host, port), flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
