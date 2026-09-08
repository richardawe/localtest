"""
Uses Ollama to synthesise fetched Nigeria news into an SEO-structured blog
post for one category. Sources are passed as title/source/date only — the
LLM is instructed to write original commentary and cite them, never
reproduce their text (same posture as blog_writer.py).
"""
import logging
import re
from typing import Dict, List, Optional

import ollama

from config import OLLAMA_MODEL
from config_ngr import NGR_BLOG_PROMPT, NGR_NEWS_MAX_ARTICLES

log = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "news": "Nigeria News",
    "culture": "Culture & Heritage",
    "notable-people": "Notable Nigerians",
    "entertainment": "Afrobeats & Entertainment",
    "tech": "Tech & Startups",
    "lifestyle": "Food & Lifestyle",
}


def _format_articles_for_prompt(articles: List[Dict]) -> str:
    lines = []
    for i, a in enumerate(articles[:NGR_NEWS_MAX_ARTICLES], 1):
        pub = a.get("published", "")[:10]
        lines.append(f"{i}. \"{a['title']}\" — {a['source']} ({pub})")
    return "\n".join(lines)


def _extract_field(raw: str, field: str) -> str:
    match = re.search(rf"^{field}:\s*(.+)$", raw, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_body(raw: str) -> str:
    idx = raw.find("BODY:")
    if idx == -1:
        return raw.strip()
    return raw[idx + len("BODY:"):].strip()


def write_post(category: str, articles: List[Dict]) -> Optional[Dict]:
    """
    Generates one structured draft from a category's fresh articles.
    Returns None if there's nothing to write from, or on an Ollama error.
    """
    if not articles:
        log.warning("No articles for category %r — skipping", category)
        return None

    prompt = NGR_BLOG_PROMPT.format(
        category_label=CATEGORY_LABELS.get(category, category),
        articles=_format_articles_for_prompt(articles),
    )

    log.info("Generating Nigeria blog post [%s] from %d articles", category, min(len(articles), NGR_NEWS_MAX_ARTICLES))
    try:
        resp = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            options={"num_predict": 1600, "temperature": 0.7},
        )
        raw = resp["response"].strip()
    except Exception as e:
        log.error("Ollama generation failed [%s]: %s", category, e)
        return None

    title = _extract_field(raw, "TITLE")
    meta = _extract_field(raw, "META")
    excerpt = _extract_field(raw, "EXCERPT")
    tags_raw = _extract_field(raw, "TAGS")
    body = _extract_body(raw)

    if not title or not body:
        log.error("Malformed LLM output [%s] — missing title or body", category)
        return None

    tags = [t.strip() for t in tags_raw.split(",") if t.strip()][:5]

    sources = [
        {
            "title": a["title"],
            "url": a["url"],
            "source": a["source"],
            "published_at": a.get("published", "")[:10],
        }
        for a in articles[:NGR_NEWS_MAX_ARTICLES]
    ]

    return {
        "title": title,
        "meta_description": meta[:300] if meta else None,
        "excerpt": excerpt[:500] if excerpt else None,
        "body": body,
        "category": category,
        "tags": tags,
        "sources": sources,
    }
