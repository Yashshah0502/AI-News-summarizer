# app/services/extract_repo.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict
from urllib.parse import urlparse

from sqlalchemy import select, or_

from app.db.models import Article
from app.services.database import SessionLocal
from app.services.extractor import extract_article_text

logger = logging.getLogger(__name__)

# Domains that are known to be hopeless (JS-heavy, paywalled, non-article pages)
SKIP_DOMAINS = {
    "wol.fm",  # Radio/audio content
    "twitter.com",
    "x.com",
    "youtube.com",
    "reddit.com",
    "retool.com",  # 403 forbidden
    "bostondynamics.com",  # JS-heavy, trafilatura fails
    "donotnotify.com",  # Minimal HTML, trafilatura fails
    "minha.sh",  # Blog with custom layout that trafilatura can't parse
    "ronjeffries.com",  # Minimal HTML blog
    "www.thebignewsletter.com",  # Newsletter site with complex layout
}

# Maximum extraction attempts before giving up
MAX_EXTRACTION_ATTEMPTS = 3


def extract_missing_content(hours: int = 10, batch_size: int = 30) -> Dict[str, int]:
    """
    Extract content from articles missing content_text with retry logic.

    Uses exponential backoff for retries:
    - Attempt 1: immediate
    - Attempt 2: wait 5 minutes
    - Attempt 3: wait 30 minutes
    - After 3 attempts: mark as permanently failed

    Returns:
        Dict with counts: {"attempted": N, "succeeded": M, "failed": K, "skipped": S}
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        # Select articles that need extraction:
        # 1. No content text
        # 2. Not permanently failed (extraction_status != 'failed' or extraction_attempts < MAX)
        # 3. Not in cooldown (next_extract_at is NULL or <= now)
        # 4. Not skipped
        q = (
            select(Article)
            .where(Article.scraped_at >= cutoff)
            .where(Article.content_text.is_(None))
            .where(
                or_(
                    Article.extraction_status.is_(None),
                    Article.extraction_status == "ok",
                    Article.extraction_attempts < MAX_EXTRACTION_ATTEMPTS,
                )
            )
            .where(
                or_(
                    Article.next_extract_at.is_(None),
                    Article.next_extract_at <= now,
                )
            )
            .where(Article.extraction_status != "skipped")
            .limit(batch_size)
        )
        rows = session.execute(q).scalars().all()

        if not rows:
            logger.info("No articles found needing extraction")
            return {"attempted": 0, "succeeded": 0, "failed": 0, "skipped": 0}

        logger.info(f"Attempting extraction for {len(rows)} articles")

        succeeded = 0
        failed = 0
        skipped = 0

        for i, article in enumerate(rows, 1):
            # Check if domain is in skiplist
            domain = urlparse(article.url).netloc
            if domain in SKIP_DOMAINS:
                logger.info(f"[{i}/{len(rows)}] Skipping {domain} (in skiplist)")
                article.extraction_status = "skipped"
                skipped += 1
                continue

            logger.info(f"[{i}/{len(rows)}] Extracting: {article.url[:80]}... (attempt {article.extraction_attempts + 1})")

            text, status_msg = extract_article_text(article.url)

            # Increment attempt counter
            article.extraction_attempts += 1

            if text:
                article.content_text = text
                article.extraction_status = "ok"
                article.next_extract_at = None  # Clear cooldown
                succeeded += 1
                logger.info(f"  ✓ Success: {len(text)} chars")
            else:
                # Calculate exponential backoff: 5 min, 30 min
                if article.extraction_attempts < MAX_EXTRACTION_ATTEMPTS:
                    # Exponential backoff: 5 * (6 ^ attempt) minutes
                    backoff_minutes = 5 * (6 ** (article.extraction_attempts - 1))
                    article.next_extract_at = now + timedelta(minutes=backoff_minutes)
                    logger.warning(f"  ✗ Failed (attempt {article.extraction_attempts}/{MAX_EXTRACTION_ATTEMPTS}): {status_msg}")
                    logger.info(f"  ⏰ Will retry after {backoff_minutes} minutes")
                else:
                    # Permanently mark as failed after MAX attempts
                    article.extraction_status = "failed"
                    article.next_extract_at = None
                    logger.error(f"  ✗ Permanently failed after {MAX_EXTRACTION_ATTEMPTS} attempts: {status_msg}")

                failed += 1

        session.commit()

        result = {
            "attempted": len(rows),
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
        }

        logger.info(f"Extraction complete: {result}")
        return result
