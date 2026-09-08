#!/usr/bin/env python3
"""
Entry point for the Nigeria content desk — called by launchd 3x/day (see
com.ngrblog.agent.plist). Each run picks one category, gathers fresh news
and a cover image, writes one draft, and pushes it to ngr.ltd's admin
review queue. Nothing this script does ever publishes anything — every
pushed draft lands as BlogPostStatus::DRAFT and waits for a human at
/admin/blog-posts.
"""
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config_ngr import NGR_CATEGORIES, NGR_LOGS_DIR
import news_fetcher_ngr
import image_sourcer_ngr
import blog_writer_ngr
import publisher_ngr

NGR_LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(NGR_LOGS_DIR / f"ngr-{datetime.now().strftime('%Y-%m-%d')}.log"),
    ],
)
log = logging.getLogger("main_ngr")


def _category_for_this_run() -> str:
    """
    Deterministic, stateless rotation through NGR_CATEGORIES using
    8-hour buckets since the epoch — matches the 3-runs/day schedule, so
    every category gets refreshed roughly once a day without needing to
    persist a counter anywhere.
    """
    bucket = int(time.time() // (8 * 3600))
    return NGR_CATEGORIES[bucket % len(NGR_CATEGORIES)]


def run() -> None:
    category = _category_for_this_run()
    log.info("=== Nigeria content desk starting — category: %s ===", category)

    try:
        articles = news_fetcher_ngr.fetch_articles_for_category(category)
        if not articles:
            log.warning("No fresh articles for %r — nothing to write this run", category)
            return

        draft = blog_writer_ngr.write_post(category, articles)
        if not draft:
            log.error("Writer produced nothing for %r — aborting run", category)
            return

        image = image_sourcer_ngr.pick_cover_image(category)
        if not image:
            log.warning("No cover image found for %r — publishing without one", category)

        published = publisher_ngr.publish_draft(draft, image)
        if not published:
            log.error("Push to ngr.ltd failed — draft was generated but not delivered")

    except Exception as e:
        log.error("Nigeria content desk run failed: %s\n%s", e, traceback.format_exc())

    finally:
        log.info("=== Nigeria content desk run complete ===")


if __name__ == "__main__":
    run()
