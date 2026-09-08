"""
Config for the Nigeria content desk — a separate, category-based blog
pipeline that pushes drafts to ngr.ltd instead of publishing to gh-pages.
Shares Ollama and Unsplash setup with config.py; keeps its own SQLite
database and schedule so it never competes with the hourly hair-trends run.
"""
import os
from pathlib import Path

from config import (
    BACKEND_DIR,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    UNSPLASH_ACCESS_KEY,
    UNSPLASH_API_BASE,
)

NGR_DB_PATH = BACKEND_DIR / "ngr_blog.db"
NGR_LOGS_DIR = BACKEND_DIR / "logs"

# The ngr.ltd deployment this pipeline pushes drafts to, and the shared
# secret it authenticates with — see VerifyContentPipelineToken on the
# ngr.ltd side. Generate a token with `php artisan tinker` -> `Str::random(64)`
# and set the identical value in both .env files.
NGR_API_BASE = os.environ.get("NGR_API_BASE", "https://ngr.ltd")
CONTENT_PIPELINE_TOKEN = os.environ.get("CONTENT_PIPELINE_TOKEN", "")

# One category is processed per run — see main_ngr.py — rotating through
# this list so every category gets refreshed roughly once a day at 3
# runs/day (see com.ngrblog.agent.plist).
NGR_CATEGORIES = ["news", "culture", "notable-people", "entertainment", "tech", "lifestyle"]

# Google News RSS queries per category — headline + source + link only,
# never full article text. The LLM is instructed to write original
# commentary and cite sources, not reproduce them (news_fetcher.py already
# uses this same posture for the hair-trends blog).
NGR_NEWS_QUERIES = {
    "news": [
        "Nigeria news today",
        "Nigeria politics",
        "Nigeria economy business",
    ],
    "culture": [
        "Nigerian culture heritage",
        "Nigeria traditional festival",
    ],
    "notable-people": [
        "notable Nigerian",
        "Nigerian achievement award",
    ],
    "entertainment": [
        "Afrobeats news",
        "Nollywood news",
        "Nigerian music artist",
    ],
    "tech": [
        "Nigerian startup funding",
        "Lagos tech ecosystem",
        "Nigeria fintech",
    ],
    "lifestyle": [
        "Nigerian food",
        "Nigeria lifestyle travel",
    ],
}
NGR_NEWS_MAX_PER_QUERY = 6
NGR_NEWS_MAX_ARTICLES = 10  # articles passed to the LLM per post

# One Unsplash search per category, reusing the same account/key as the
# hair-trends pipeline (image_fetcher.py) — just a different query set.
NGR_IMAGE_QUERIES = {
    "news": "Nigeria Lagos city",
    "culture": "Nigerian culture traditional",
    "notable-people": "Nigerian portrait professional",
    "entertainment": "Africa concert music",
    "tech": "Africa technology office",
    "lifestyle": "Nigerian food market",
}

NGR_BLOG_PROMPT = """You are the editorial desk for ngr.ltd, a site covering Nigeria for a global \
audience — news, culture, notable people, tech, entertainment, and lifestyle. Category for this \
piece: {category_label}.

Write an original, SEO-structured blog post grounded in today's headlines below. Do not copy \
sentences from the headlines — write your own analysis and context, and cite sources naturally \
in the text (e.g. "According to Premium Times, ..."). If a fact isn't in the sources, don't state \
it as fact.

Output exactly these fields, one per line at the start, in this order, then the body:
TITLE: [a specific, compelling title, no clickbait]
META: [a 150-160 character meta description]
EXCERPT: [a 2-sentence excerpt, standalone, no "in this post"]
TAGS: [3-5 short tags, comma-separated]
BODY:
[800-1200 words, HTML paragraphs only: <p>...</p> and <h2>...</h2> subheads. No markdown, no \
lists unless genuinely appropriate as <ul><li>. Journalistic tone, not a listicle.]

Today's headlines:
{articles}
"""
