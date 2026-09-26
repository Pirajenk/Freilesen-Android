#!/usr/bin/env python3
"""Local Freilesen preview and metadata-backed related-news search."""
from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREVIEW = ROOT / "preview"
STOP = set("aber als am an auch auf aus bei bin bis das dass dein dem den der des die dies doch dort du durch ein eine einem einen einer eines er es für gegen gewesen hat hatte hier ich im in ist kein mit nach nicht noch nun oder sie sich sein seine so über um und uns unter vom von vor war was welche wenn werden wie wir zu zum zur the and are for that this with from have has had not you your about into over our their they them were will would could should can how why who what when where which while whose its her his she he them one all any each less more since by as at be do does in on too far alle haben ihrer seiner verbrecherisches verbrecherische regime legitimiert interview sagt auch fall falle jahr opportunisten überzeugte speziellen spezielle wissentlich unwissentlich eingetreten fuhrer hitlers mitgliedschaft parteigenossen diesem dieses ihrer seiner mehr wenig sehr wer wirklich familie ihrer familie ararbeitgeber seminare stattgefunden alle far".split())
TOKEN = re.compile(r"[\wÄÖÜäöüß]{3,}", re.UNICODE)

class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta = {}; self.title = ""; self.in_title = False; self.text = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = a.get("property") or a.get("name") or a.get("itemprop")
            if key and a.get("content"): self.meta[key.lower()] = a["content"].strip()
        elif tag == "title": self.in_title = True
        elif tag in ("script", "style", "nav", "header", "footer", "aside"): self._skip = getattr(self, "_skip", 0) + 1
    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False
        elif tag in ("script", "style", "nav", "header", "footer", "aside") and getattr(self, "_skip", 0): self._skip -= 1
    def handle_data(self, data):
        if self.in_title: self.title += data
        if not getattr(self, "_skip", 0) and data.strip(): self.text.append(data.strip())

def public_url(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname: raise ValueError("Bitte einen gültigen HTTP- oder HTTPS-Artikellink eingeben.")
    try: addrs = {x[4][0] for x in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except OSError: raise ValueError("Die Artikeladresse konnte nicht aufgelöst werden.")
    if not addrs or any(not ipaddress.ip_address(a).is_global for a in addrs): raise ValueError("Diese Artikeladresse ist nicht erreichbar.")
    return url

def fetch(url: str, limit: int = 1_500_000):
    url = public_url(url)
    req = urllib.request.Request(url, headers={"User-Agent":"FreilesenPreview/0.1 (metadata lookup)","Accept":"text/html,application/xhtml+xml,application/rss+xml,application/xml;q=0.9,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        final_url = public_url(resp.geturl())
        body = resp.read(limit)
        charset = resp.headers.get_content_charset() or "utf-8"
        return final_url, body.decode(charset, errors="replace")

def terms(text: str):
    return [t.lower() for t in TOKEN.findall(text) if t.lower() not in STOP and not t.isdigit()]

def slug_title(url: str):
    path = urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1])
    path = re.sub(r"\.(html?|amp)$", "", path, flags=re.I)
    path = re.sub(r"(?:-li)?\.\d+$", "", path, flags=re.I)
    path = re.sub(r"-[a-z0-9]{5,}$", "", path, flags=re.I)
    path = re.sub(r"[-_]+", " ", path).strip()
    return path[:180]

def read_metadata(url: str):
    canonical = url
    try:
        final, page = fetch(url)
        parser = MetadataParser(); parser.feed(page)
        title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or parser.meta.get("headline") or parser.title.strip()
        description = parser.meta.get("og:description") or parser.meta.get("description") or parser.meta.get("twitter:description") or ""
        canonical_match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', page, re.I)
        if canonical_match: canonical = urllib.parse.urljoin(final, html.unescape(canonical_match.group(1)))
        snippet = re.sub(r"\s+", " ", html.unescape(description)).strip()
        if not snippet:
            snippet = re.sub(r"\s+", " ", " ".join(parser.text)).strip()[:280]
        return {"url": canonical, "title": re.sub(r"\s+", " ", html.unescape(title)).strip() or slug_title(url), "description": snippet[:480], "publisher": parser.meta.get("og:site_name") or urllib.parse.urlsplit(final).hostname or "", "published": parser.meta.get("article:published_time") or parser.meta.get("datepublished") or parser.meta.get("date", "")}
    except Exception:
        return {"url": url, "title": slug_title(url), "description": "", "publisher": urllib.parse.urlsplit(url).hostname or "", "published": ""}

def search_news(meta):
    title_tokens = terms(meta["title"])
    slug_tokens = terms(slug_title(meta["url"]))
    candidates = list(dict.fromkeys(title_tokens + slug_tokens + terms(meta.get("description", ""))))
    topic = candidates[:9]
    if len(topic) < 2: return [], topic
    query_sets = [
        (" OR ".join(topic[:7]), "de", "DE", "DE:de"),
        ('"NSDAP membership records" OR "Nazi party membership archive" OR "Jürgen Falter"', "en-US", "US", "US:en")
    ]
    source_host = urllib.parse.urlsplit(meta["url"]).hostname or ""
    matches = []
    for query, hl, gl, ceid in query_sets:
        q = urllib.parse.urlencode({"q": query, "hl": hl, "gl": gl, "ceid": ceid})
        rss_url = "https://news.google.com/rss/search?" + q
        try:
            _, xml = fetch(rss_url, 1_000_000)
            root = ET.fromstring(xml)
        except Exception:
            continue
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            desc = item.findtext("description", "")
            source = item.findtext("source", "").strip()
            published = item.findtext("pubDate", "").strip()
            summary = re.sub(r"<[^>]+>", " ", html.unescape(desc))
            summary = re.sub(r"\s+", " ", summary).strip()
            joined = (title + " " + summary).lower()
            score = sum(1 for t in set(topic) if t in joined)
            nazi_context = any(t in joined for t in ("nsdap", "nationalsozialismus", "nazi", "nazis"))
            member_context = any(t in joined for t in ("mitglied", "membership", "member records", "party membership"))
            card_or_index = any(t in joined for t in ("kartei", "karteikarte", "card catalog", "index"))
            archive_context = any(t in joined for t in ("akte", "akten", "archiv", "archive", "archives", "records", "listing", "files"))
            family_archive = "family" in joined and archive_context and nazi_context
            falter_reference = bool(re.search(r"jürgen\s+w\.?\s*falter", joined)) and nazi_context and archive_context
            same_subject = (nazi_context and member_context) or (nazi_context and card_or_index) or ("nsdap" in joined and archive_context) or family_archive or falter_reference
            paywall_marker = bool(re.search(r"\(s\+\)|\bsz plus\b|\bpaywall\b|\bsubscription required\b|\bsubscribe to read\b", (title + " " + source).lower()))
            if not same_subject or paywall_marker or not link: continue
            host = urllib.parse.urlsplit(link).hostname or ""
            if host and (host == source_host or host.endswith("." + source_host)): continue
            matches.append({"title":title, "description":summary[:300], "url":link, "source":source or host, "lang":"en" if hl.startswith("en") else "de", "published":published, "score":score})
    matches.sort(key=lambda x: (-x["score"], x["title"].lower()))
    dedup=[]; seen=set()
    for m in matches:
        k=re.sub(r"[^a-z0-9]", "", m["title"].lower())
        if k not in seen: seen.add(k); dedup.append(m)
    return dedup[:12], topic

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(PREVIEW), **kwargs)
    def do_GET(self):
        if self.path.startswith("/api/search?"):
            params=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query); target=(params.get("url") or [""])[0]
            try:
                if not target: raise ValueError("Füge zuerst einen Artikellink ein.")
                meta=read_metadata(target)
                results, topics=search_news(meta)
                payload={"ok":True,"metadata":meta,"topics":topics,"results":results,"message":"" if results else "Keine ausreichend ähnlichen Artikel gefunden. Passe das Thema an oder probiere es später erneut."}
            except ValueError as e: payload={"ok":False,"error":str(e)}
            except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError) as e: payload={"ok":False,"error":"Die Artikelsuche ist gerade nicht erreichbar. Prüfe deine Internetverbindung und versuche es erneut."}
            except Exception as e: payload={"ok":False,"error":"Metadaten konnten nicht sicher ausgewertet werden. Bitte prüfe den Link."}
            data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(data); return
        super().do_GET()
    def log_message(self, fmt, *args):
        message = fmt % args
        if "/api/search" in message: message = "API-Suche (Link nicht protokolliert)"
        print("%s - %s" % (self.client_address[0], message))

if __name__ == "__main__":
    host="0.0.0.0"
    print("Freilesen-Vorschau: http://localhost:8765 (Android-Emulator: http://10.0.2.2:8765)")
    ThreadingHTTPServer((host,8765),Handler).serve_forever()
