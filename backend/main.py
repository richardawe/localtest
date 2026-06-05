#!/usr/bin/env python3
"""
Entry point called by launchd every hour.
Orchestrates the full pipeline: research → fetch → export → deploy.
Writes status.json regardless of success or failure.
"""
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend/ is on the path when invoked directly
sys.path.insert(0, str(Path(__file__).parent))

from config import LOGS_DIR
import researcher
import image_fetcher
import historian
import data_manager
import git_publisher

LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"),
    ],
)
log = logging.getLogger("main")


def _is_daily_run() -> bool:
    """True at the top of the midnight hour (00:xx UTC)."""
    return datetime.now(timezone.utc).hour == 0


def run() -> None:
    log.info("=== Hair Trends pipeline starting ===")
    status_kwargs: dict = {"success": False, "error": None, "stats": {}}

    try:
        # Step 1: generate search queries
        log.info("Step 1/5 — Generating search queries")
        queries = researcher.generate_search_queries()
        log.info("Generated %d queries", len(queries))

        # Step 2: fetch images from Unsplash
        log.info("Step 2/5 — Fetching images from Unsplash")
        new_images = image_fetcher.fetch_and_store(queries)
        log.info("New images this run: %d", new_images)

        # Step 3: generate historical decade narratives (once per day)
        if _is_daily_run():
            log.info("Step 3/5 — Updating historical narratives (daily task)")
            historian.update_decade_narratives()
        else:
            log.info("Step 3/5 — Skipping historical update (not midnight run)")

        # Step 4: generate hero summary and export JSON
        log.info("Step 4/5 — Exporting JSON data files")
        hero_summary = ""
        if new_images > 0:
            style_names = list({q["category"] for q in queries if q["category"] != "historical"})
            hero_summary = researcher.generate_latest_summary(style_names)

        stats = data_manager.export_all(hero_summary=hero_summary, total_new=new_images)

        status_kwargs["success"] = True
        status_kwargs["stats"] = stats
        log.info("Export complete: %s", stats)

    except Exception as e:
        status_kwargs["error"] = str(e)
        log.error("Pipeline failed: %s\n%s", e, traceback.format_exc())

    finally:
        # Step 5: always write status and deploy (even on partial failure,
        # so the frontend shows the latest available data)
        log.info("Step 5/5 — Writing status and deploying to gh-pages")
        data_manager.write_status(**status_kwargs)
        deployed = git_publisher.publish()
        if not deployed:
            log.error("Deployment to gh-pages failed")
        log.info("=== Pipeline complete ===")


if __name__ == "__main__":
    run()
