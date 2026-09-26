#!/usr/bin/env python3
"""Freilesen local preview and link-driven related-news search."""
from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
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
TOKEN = re.compile(r"[\wÄÖÜäöüß]{2,}", re.UNICODE)
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
PUBLISHER_DOMAINS = {"sueddeutsche.de":"sueddeutsche.de", "sz.de":"sueddeutsche.de"}

def same_publisher(host: str, source_host: str):
    clean = lambda value: (value or "").lower().removeprefix("www.")
    host, source_host = clean(host), clean(source_host)
    if host == source_host or host.endswith("." + source_host) or source_host.endswith("." + host): return True
    return PUBLISHER_DOMAINS.get(host, host) == PUBLISHER_DOMAINS.get(source_host, source_host)

class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta = {}; self.title = ""; self.in_title = False; self.text = []; self._skip = 0; self.article_depth = 0; self.article_text = []; self.main_depth = 0; self.main_text = []; self.paywall_markup = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = a.get("property") or a.get("name") or a.get("itemprop")
            if key and a.get("content"): self.meta[key.lower()] = a["content"].strip()
        elif tag == "title": self.in_title = True
        if tag == "article": self.article_depth += 1
        if tag == "main": self.main_depth += 1
        if tag in ("div", "section", "aside") and re.search(r"paywall|pay-wall|subscriber.only|premium.content|paid.content|metered.content|registration.wall", (a.get("id", "") + " " + a.get("class", "")).lower()): self.paywall_markup = True
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

PAYWALL_TEXT = re.compile(r"(?:subscribe\s+to\s+(?:read|continue)|subscription\s+(?:required|only)|sign\s+in\s+to\s+continue\s+reading|this\s+article\s+is\s+for\s+subscribers|only\s+available\s+to\s+subscribers|already\s+a\s+subscriber|nur\s+für\s+abonnenten|abo\s+erforderlich|weiterlesen\s+mit\s+(?:ihrem|deinem)\s+abo|plus-artikel|plus\s+freischalten|artikel\s+ist\s+kostenpflichtig|zahlungspflichtig|kostenpflichtig\s+lesen|zum\s+weiterlesen\s+abo)", re.I)

def verify_free_access(url: str, source_host: str = ""):
    """Classify live public access, excluding explicit paywalls and dead pages."""
    try:
        final_url, page = fetch(url, 1_800_000, timeout=7)
        final_host = urllib.parse.urlsplit(final_url).hostname or ""
        if same_publisher(final_host, source_host): return ("same_source", final_url)
        parser = MetadataParser(); parser.feed(page)
        lowered = page.lower()
        # Structured publisher signals are reliable in both directions.
        if re.search(r'"isAccessibleForFree"\s*:\s*false|isaccessibleforfree\s*["\']?\s*content\s*=\s*["\']false', lowered):
            return ("paywall", final_url)
        page_text = html.unescape(" ".join(parser.text))
        if PAYWALL_TEXT.search(page_text): return ("paywall", final_url)
        if re.search(r'"isAccessibleForFree"\s*:\s*true', lowered):
            return ("verified_free", final_url)
        # A page shell or short search teaser isn't enough. Many publishers use
        # <main> rather than <article>; accept substantive readable body text.
        article_text = re.sub(r"\s+", " ", " ".join(parser.article_text)).strip()
        main_text = re.sub(r"\s+", " ", " ".join(parser.main_text)).strip()
        if len(article_text) >= 650: return ("likely_free" if parser.paywall_markup else "verified_free", final_url)
        if len(main_text) >= 1000: return ("likely_free", final_url)
        if len(page_text) >= 1800 and not parser.paywall_markup: return ("likely_free", final_url)
        return ("unknown", final_url)
    except urllib.error.HTTPError as e:
        return ("unavailable" if e.code in (404, 410) else "unknown", url)
    except Exception:
        return ("unknown", url)

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
                    records.append({"title":item.get("title", "").strip(), "url":item.get("url", "").strip(), "source":item.get("domain", "").strip(), "description":"", "published":item.get("seendate", ""), "language":lang})
        except Exception:
            continue
        for item in records:
            title, link = item["title"], item["url"]
            if not title or not link: continue
            host = (urllib.parse.urlsplit(link).hostname or "").lower()
            if same_publisher(host, source_host) or same_publisher(host, item["source"]) or same_publisher(item["source"], source_host): continue
            text = title + " " + item["description"]
            result_words = set(canonical_terms(text))
            title_words = set(canonical_terms(title))
            core = set(ranked[:7])
            overlap = core & result_words
            title_overlap = core & title_words
            if len(overlap) < 2 or not title_overlap or not (overlap - BROAD_TOPICS): continue
            paywall_marker = bool(re.search(r"bild\s*plus|bildplus|sz\s*plus|plus-abo|paywall|abo-artikel|subscription required|subscribe to read|\(\s*s\+\s*\)|(?<!\w)s\+(?!\w)", (title + " " + item["source"]).lower()))
            if paywall_marker: continue
            key = re.sub(r"[^a-z0-9]", "", title.lower())
            body_words = set(canonical_terms(item["description"]))
            # Score shared meaning only, not exact title word order. 100 is
            # reserved for identical normalized headlines; partial topic overlap
            # remains visibly lower even when the search index returned it.
            matched_weight = sum(weights[w] * (1.0 if w in title_overlap else 0.45 if w in body_words else 0.0) for w in core_topics)
            raw_score = min(99, round(100 * matched_weight / total_topic_weight))
            # A small optimistic calibration offsets headline/metadata sparsity;
            # it can't turn a weak match into a strong one.
            score = min(99, round(raw_score + (100 - raw_score) * 0.08))
            target_title_words = set(canonical_terms(title))
            if source_title_words and source_title_words == target_title_words: score = 100
            result = {"title":title, "description":item["description"][:360], "url":link, "source":item["source"] or host, "lang":item["language"], "published":item["published"], "score":score, "matchedTopics":list(overlap), "provider":provider}
            current = candidates.get(key)
            if current is None or score > current["score"]: candidates[key] = result
    # Check a bounded set of highest relevance candidates against their live
    # publisher pages. Search-index snippets and HTTP status alone don't prove
    # that a story is free. Unknown/blocked/ambiguous pages are excluded.
    matches = {}
    top = sorted(candidates.items(), key=lambda item: -item[1]["score"])[:40]
    with ThreadPoolExecutor(max_workers=10) as pool:
        checked = list(pool.map(lambda pair: verify_free_access(pair[1]["url"], source_host), top))
    for (key, result), (access, final_url) in zip(top, checked):
        if access not in ("paywall", "unavailable"):
            result["access"] = access
            result["url"] = final_url
            matches[key] = result
    print("Suchprüfung: %d thematische Kandidaten, %d gezeigt, %d unbestätigt." % (len(candidates), len(matches), sum(1 for x in matches.values() if x["access"] == "unknown")), flush=True)
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
