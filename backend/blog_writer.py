"""
Uses Ollama to synthesise fetched news articles into a daily blog post.
The LLM is given article titles, sources, and dates — it writes the
narrative. Source links are passed through verbatim (no hallucination risk).
"""
import json
import logging
import sqlite3
from datetime import datetime, timezone

import ollama
from config import DB_PATH, OLLAMA_MODEL, NEWS_MAX_ARTICLES

log = logging.getLogger(__name__)

BLOG_PROMPT = """You are a warm, culturally aware writer for a publication celebrating Black and African hair culture.

Below are today's news headlines about Black hair. Write a blog post that:
- Has a compelling title (prefix it with exactly "TITLE: " on its own line)
- Opens with a 2-sentence intro that sets the cultural context
- Has 3–4 short paragraphs, each covering a distinct theme from the headlines
- Mentions article sources naturally in the text (e.g. "According to Essence, …")
- Closes with one sentence celebrating Black hair identity
- Is 350–450 words total
- Feels like editorial journalism, not a list

Start the body with exactly "BODY: " on its own line, then write the full post as flowing paragraphs.

Today's articles:
{articles}

Output format (two lines then body — nothing else before TITLE:):
TITLE: [your title here]
BODY: [your blog post here, multiple paragraphs]"""


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS blog_posts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            body        TEXT NOT NULL,
            sources     TEXT NOT NULL,
            published_at TEXT NOT NULL,
            run_date    TEXT NOT NULL UNIQUE
        )
    """)
    conn.commit()


def _already_ran_today(conn: sqlite3.Connection) -> bool:
    today = datetime.now(timezone.utc).date().isoformat()
    row = conn.execute(
        "SELECT 1 FROM blog_posts WHERE run_date = ?", (today,)
    ).fetchone()
    return row is not None


def _format_articles_for_prompt(articles: list[dict]) -> str:
    lines = []
    for i, a in enumerate(articles[:NEWS_MAX_ARTICLES], 1):
        pub = a.get("published", "")[:10]  # YYYY-MM-DD only
        lines.append(f"{i}. \"{a['title']}\" — {a['source']} ({pub})")
    return "\n".join(lines)


def _parse_llm_output(raw: str) -> tuple[str, str]:
    """Extract TITLE and BODY from structured LLM output."""
    title = ""
    body = ""
    for line in raw.splitlines():
        if line.startswith("TITLE:"):
            title = line[len("TITLE:"):].strip()
        elif line.startswith("BODY:"):
            # Everything after "BODY:" on this line plus subsequent lines
            body = line[len("BODY:"):].strip()
            idx = raw.find("BODY:")
            after = raw[idx + len("BODY:"):].strip()
            body = after
            break

    if not title:
        title = "Today in Black Hair Culture"
    if not body:
        body = raw.strip()
    return title, body


def write_post(articles: list[dict]) -> dict | None:
    """
    Generates and stores today's blog post.
    Returns the post dict, or None if already done today or on error.
    """
    if not articles:
        log.warning("No articles provided — skipping blog generation")
        return None

    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)

    if _already_ran_today(conn):
        log.info("Blog post already written today — skipping")
        conn.close()
        return None

    prompt = BLOG_PROMPT.format(
        articles=_format_articles_for_prompt(articles)
    )

    log.info("Generating blog post from %d articles", min(len(articles), NEWS_MAX_ARTICLES))
    try:
        resp = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            options={"num_predict": 700, "temperature": 0.75},
        )
        raw = resp["response"].strip()
    except Exception as e:
        log.error("Ollama blog generation failed: %s", e)
        conn.close()
        return None

    title, body = _parse_llm_output(raw)
    now = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc).date().isoformat()

    sources = [
        {"title": a["title"], "url": a["url"],
         "source": a["source"], "published": a.get("published", "")[:10]}
        for a in articles[:NEWS_MAX_ARTICLES]
    ]

    try:
        conn.execute(
            """INSERT OR REPLACE INTO blog_posts
               (title, body, sources, published_at, run_date)
               VALUES (?,?,?,?,?)""",
            (title, body, json.dumps(sources), now, today),
        )
        conn.commit()
        log.info("Blog post stored: %r", title)
    except Exception as e:
        log.error("Failed to store blog post: %s", e)
        conn.close()
        return None

    conn.close()
    return {"title": title, "body": body, "sources": sources, "published_at": now}


def get_all_posts(limit: int = 30) -> list[dict]:
    """Returns recent blog posts newest-first, for data_manager export."""
    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)
    rows = conn.execute(
        "SELECT id, title, body, sources, published_at FROM blog_posts "
        "ORDER BY published_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "title": r[1],
            "body": r[2],
            "sources": json.loads(r[3]),
            "published_at": r[4],
        }
        for r in rows
    ]
