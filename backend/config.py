import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
DB_PATH = BACKEND_DIR / "hair_trends.db"
LOGS_DIR = BACKEND_DIR / "logs"

load_dotenv(BASE_DIR / ".env")

UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO_URL = os.environ.get("GITHUB_REPO_URL", "https://github.com/richardawe/localtest.git")

OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_BASE_URL = "http://localhost:11434"

UNSPLASH_API_BASE = "https://api.unsplash.com"
UNSPLASH_RESULTS_PER_PAGE = 30
# Stay within 50 req/hr free tier; production tier allows 5000/hr
UNSPLASH_MAX_QUERIES_PER_RUN = 12

WIKIPEDIA_API_BASE = "https://en.wikipedia.org/api/rest_v1"
WIKIPEDIA_ARTICLES = [
    "Natural_hair_movement",
    "Afro",
    "Cornrows",
    "Dreadlocks",
    "Protective_hairstyle",
    "Bantu_knot",
    "Box_braids",
    "Locs",
    "African-American_culture",
    "Jheri_curl",
]

STYLE_CATEGORIES = [
    "box braids",
    "cornrows",
    "senegalese twists",
    "goddess braids",
    "bantu knots",
    "locs dreadlocks",
    "sisterlocks",
    "natural afro",
    "TWA teenie weenie afro",
    "protective styles",
    "weaves extensions",
    "press and curl",
    "relaxed permed hair",
    "crochet braids",
    "fulani braids",
]

ERA_QUERIES = {
    "1920s": "1920s Harlem Renaissance Black women hairstyle vintage",
    "1930s": "1930s Black women hair style vintage portrait",
    "1940s": "1940s Black women hairstyle wartime era",
    "1950s": "1950s Black women hair style press and curl",
    "1960s": "1960s Civil Rights movement Black women afro hairstyle",
    "1970s": "1970s Black Power natural afro women hair",
    "1980s": "1980s jheri curl Black women braids hairstyle",
    "1990s": "1990s Black women braid styles weave",
    "2000s": "2000s Black women hair trends extensions",
    "2010s": "2010s natural hair movement Black women",
    "2020s": "2020s Black women protective styles modern braids",
}

PAGES_SIZE = 50
LATEST_COUNT = 20
BLOG_POSTS_KEEP = 30   # rolling window of daily posts to keep in blog.json

# Google News RSS queries — rotated across daily blog runs
NEWS_QUERIES = [
    "black women natural hair",
    "African hair braiding culture",
    "natural hair movement",
    "black hair care beauty",
    "locs braids black women",
    "black hair discrimination CROWN Act",
    "African American hair trends",
    "protective styles black women",
]
NEWS_MAX_ARTICLES = 12  # articles passed to the LLM per blog post
NEWS_MAX_PER_QUERY = 5  # cap per RSS query before dedup

RELEVANCE_PROMPT = (
    "You are a content classifier. Given image metadata, decide if the image "
    "likely shows a Black or African woman's hairstyle.\n\n"
    "Metadata:\nalt: {alt}\ndescription: {desc}\ntags: {tags}\n\n"
    "Answer with exactly one word: YES or NO."
)

SUMMARY_PROMPT = (
    "Write a 2-sentence editorial summary of the following hair style trend "
    "for Black and African women. Style: {style}. Be specific, celebratory, "
    "and culturally informed. Output only the summary, no preamble."
)

KEYWORD_PROMPT = (
    "Generate {n} specific Unsplash image search queries to find high-quality "
    "photos of Black and African women's hairstyles. Focus on: {styles}. "
    "Each query should be 4-7 words. Output one query per line, no numbering, "
    "no extra text."
)
