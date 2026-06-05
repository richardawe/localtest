"""
Fetches images from the Unsplash API and stores them in SQLite.
Deduplication uses Unsplash photo ID (globally unique, stable).
Relevance filtering uses llama3.1:8b on image text metadata.
"""
import logging
import time
import sqlite3
import requests
import ollama
from config import (
    UNSPLASH_ACCESS_KEY, UNSPLASH_API_BASE, UNSPLASH_RESULTS_PER_PAGE,
    DB_PATH, OLLAMA_MODEL, RELEVANCE_PROMPT,
)

log = logging.getLogger(__name__)

HEADERS = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            unsplash_id       TEXT PRIMARY KEY,
            url_regular       TEXT NOT NULL,
            url_thumb         TEXT NOT NULL,
            url_full          TEXT NOT NULL,
            alt_description   TEXT,
            description       TEXT,
            photographer_name TEXT,
            photographer_url  TEXT,
            unsplash_photo_url TEXT,
            tags              TEXT,
            search_query      TEXT,
            era               TEXT,
            style_category    TEXT,
            fetched_at        TEXT NOT NULL
        )
    """)
    conn.commit()


def _is_relevant(alt: str, desc: str, tags: str) -> bool:
    """Ask llama3.1:8b if this image metadata suggests a hair-related photo."""
    prompt = RELEVANCE_PROMPT.format(
        alt=alt or "",
        desc=desc or "",
        tags=tags or "",
    )
    try:
        resp = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            options={"num_predict": 5, "temperature": 0.0},
        )
        answer = resp["response"].strip().upper()
        return answer.startswith("YES")
    except Exception as e:
        log.warning("Relevance check failed, defaulting to include: %s", e)
        return True


def _search(query: str, page: int = 1) -> list[dict]:
    url = f"{UNSPLASH_API_BASE}/search/photos"
    params = {
        "query": query,
        "per_page": UNSPLASH_RESULTS_PER_PAGE,
        "page": page,
        "orientation": "portrait",
        "content_filter": "high",
    }
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("results", [])


def fetch_and_store(queries: list[dict]) -> int:
    """
    Runs all search queries, filters for relevance, stores new images.
    Returns count of newly inserted images.
    """
    if not UNSPLASH_ACCESS_KEY:
        log.error("UNSPLASH_ACCESS_KEY not set — skipping image fetch")
        return 0

    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)

    inserted = 0
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    for item in queries:
        query = item["query"]
        era = item.get("era")
        category = item.get("category", "current")

        log.info("Searching Unsplash: %r", query)
        try:
            results = _search(query)
        except requests.HTTPError as e:
            log.error("Unsplash API error for %r: %s", query, e)
            time.sleep(2)
            continue
        except Exception as e:
            log.error("Unexpected error fetching %r: %s", query, e)
            continue

        for photo in results:
            pid = photo.get("id")
            if not pid:
                continue

            # Skip duplicates by Unsplash ID
            exists = conn.execute(
                "SELECT 1 FROM photos WHERE unsplash_id = ?", (pid,)
            ).fetchone()
            if exists:
                continue

            alt = photo.get("alt_description") or ""
            desc = photo.get("description") or ""
            raw_tags = photo.get("tags") or []
            tags_str = ", ".join(t.get("title", "") for t in raw_tags if t.get("title"))

            if not _is_relevant(alt, desc, tags_str):
                log.debug("Filtered out (not relevant): %s", pid)
                continue

            urls = photo.get("urls", {})
            user = photo.get("user", {})
            links = photo.get("links", {})

            conn.execute(
                """
                INSERT OR IGNORE INTO photos
                  (unsplash_id, url_regular, url_thumb, url_full,
                   alt_description, description,
                   photographer_name, photographer_url, unsplash_photo_url,
                   tags, search_query, era, style_category, fetched_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    pid,
                    urls.get("regular", ""),
                    urls.get("thumb", ""),
                    urls.get("full", ""),
                    alt,
                    desc,
                    user.get("name", ""),
                    user.get("links", {}).get("html", ""),
                    links.get("html", ""),
                    tags_str,
                    query,
                    era,
                    category,
                    now,
                ),
            )
            inserted += 1

        conn.commit()
        # Respect Unsplash rate limits between queries
        time.sleep(1.5)

    conn.close()
    log.info("Image fetch complete: %d new images inserted", inserted)
    return inserted
