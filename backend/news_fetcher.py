"""
Fetches news articles about Black hair from Google News RSS feeds.
No API key required. Returns deduplicated article list for blog_writer.
"""
import logging
import re
import time
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests
from config import DB_PATH, NEWS_QUERIES, NEWS_MAX_PER_QUERY

log = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news_articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            url         TEXT NOT NULL UNIQUE,
            source      TEXT,
            published   TEXT,
            fetched_at  TEXT NOT NULL
        )
    """)
    conn.commit()


def _parse_pubdate(raw: str) -> str:
    """Convert RFC-2822 pubDate to ISO-8601."""
    try:
        return parsedate_to_datetime(raw).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _clean_title(raw: str) -> str:
    """Strip trailing '- Source Name' that Google appends to titles."""
    return re.sub(r"\s*-\s*[^-]{2,60}$", "", raw).strip()


def _fetch_query(query: str) -> list[dict]:
    params = {
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }
    try:
        resp = requests.get(
            GOOGLE_NEWS_RSS, params=params, headers=HEADERS, timeout=15
        )
        resp.raise_for_status()
    except Exception as e:
        log.error("RSS fetch failed for %r: %s", query, e)
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        log.error("RSS parse error for %r: %s", query, e)
        return []

    articles = []
    for item in root.findall(".//item")[:NEWS_MAX_PER_QUERY]:
        title = _clean_title(item.findtext("title") or "")
        url = item.findtext("link") or ""
        source = item.findtext("source") or ""
        pub = _parse_pubdate(item.findtext("pubDate") or "")
        if title and url:
            articles.append(
                {"title": title, "url": url, "source": source, "published": pub}
            )
    return articles


def fetch_articles() -> list[dict]:
    """
    Fetches from all NEWS_QUERIES, deduplicates by title, stores new articles
    in SQLite, and returns the fresh batch for today's blog post.
    """
    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)
    now = datetime.now(timezone.utc).isoformat()

    seen_titles: set[str] = set()
    fresh: list[dict] = []

    for query in NEWS_QUERIES:
        log.info("Fetching news: %r", query)
        for art in _fetch_query(query):
            norm = art["title"].lower().strip()
            if norm in seen_titles:
                continue
            seen_titles.add(norm)

            # Store in DB (UNIQUE on url handles cross-run dedup)
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO news_articles
                       (title, url, source, published, fetched_at)
                       VALUES (?,?,?,?,?)""",
                    (art["title"], art["url"], art["source"], art["published"], now),
                )
                conn.commit()
            except Exception as e:
                log.warning("DB insert failed for %r: %s", art["title"], e)

            fresh.append(art)

        time.sleep(1.0)   # polite delay between RSS requests

    conn.close()
    log.info("News fetch complete: %d unique articles", len(fresh))
    return fresh
