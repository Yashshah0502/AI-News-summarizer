# app/services/extract_repo.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

from sqlalchemy import select

from app.db.models import Article
from app.services.database import SessionLocal
from app.services.extractor import extract_article_text

logger = logging.getLogger(__name__)


def extract_missing_content(hours: int = 10, batch_size: int = 30) -> Dict[str, int]:
    """
    Extract content from articles missing content_text.

    Returns:
        Dict with counts: {"attempted": N, "succeeded": M, "failed": K}
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with SessionLocal() as session:
        # Select articles with no content that aren't already permanently failed
        q = (
            select(Article)
            .where(Article.scraped_at >= cutoff)
            .where(Article.content_text.is_(None))
            .limit(batch_size)
        )
        rows = session.execute(q).scalars().all()

        if not rows:
            logger.info("No articles found needing extraction")
            return {"attempted": 0, "succeeded": 0, "failed": 0}

        logger.info(f"Attempting extraction for {len(rows)} articles")

        succeeded = 0
        failed = 0

        for i, article in enumerate(rows, 1):
            logger.info(f"[{i}/{len(rows)}] Extracting: {article.url[:80]}...")

            text, status_msg = extract_article_text(article.url)

            if text:
                article.content_text = text
                article.extraction_status = "ok"
                succeeded += 1
                logger.info(f"  ✓ Success: {len(text)} chars")
            else:
                article.extraction_status = "failed"
                failed += 1
                logger.warning(f"  ✗ Failed: {status_msg}")

        session.commit()

        result = {
            "attempted": len(rows),
            "succeeded": succeeded,
            "failed": failed,
        }

        logger.info(f"Extraction complete: {result}")
        return result
