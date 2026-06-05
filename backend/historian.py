"""
Builds Wikipedia-grounded historical decade narratives using RAG.
Runs once per day (checked in main.py). Never hallucinates — the prompt
explicitly restricts Ollama to the provided source text only.
"""
import logging
import sqlite3
import requests
import ollama
from config import (
    WIKIPEDIA_API_BASE, WIKIPEDIA_ARTICLES,
    ERA_QUERIES, OLLAMA_MODEL, DB_PATH,
)

log = logging.getLogger(__name__)

DECADE_NARRATIVE_PROMPT = """You are a cultural historian. Using ONLY the source material provided below, write a
150-word paragraph describing Black and African women's hairstyles and hair culture during the {decade}.

Source material:
{sources}

Rules:
- Do not add any facts not present in the source material.
- Write in an engaging, celebratory, and educational tone.
- Focus specifically on hairstyles, hair culture, and identity.
- Output only the paragraph, no title or preamble.

If the source material does not contain enough information about this decade, write what you can from the
available text and acknowledge that documentation from this era is limited."""


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wikipedia_cache (
            article   TEXT PRIMARY KEY,
            extract   TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decade_narratives (
            decade     TEXT PRIMARY KEY,
            narrative  TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()


def _fetch_wikipedia_extract(article: str) -> str | None:
    url = f"{WIKIPEDIA_API_BASE}/page/summary/{article}"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "HairTrendsApp/1.0"})
        resp.raise_for_status()
        data = resp.json()
        return data.get("extract", "")
    except Exception as e:
        log.error("Failed to fetch Wikipedia article %r: %s", article, e)
        return None


def refresh_wikipedia_cache() -> None:
    """Fetches all configured Wikipedia articles and stores extracts in SQLite."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)

    for article in WIKIPEDIA_ARTICLES:
        extract = _fetch_wikipedia_extract(article)
        if extract:
            conn.execute(
                "INSERT OR REPLACE INTO wikipedia_cache (article, extract, fetched_at) VALUES (?,?,?)",
                (article, extract, now),
            )
            log.info("Cached Wikipedia article: %s", article)

    conn.commit()
    conn.close()


def _get_all_extracts(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT article, extract FROM wikipedia_cache").fetchall()
    if not rows:
        return ""
    return "\n\n".join(f"[{article}]\n{extract}" for article, extract in rows)


def update_decade_narratives() -> None:
    """
    Generates a grounded narrative for each decade using Wikipedia context.
    Only regenerates if the decade entry is missing or the Wikipedia cache
    was refreshed today.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)

    # Refresh Wikipedia cache first
    refresh_wikipedia_cache()

    sources = _get_all_extracts(conn)
    if not sources:
        log.warning("No Wikipedia source material available — skipping decade narratives")
        conn.close()
        return

    for decade in ERA_QUERIES:
        existing = conn.execute(
            "SELECT updated_at FROM decade_narratives WHERE decade = ?", (decade,)
        ).fetchone()

        # Regenerate at most once per day
        if existing:
            updated = existing[0][:10]
            today = datetime.now(timezone.utc).date().isoformat()
            if updated == today:
                log.debug("Decade narrative for %s is current, skipping", decade)
                continue

        prompt = DECADE_NARRATIVE_PROMPT.format(decade=decade, sources=sources)
        try:
            resp = ollama.generate(
                model=OLLAMA_MODEL,
                prompt=prompt,
                options={"num_predict": 250, "temperature": 0.5},
            )
            narrative = resp["response"].strip()
            conn.execute(
                "INSERT OR REPLACE INTO decade_narratives (decade, narrative, updated_at) VALUES (?,?,?)",
                (decade, narrative, now),
            )
            conn.commit()
            log.info("Generated narrative for %s", decade)
        except Exception as e:
            log.error("Failed to generate narrative for %s: %s", decade, e)

    conn.close()


def get_all_narratives() -> dict[str, str]:
    """Returns {decade: narrative} dict for use by data_manager."""
    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)
    rows = conn.execute("SELECT decade, narrative FROM decade_narratives").fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}
