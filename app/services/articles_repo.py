# app/services/articles_repo.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.dialects.postgresql import insert

from app.db.models import Article
from app.services.database import SessionLocal


def _to_dt(v) -> Optional[datetime]:
    # If your scrapers already return datetime, keep it.
    if isinstance(v, datetime):
        return v
    # If it's a string, skip parsing for now (store None) to keep Step 3 simple.
    return None


def upsert_articles(items: List[Dict]) -> List[int]:
    now = datetime.now(timezone.utc)

    # De-dupe within this batch by URL (Postgres requires this for ON CONFLICT DO UPDATE)
    by_url: dict[str, dict] = {}

    for it in items:
        url = (it.get("url") or it.get("link") or "").strip()
        if not url:
            continue

        row = {
            "source": it.get("source", "unknown"),
            "title": (it.get("title") or "").strip(),
            "url": url,
            "category": it.get("category"),
            "published_at": _to_dt(it.get("published_at") or it.get("published_time")),
            "scraped_at": now,
        }

        # keep the latest scraped_at version if the same url appears again
        prev = by_url.get(url)
        if prev is None or (row["scraped_at"] and prev["scraped_at"] and row["scraped_at"] > prev["scraped_at"]):
            by_url[url] = row

    rows = list(by_url.values())
    if not rows:
        return []

    stmt = insert(Article).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Article.url],
        set_={
            "title": stmt.excluded.title,
            "category": stmt.excluded.category,
            "published_at": stmt.excluded.published_at,
            "scraped_at": stmt.excluded.scraped_at,
        },
    ).returning(Article.id)

    with SessionLocal() as session:
        ids = session.execute(stmt).scalars().all()
        session.commit()
        return ids
