# app/services/cleanup_repo.py
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete

from app.db.models import Article, Digest, DigestItem
from app.services.database import SessionLocal

def cleanup_older_than(hours: int = 18) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with SessionLocal() as s:
        # delete digest_items via joining digests cutoff (safe)
        dig_ids = s.execute(
            delete(DigestItem).where(
                DigestItem.digest_id.in_(
                    s.query(Digest.id).filter(Digest.created_at < cutoff).subquery()
                )
            )
        )
        d_items = dig_ids.rowcount or 0

        d_dig = s.execute(delete(Digest).where(Digest.created_at < cutoff)).rowcount or 0
        d_art = s.execute(delete(Article).where(Article.scraped_at < cutoff)).rowcount or 0

        s.commit()
        return {"cutoff": cutoff.isoformat(), "deleted_digest_items": d_items, "deleted_digests": d_dig, "deleted_articles": d_art}
