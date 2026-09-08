"""
Pushes one generated draft to ngr.ltd's ingestion endpoint. Always
computes and sends its own slug, so a retried or re-run push upserts the
same row on the ngr.ltd side (see BlogPostRepository::upsertDraft) instead
of creating a duplicate — the ngr.ltd side only auto-generates a slug when
none is supplied.
"""
import logging
import re
import unicodedata

import requests

from config_ngr import CONTENT_PIPELINE_TOKEN, NGR_API_BASE

log = logging.getLogger(__name__)

INGEST_URL = f"{NGR_API_BASE.rstrip('/')}/api/internal/blog-posts"


def slugify(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug[:200]


def publish_draft(draft: dict, image: dict | None) -> bool:
    """
    POSTs a draft (from blog_writer_ngr.write_post) plus its cover image
    (from image_sourcer_ngr.pick_cover_image, or None) to ngr.ltd. Returns
    True on success. Never raises — a failed push is logged and retried on
    the next scheduled run.
    """
    if not CONTENT_PIPELINE_TOKEN:
        log.error("CONTENT_PIPELINE_TOKEN not set — skipping publish")
        return False

    payload = {
        "title": draft["title"],
        "slug": slugify(draft["title"]),
        "meta_description": draft.get("meta_description"),
        "excerpt": draft.get("excerpt"),
        "body": draft["body"],
        "category": draft["category"],
        "tags": draft.get("tags", []),
        "sources": draft.get("sources", []),
    }

    if image:
        payload["cover_image_url"] = image.get("url")
        payload["cover_image_credit"] = image.get("credit")
        payload["cover_image_credit_url"] = image.get("credit_url")

    try:
        resp = requests.post(
            INGEST_URL,
            json=payload,
            headers={"Authorization": f"Bearer {CONTENT_PIPELINE_TOKEN}", "Accept": "application/json"},
            timeout=30,
            # A validation failure without an explicit JSON Accept header
            # gets treated by Laravel as a browser request and redirected
            # back rather than answered with 422 — which `requests` would
            # otherwise follow silently, turning a rejected draft into a
            # 200 on some unrelated page. Surfacing the redirect as a
            # failure here caught exactly that bug in testing.
            allow_redirects=False,
        )
    except Exception as e:
        log.error("Publish request failed [%s]: %s", payload["slug"], e)
        return False

    if resp.status_code not in (200, 201):
        log.error("Publish rejected [%s]: %d %s", payload["slug"], resp.status_code, resp.text[:500])
        return False

    log.info("Pushed draft to ngr.ltd admin queue: %r (slug=%s)", draft["title"], payload["slug"])
    return True
