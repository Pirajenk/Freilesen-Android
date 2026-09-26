#!/usr/bin/env python3
"""Freilesen local preview and link-driven related-news search."""
from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
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
    "mitgliederkartei":"membership", "mitgliedskartei":"membership", "mitgliedskarteien":"membership", "mitgliedschaft":"membership", "mitglied":"membership", "members":"membership", "membership":"membership",
    "kartei":"records", "karteikarte":"records", "karteikarten":"records", "akten":"records", "akte":"records", "archive":"records", "archives":"records", "archiv":"records", "archiviert":"records", "records":"records", "files":"records", "file":"records",
}
GERMAN_FOR_ENGLISH = {"india":"indien", "boy":"junge", "child":"kind", "grow":"wuchs", "poverty":"armut", "slum":"slum", "nazi":"nazi", "membership":"mitgliedschaft", "records":"akten"}

class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta = {}; self.title = ""; self.in_title = False; self.text = []; self._skip = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = a.get("property") or a.get("name") or a.get("itemprop")
            if key and a.get("content"): self.meta[key.lower()] = a["content"].strip()
        elif tag == "title": self.in_title = True
        elif tag in ("script", "style", "nav", "header", "footer", "aside"): self._skip += 1
    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False
        elif tag in ("script", "style", "nav", "header", "footer", "aside") and self._skip: self._skip -= 1
    def handle_data(self, data):
        if self.in_title: self.title += data
        if not self._skip and data.strip(): self.text.append(data.strip())

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
def canonical_terms(text: str): return [canonical(t) for t in terms(text)]
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
    de_terms = [GERMAN_FOR_ENGLISH.get(w, w) for w in ranked[:5]]
    en_terms = ranked[:5]
    queries = [
        ("google", " ".join(de_terms), "de", {"hl":"de", "gl":"DE", "ceid":"DE:de"}),
        ("google", " ".join(en_terms), "en", {"hl":"en-US", "gl":"US", "ceid":"US:en"}),
        ("gdelt", "(" + " OR ".join('"' + w + '"' for w in en_terms[:7]) + ")", "all", {}),
    ]
    source_host = (urllib.parse.urlsplit(meta.get("url", "")).hostname or "").lower()
    source_title_words = set(canonical_terms(meta.get("title", "")))
    # Denominate by all extracted topical evidence, including weaker description
    # terms. Otherwise unrelated matches can score artificially high.
    total_topic_weight = sum(weights.values()) or 1
    matches = {}
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
            if host == source_host or (source_host and host.endswith("." + source_host)): continue
            text = title + " " + item["description"]
            result_words = set(canonical_terms(text))
            title_words = set(canonical_terms(title))
            core = set(ranked[:7])
            overlap = core & result_words
            title_overlap = core & title_words
            if len(overlap) < 2 or not title_overlap: continue
            paywall_marker = bool(re.search(r"\b(?:bild\s*plus|bildplus|sz\s*plus|plus-abo|s\+|paywall|abo-artikel|subscription required|subscribe to read)\b", (title + " " + item["source"]).lower()))
            if paywall_marker: continue
            key = re.sub(r"[^a-z0-9]", "", title.lower())
            body_words = set(canonical_terms(item["description"]))
            # Score shared meaning only, not exact title word order. 100 is
            # reserved for identical normalized headlines; partial topic overlap
            # remains visibly lower even when the search index returned it.
            matched_weight = sum(weights[w] * (1.0 if w in title_overlap else 0.35 if w in body_words else 0.0) for w in weights)
            score = min(99, round(100 * matched_weight / total_topic_weight))
            target_title_words = set(canonical_terms(title))
            if source_title_words and source_title_words == target_title_words: score = 100
            current = matches.get(key)
            result = {"title":title, "description":item["description"][:360], "url":link, "source":item["source"] or host, "lang":item["language"], "published":item["published"], "score":score, "matchedTopics":list(overlap), "provider":provider}
            if current is None or score > current["score"]: matches[key] = result
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
                payload = {"ok":True,"metadata":meta,"topics":topics,"results":results,"message":"" if results else "Keine ausreichend ähnlichen Artikel gefunden. Die Suche verwendet die erkannten Linkthemen; versuche es mit dem direkten Artikel-Link erneut."}
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
