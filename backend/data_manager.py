"""
Exports SQLite data to paginated JSON files consumed by the frontend.
Writes into a local staging directory; git_publisher.py deploys them.
"""
import json
import logging
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH, FRONTEND_DIR, PAGES_SIZE, LATEST_COUNT, ERA_QUERIES, BASE_DIR, BLOG_POSTS_KEEP

log = logging.getLogger(__name__)

# Staging area: exported JSON lives here before git_publisher copies to gh-pages
DATA_DIR = BASE_DIR / "data"


def _ensure_dirs() -> None:
    (DATA_DIR / "historical").mkdir(parents=True, exist_ok=True)


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["unsplash_id"],
        "url": row["url_regular"],
        "thumb": row["url_thumb"],
        "full": row["url_full"],
        "alt": row["alt_description"] or "",
        "description": row["description"] or "",
        "photographer": row["photographer_name"] or "",
        "photographer_url": row["photographer_url"] or "",
        "photo_url": row["unsplash_photo_url"] or "",
        "tags": row["tags"] or "",
        "era": row["era"] or "",
        "category": row["style_category"] or "",
        "fetched_at": row["fetched_at"],
    }


def export_all(hero_summary: str = "", total_new: int = 0) -> dict:
    """
    Builds and writes all JSON files. Returns the status dict.
    """
    _ensure_dirs()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Ensure photos table exists even on first run with no images
    conn.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            unsplash_id TEXT PRIMARY KEY, url_regular TEXT NOT NULL,
            url_thumb TEXT NOT NULL, url_full TEXT NOT NULL,
            alt_description TEXT, description TEXT,
            photographer_name TEXT, photographer_url TEXT,
            unsplash_photo_url TEXT, tags TEXT, search_query TEXT,
            era TEXT, style_category TEXT, fetched_at TEXT NOT NULL
        )
    """)

    total = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
    total_pages = max(1, math.ceil(total / PAGES_SIZE))

    # latest.json
    latest_rows = conn.execute(
        "SELECT * FROM photos ORDER BY fetched_at DESC LIMIT ?", (LATEST_COUNT,)
    ).fetchall()
    latest_images = [_row_to_dict(r) for r in latest_rows]

    latest_data = {
        "summary": hero_summary or "Celebrating the beauty and diversity of Black and African women's hair.",
        "images": latest_images,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write(DATA_DIR / "latest.json", latest_data)

    # paginated pages
    for page in range(1, total_pages + 1):
        offset = (page - 1) * PAGES_SIZE
        rows = conn.execute(
            "SELECT * FROM photos ORDER BY fetched_at ASC LIMIT ? OFFSET ?",
            (PAGES_SIZE, offset),
        ).fetchall()
        _write(DATA_DIR / f"page_{page:03d}.json", {"page": page, "images": [_row_to_dict(r) for r in rows]})

    # catalog.json
    era_counts = {}
    for era in ERA_QUERIES:
        count = conn.execute(
            "SELECT COUNT(*) FROM photos WHERE era = ?", (era,)
        ).fetchone()[0]
        era_counts[era] = count

    category_counts = {}
    rows = conn.execute(
        "SELECT style_category, COUNT(*) as c FROM photos GROUP BY style_category"
    ).fetchall()
    for r in rows:
        if r["style_category"]:
            category_counts[r["style_category"]] = r["c"]

    catalog = {
        "total_images": total,
        "total_pages": total_pages,
        "page_size": PAGES_SIZE,
        "era_counts": era_counts,
        "category_counts": category_counts,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write(DATA_DIR / "catalog.json", catalog)

    # historical/NNNN0s.json — merge narratives with images
    from historian import get_all_narratives
    narratives = get_all_narratives()

    for era in ERA_QUERIES:
        rows = conn.execute(
            "SELECT * FROM photos WHERE era = ? ORDER BY fetched_at DESC LIMIT 12",
            (era,),
        ).fetchall()
        era_data = {
            "era": era,
            "narrative": narratives.get(era, ""),
            "images": [_row_to_dict(r) for r in rows],
        }
        _write(DATA_DIR / "historical" / f"{era}.json", era_data)

    conn.close()

    # sitemap.xml
    _write_sitemap(total_pages)

    log.info("Exported %d total images across %d pages", total, total_pages)
    return {"total_images": total, "total_pages": total_pages, "new_this_run": total_new}


def export_blog() -> int:
    """
    Exports the rolling blog post archive to data/blog.json.
    Returns the number of posts exported.
    """
    _ensure_dirs()
    from blog_writer import get_all_posts
    posts = get_all_posts(limit=BLOG_POSTS_KEEP)
    _write(DATA_DIR / "blog.json", {
        "posts": posts,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    log.info("Exported %d blog posts to blog.json", len(posts))
    return len(posts)


def write_status(success: bool, error: str | None = None, stats: dict | None = None) -> None:
    _ensure_dirs()
    status = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "error": error,
        **(stats or {}),
    }
    _write(DATA_DIR / "status.json", status)
    log.info("Wrote status.json: success=%s", success)


def _write(path: Path, data: dict | list) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_sitemap(total_pages: int) -> None:
    base = "https://richardawe.github.io/localtest"
    urls = [
        f"<url><loc>{base}/</loc><changefreq>hourly</changefreq><priority>1.0</priority></url>",
        f"<url><loc>{base}/gallery.html</loc><changefreq>hourly</changefreq><priority>0.9</priority></url>",
        f"<url><loc>{base}/timeline.html</loc><changefreq>daily</changefreq><priority>0.8</priority></url>",
        f"<url><loc>{base}/blog.html</loc><changefreq>daily</changefreq><priority>0.8</priority></url>",
    ]
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    (DATA_DIR.parent / "frontend" / "sitemap.xml").write_text(sitemap, encoding="utf-8")
