#!/usr/bin/env python3
"""Freilesen local preview and link-driven related-news search."""
from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
import time
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
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
STOP = set("""
a an and are as at be been being but by can could did do does doing down during each few for from further had has have having he her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was we were what when where which while who whom why will with would you your yours yourself yourselves
aber alle als also am an andere auch auf aus bei bin bis bist bitte bleiben dadurch dafür dagegen daher damit danach dann das dass dein deine dem den der des deshalb die dies diese dieser dieses doch dort du durch eigentlich ein eine einem einen einer eines einfach einmal er es etwas euer für gegen gewesen hat hatte hatten haben hier hin hinter ich ihm ihn ihre im immer in ins ist ja jeder jede jedes kann kein keine mit man mehr mein meine mich mir mit muss nach nachdem neben nein nicht nichts noch nun nur ob oder ohne sein seine selbst sich sie sind so über um und uns unser unter vom von vor war waren warum was weiter weil welcher welche welches wenn werden wie wieder wir wo zu zum zur zwischen
artikel report story news latest update video bildplus bild de deutschland deutschlandweit interview spricht sagte sagt laut nun heute gestern wurde worden weitere thema wie geht heißt hiesige
""".split())
# Small bilingual concept map lets German and English feeds share core ideas.
ALIASES = {
    "indien":"india", "indiens":"india", "indische":"india", "indischer":"india", "indischen":"india", "indischem":"india",
    "junge":"boy", "jungen":"boy", "junges":"boy", "junger":"boy", "boy":"boy", "boys":"boy",
    "kind":"child", "kinder":"child", "children":"child", "child":"child",
    "wuchs":"grow", "aufwuchs":"grow", "wachsen":"grow", "aufwachsen":"grow", "grew":"grow", "grows":"grow", "grown":"grow", "growing":"grow",
    "armenviertel":"poverty", "armut":"poverty", "poor":"poverty", "poverty":"poverty",
    "slums":"slum", "slum":"slum", "indian":"india", "india":"india",
    "nazi":"nazi", "nazis":"nazi", "nationalsozialismus":"nazi", "nationalsozialistisch":"nazi", "nsdap":"nazi", "hitler":"nazi",
    "mitgliederkartei":"membership", "mitgliedskartei":"membership", "mitgliedskarteien":"membership", "mitgliedschaft":"membership", "mitglied":"membership", "membership":"membership",
    "kartei":"records", "karteikarte":"records", "karteikarten":"records", "akten":"records", "akte":"records", "archive":"records", "archives":"records", "archiv":"records", "archiviert":"records", "records":"records", "files":"records", "file":"records",
    "familie":"family", "familien":"family", "family":"family", "families":"family",
    "geschichte":"history", "geschichten":"history", "history":"history", "histories":"history",
    "legitimiert":"legitimize", "legitimieren":"legitimize", "legitimize":"legitimize", "legitimized":"legitimize", "legitimising":"legitimize",
    "parteigenosse":"party_member", "parteigenossen":"party_member", "party_member":"party_member", "party_members":"party_member",
}
GERMAN_FOR_ENGLISH = {"india":"indien", "boy":"junge", "child":"kind", "grow":"wuchs", "poverty":"armut", "slum":"slum", "nazi":"nazi", "membership":"mitgliedschaft", "records":"akten", "family":"familie", "history":"geschichte", "legitimize":"legitimiert", "party_member":"parteigenosse"}
ENGLISH_FOR_GERMAN = {"india":"india", "boy":"boy", "child":"child", "grow":"grew", "poverty":"poverty", "slum":"slum", "nazi":"nazi", "membership":"membership", "records":"records", "family":"family", "history":"history", "legitimize":"legitimized", "party_member":"party member"}
# Broad concepts help discovery, but cannot alone justify an alternative.
BROAD_TOPICS = {"nazi", "family", "history", "records", "regime", "war", "politics", "government"}
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
PUBLISHER_DOMAINS = {"sueddeutsche.de":"sueddeutsche.de", "sz.de":"sueddeutsche.de"}

def same_publisher(host: str, source_host: str):
    clean = lambda value: (value or "").lower().removeprefix("www.")
    host, source_host = clean(host), clean(source_host)
    if host == source_host or host.endswith("." + source_host) or source_host.endswith("." + host): return True
    return PUBLISHER_DOMAINS.get(host, host) == PUBLISHER_DOMAINS.get(source_host, source_host)

class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta = {}; self.title = ""; self.in_title = False; self.text = []; self._skip = 0; self.article_depth = 0; self.article_text = []; self.main_depth = 0; self.main_text = []; self.paywall_markup = False; self.author_present = False; self.article_hrefs = []; self.page_hrefs = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = a.get("property") or a.get("name") or a.get("itemprop")
            if key and a.get("content"):
                self.meta[key.lower()] = a["content"].strip()
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
        # A page shell, teaser, or access-denied response is not evidence of free access.
        article_text = re.sub(r"\s+", " ", " ".join(parser.article_text)).strip()
        main_text = re.sub(r"\s+", " ", " ".join(parser.main_text)).strip()
        if len(article_text) >= 1200: return verdict("likely_free", final_url, signals)
        if len(main_text) >= 1800: return verdict("likely_free", final_url, signals)
        return verdict("unknown", final_url, signals)
    except urllib.error.HTTPError as e:
        return verdict("paywall" if e.code in (401, 402, 403) else "unavailable" if e.code in (404, 410) else "unknown", url)
    except Exception:
        return verdict("unknown", url)

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
    for category in ("News", "History", "Science", "Environment"):
        if category not in preferred: preferred.append(category)
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
    language_priority = {"de": 0, "en": 1}
    candidates = [s for s in SOURCE_CATALOG if s.get("topic") in priorities and s.get("language") in ("de", "en")]
    by_topic = {category: [] for category in preferred}
    for source in candidates: by_topic[source.get("topic")].append(source)
    for sources in by_topic.values():
        sources.sort(key=lambda s: (0 if "blog" in s.get("kind", "") else 1, language_priority.get(s.get("language"), 9), s.get("name", "").lower()))
    # Round-robin topic collections so a crowded News category cannot consume
    # the entire discovery budget before independent subject blogs are searched.
    picked = []
    indexes = {category: 0 for category in preferred}
    while len(picked) < 16:
        added = False
        for category in preferred:
            index = indexes[category]
            if index < len(by_topic[category]):
                picked.append(by_topic[category][index]); indexes[category] += 1; added = True
                if len(picked) >= 16: break
        if not added: break
    with ThreadPoolExecutor(max_workers=16) as pool:
        groups = list(pool.map(feed_items, picked))
    return [item for group in groups for item in group]

def terms(text: str):
    return [t.lower() for t in TOKEN.findall(text) if t.lower() not in STOP and not t.isdigit()]
def canonical(token: str): return ALIASES.get(token, token)
def canonical_terms(text: str):
    # Treat this unambiguous phrase as one concept without matching generic
    # "family members" or "members of the public" to political membership.
    text = re.sub(r"\bparty\s+members?\b", " party_member ", text, flags=re.I)
    return [canonical(t) for t in terms(text)]
def slug_title(url: str):
    path = urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1])
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
        canonical_match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', page, re.I)
        if canonical_match: canonical_url = urllib.parse.urljoin(final, html.unescape(canonical_match.group(1)))
        snippet = re.sub(r"\s+", " ", html.unescape(description)).strip()
        if not snippet: snippet = re.sub(r"\s+", " ", " ".join(parser.text)).strip()[:320]
        return {"url": canonical_url, "title": re.sub(r"\s+", " ", html.unescape(title)).strip() or slug_title(url), "description": snippet[:600], "publisher": parser.meta.get("og:site_name") or urllib.parse.urlsplit(final).hostname or "", "published": parser.meta.get("article:published_time") or parser.meta.get("datepublished") or parser.meta.get("date", "")}
    except Exception:
        return {"url": url, "title": slug_title(url), "description": "", "publisher": urllib.parse.urlsplit(url).hostname or "", "published": ""}

def topic_weights(meta):
    weights = Counter()
    # The headline and URL slug are strong topic evidence; description enriches context.
    for text, weight in ((meta.get("title", ""), 5), (slug_title(meta.get("url", "")), 4), (meta.get("description", ""), 2)):
        for word in canonical_terms(text):
            if len(word) >= 2: weights[word] += weight
    return weights

def search_news(meta):
    weights = topic_weights(meta)
    if len(weights) < 2: return [], list(weights)
    ranked = sorted(weights, key=lambda w: (-weights[w], -len(w), w))[:10]
    # Google News is searched in both interface languages. GDELT's Doc API searches
    # its global, multilingual news index using English-translated terms.
    # Search with alternative phrasing so feeds don't require every extracted
    # noun to appear verbatim. Ranking below still checks actual overlap.
    # Use a wider concept set in both languages. The overlap checks below keep
    # the broader discovery from admitting stories that share only generic words.
    de_terms = list(dict.fromkeys(GERMAN_FOR_ENGLISH.get(w, w) for w in ranked[:7]))
    en_terms = list(dict.fromkeys(ENGLISH_FOR_GERMAN.get(w, w) for w in ranked[:7]))
    de_query = "(" + " OR ".join('"' + w + '"' for w in de_terms) + ")"
    en_query = "(" + " OR ".join('"' + w + '"' for w in en_terms) + ")"
    queries = [
        ("google", de_query, "de", {"hl":"de", "gl":"DE", "ceid":"DE:de"}),
        ("google", en_query, "en", {"hl":"en-US", "gl":"US", "ceid":"US:en"}),
        ("gdelt", "(" + " OR ".join('"' + w + '"' for w in en_terms[:7]) + ")", "all", {}),
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
        core = set(ranked[:7])
        overlap = core & result_words
        title_overlap = core & title_words
        if len(overlap) < 2 or not title_overlap or not (overlap - BROAD_TOPICS): return
        paywall_marker = bool(re.search(r"bild\s*plus|bildplus|sz\s*plus|plus-abo|paywall|abo-artikel|subscription required|subscribe to read|\(\s*s\+\s*\)|(?<!\w)s\+(?!\w)", (title + " " + item.get("source", "")).lower()))
        if paywall_marker: return
        key = re.sub(r"[^a-z0-9]", "", title.lower())
        body_words = set(canonical_terms(item.get("description", "")))
        matched_weight = sum(weights[w] * (1.0 if w in title_overlap else 0.45 if w in body_words else 0.0) for w in core_topics)
        raw_score = min(99, round(100 * matched_weight / total_topic_weight))
        score = min(99, round(raw_score + (100 - raw_score) * 0.08))
        if source_title_words and source_title_words == title_words: score = 100
        result = {"title":title, "description":item.get("description", "")[:360], "url":link, "source":item.get("source") or host, "lang":item.get("language", "en"), "published":item.get("published", ""), "score":score, "matchedTopics":list(overlap), "provider":provider, "sourceKind":item.get("sourceKind", "newsroom"), "sourceTopic":item.get("sourceTopic", ""), "catalogued":bool(item.get("catalogued"))}
        current = candidates.get(key)
        if current is None or score > current["score"] or (result["catalogued"] and not current.get("catalogued")): candidates[key] = result
    for provider, query, requested_lang, extras in queries:
        if not query.strip(): continue
        try:
            if provider == "google":
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
                        "language":requested_lang
                    })
            else:
                params = urllib.parse.urlencode({"query":query, "mode":"artlist", "format":"json", "maxrecords":"75", "timespan":"3months", "sort":"HybridRel"})
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
            continue
        for item in records: consider(item, provider)
    for item in search_curated_feeds(set(ranked)):
        consider(item, "kuratiert")
    # Check only the highest relevance candidates. Publisher markup is decisive;
    # unknown/blocked/ambiguous pages stay hidden to avoid frustrating readers.
    matches = {}
    top = sorted(candidates.items(), key=lambda item: -item[1]["score"])[:24]
    with ThreadPoolExecutor(max_workers=16) as pool:
        checked = list(pool.map(lambda pair: verify_free_access(pair[1]["url"], source_host), top))
    for (key, result), (access, final_url, signals) in zip(top, checked):
        if access in ("verified_free", "likely_free"):
            result["access"] = access
            result["url"] = final_url
            result["qualitySignals"] = signals
            matches[key] = result
    print("Zugriffsprüfung: %d Kandidaten, %d als frei bestätigt/lesbar gezeigt, %d wegen Paywall oder unklarem Zugriff ausgeblendet." % (len(candidates), len(matches), len(candidates) - len(matches)), flush=True)
    results = sorted(matches.values(), key=lambda x: (-x["score"], x["title"].lower()))
    return results[:12], ranked

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(PREVIEW), **kwargs)
    def do_GET(self):
        if self.path.startswith("/api/search?"):
            params = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query); target = (params.get("url") or [""])[0]
            try:
                if not target: raise ValueError("Füge zuerst einen Artikellink ein.")
                meta = read_metadata(target)
                results, topics = search_news(meta)
                payload = {"ok":True,"metadata":meta,"topics":topics,"results":results,"message":"" if results else "Keine passenden Artikel gefunden. Versuche es später mit mehr Kontext oder einer anderen Suchanfrage."}
            except ValueError as e: payload = {"ok":False,"error":str(e)}
            except Exception: payload = {"ok":False,"error":"Metadaten oder thematische Suche konnten gerade nicht ausgewertet werden."}
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(data); return
        super().do_GET()
    def log_message(self, fmt, *args):
        message = fmt % args
        if "/api/search" in message: message = "API-Suche (Link nicht protokolliert)"
        print("%s - %s" % (self.client_address[0], message))

if __name__ == "__main__":
    print("Freilesen-Vorschau: http://localhost:8765 (Android-Emulator: http://10.0.2.2:8765)")
    ThreadingHTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
