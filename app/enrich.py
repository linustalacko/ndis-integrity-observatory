"""Enrichment: crawl regulator/AFP news for NDIS enforcement stories and match
them to register entities by name.

Primary source: AFP news centre (scriptable; carries Fraud Fusion Taskforce
releases naming charged/banned operators and describing conduct). The NDIS
Commission and NDIA sites are WAF-blocked for scripts; their items can be added
via the browser-capture path later.

CLI: python -m app.enrich [pages]
"""
from __future__ import annotations

import re
import sys

import httpx

from .db import connect
from .ingest import norm_name

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
AFP_LIST = "https://www.afp.gov.au/news-centre?title=NDIS&page={page}"
AFP_BASE = "https://www.afp.gov.au"


def strip_tags(html: str) -> str:
    html = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", html)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def crawl_afp(conn, pages: int = 5) -> int:
    added = 0
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as client:
        for page in range(pages):
            try:
                html = client.get(AFP_LIST.format(page=page)).text
            except Exception:
                break
            links = sorted(set(re.findall(
                r'href="(/news-centre/media-release/[^"]+)"', html)))
            if not links:
                break
            for path in links:
                url = AFP_BASE + path
                if conn.execute("SELECT 1 FROM articles WHERE url=?", (url,)).fetchone():
                    continue
                try:
                    art = client.get(url).text
                except Exception:
                    continue
                title_m = (re.search(r'property="og:title" content="([^"]+)"', art)
                           or re.search(r"<title>([\s\S]*?)</title>", art))
                title = strip_tags(title_m.group(1)).replace("| Australian Federal Police", "").strip() \
                    if title_m else path
                date_m = re.search(r'datetime="(\d{4}-\d{2}-\d{2})', art)
                body_m = re.search(r"<article[\s\S]*?</article>", art) or \
                    re.search(r"<main[\s\S]*?</main>", art)
                body = strip_tags(body_m.group(0)) if body_m else strip_tags(art)
                conn.execute(
                    "INSERT OR REPLACE INTO articles (url, source, title, published, body) "
                    "VALUES (?,?,?,?,?)",
                    (url, "afp", title, date_m.group(1) if date_m else "", body[:20000]))
                added += 1
            conn.commit()
    return added


def match_articles(conn) -> int:
    """Match register entity names inside article bodies (person names and
    distinctive org names only — short/common tokens skipped)."""
    conn.execute("DELETE FROM article_matches")
    actions = conn.execute(
        "SELECT action_id, name, norm_name, is_person FROM actions").fetchall()
    articles = conn.execute("SELECT url, body, title FROM articles").fetchall()
    n = 0
    for art in articles:
        hay = norm_name(art["body"] + " " + art["title"])
        for act in actions:
            nn = act["norm_name"]
            if len(nn) < 10 or len(nn.split()) < 2:
                continue  # too collision-prone
            if nn in hay:
                conn.execute("INSERT OR IGNORE INTO article_matches (url, action_id, "
                             "matched_on) VALUES (?,?,?)", (art["url"], act["action_id"], nn))
                n += 1
    conn.commit()
    return n


def main(argv: list[str]) -> int:
    pages = int(argv[0]) if argv else 8
    conn = connect()
    added = crawl_afp(conn, pages)
    total = conn.execute("SELECT COUNT(*) c FROM articles").fetchone()["c"]
    matches = match_articles(conn)
    print(f"articles: +{added} new, {total} total | name matches into register: {matches}")
    for r in conn.execute("""
            SELECT a.name, ar.title, ar.published FROM article_matches m
            JOIN actions a USING(action_id) JOIN articles ar ON ar.url = m.url
            GROUP BY m.url, a.norm_name LIMIT 12"""):
        print(f"  {r['name'][:30]:30} <- {r['published']} {r['title'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
