"""
Picks one cover image per blog post from Unsplash. Unlike image_fetcher.py
(which bulk-stores a gallery), this needs exactly one image per run —
landscape, not already used for a previous ngr.ltd post, with attribution
tracked per Unsplash API guidelines (a download-tracking ping alongside the
required photographer credit).
"""
import logging
import random
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Optional

import requests

from config import UNSPLASH_ACCESS_KEY, UNSPLASH_API_BASE
from config_ngr import NGR_DB_PATH, NGR_IMAGE_QUERIES

log = logging.getLogger(__name__)

HEADERS = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ngr_used_images (
            unsplash_id TEXT PRIMARY KEY,
            used_at     TEXT NOT NULL
        )
    """)
    conn.commit()


def _mark_used(conn: sqlite3.Connection, unsplash_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO ngr_used_images (unsplash_id, used_at) VALUES (?, ?)",
        (unsplash_id, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def _track_download(download_location: str) -> None:
    """
    Unsplash API guidelines require pinging this endpoint whenever a photo
    is displayed, separate from hotlinking the image itself. Best-effort —
    never blocks post creation on a tracking failure.
    """
    try:
        requests.get(download_location, headers=HEADERS, timeout=10)
    except Exception as e:
        log.warning("Unsplash download-tracking ping failed: %s", e)


def pick_cover_image(category: str) -> Optional[Dict]:
    """
    Returns {url, credit, credit_url} for an unused image matching the
    category's query, or None if Unsplash is unavailable or exhausted.
    """
    query = NGR_IMAGE_QUERIES.get(category)
    if not UNSPLASH_ACCESS_KEY or not query:
        return None

    conn = sqlite3.connect(NGR_DB_PATH)
    _init_db(conn)

    try:
        resp = requests.get(
            f"{UNSPLASH_API_BASE}/search/photos",
            headers=HEADERS,
            params={
                "query": query,
                "per_page": 20,
                "orientation": "landscape",
                "content_filter": "high",
            },
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except Exception as e:
        log.error("Unsplash search failed for %r: %s", query, e)
        conn.close()
        return None

    random.shuffle(results)
    for photo in results:
        pid = photo.get("id")
        if not pid:
            continue
        already_used = conn.execute(
            "SELECT 1 FROM ngr_used_images WHERE unsplash_id = ?", (pid,)
        ).fetchone()
        if already_used:
            continue

        user = photo.get("user", {})
        credit_url = user.get("links", {}).get("html", "")
        if credit_url:
            credit_url += ("&" if "?" in credit_url else "?") + "utm_source=ngr_ltd&utm_medium=referral"

        _mark_used(conn, pid)
        conn.close()

        download_location = photo.get("links", {}).get("download_location", "")
        if download_location:
            _track_download(download_location)

        return {
            "url": photo.get("urls", {}).get("regular", ""),
            "credit": user.get("name", ""),
            "credit_url": credit_url,
        }

    conn.close()
    log.warning("No unused Unsplash image found for category %r", category)
    return None
