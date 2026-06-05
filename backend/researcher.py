"""
Generates search queries and editorial summaries using Ollama.
All calls use a single model (llama3.1:8b) to avoid swap overhead.
"""
import logging
import random
import ollama
from config import (
    OLLAMA_MODEL, STYLE_CATEGORIES, ERA_QUERIES,
    KEYWORD_PROMPT, SUMMARY_PROMPT, UNSPLASH_MAX_QUERIES_PER_RUN,
)

log = logging.getLogger(__name__)


def _call(prompt: str, max_tokens: int = 256) -> str:
    response = ollama.generate(
        model=OLLAMA_MODEL,
        prompt=prompt,
        options={"num_predict": max_tokens, "temperature": 0.7},
    )
    return response["response"].strip()


def generate_search_queries() -> list[dict]:
    """
    Returns a list of dicts: {query: str, category: str, era: str|None}
    Stays within UNSPLASH_MAX_QUERIES_PER_RUN to respect free-tier limits.
    """
    queries = []

    # Pick a rotating subset of style categories each run
    styles = random.sample(STYLE_CATEGORIES, min(8, len(STYLE_CATEGORIES)))
    prompt = KEYWORD_PROMPT.format(n=8, styles=", ".join(styles))
    try:
        raw = _call(prompt, max_tokens=300)
        for line in raw.splitlines():
            line = line.strip().lstrip("-•*123456789. ").strip()
            if line and len(line) > 5:
                queries.append({"query": line, "category": "current", "era": None})
    except Exception as e:
        log.error("Failed to generate style queries: %s", e)
        # Fallback: use static queries so the pipeline never comes up empty
        for style in styles[:4]:
            queries.append({
                "query": f"Black African women {style} hairstyle",
                "category": "current",
                "era": None,
            })

    # Add a rotating pair of era queries each run
    era_keys = random.sample(list(ERA_QUERIES.keys()), min(4, len(ERA_QUERIES)))
    for era in era_keys:
        queries.append({
            "query": ERA_QUERIES[era],
            "category": "historical",
            "era": era,
        })

    return queries[:UNSPLASH_MAX_QUERIES_PER_RUN]


def generate_style_summary(style: str) -> str:
    """2-sentence editorial summary for a given style category."""
    prompt = SUMMARY_PROMPT.format(style=style)
    try:
        return _call(prompt, max_tokens=150)
    except Exception as e:
        log.error("Failed to generate summary for '%s': %s", style, e)
        return f"{style.title()} is a celebrated hairstyle tradition in Black and African culture."


def generate_latest_summary(style_names: list[str]) -> str:
    """Short 'what's trending now' blurb for the landing page hero."""
    joined = ", ".join(style_names[:5])
    prompt = (
        f"Write one energetic sentence (max 25 words) introducing today's featured "
        f"Black and African women's hair trends: {joined}. Output only the sentence."
    )
    try:
        return _call(prompt, max_tokens=60)
    except Exception as e:
        log.error("Failed to generate latest summary: %s", e)
        return "Celebrating the beauty and diversity of Black and African women's hair today."
