from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.models import Article, Digest, DigestItem
from app.services.database import SessionLocal

def create_digest(hours: int) -> int:
    now = datetime.now(timezone.utc)
    d = Digest(window_start=now - timedelta(hours=hours), window_end=now)
    with SessionLocal() as s:
        s.add(d); s.commit(); s.refresh(d)
        return d.id

def add_items(digest_id: int, items: list[tuple[int,int,str]]):  # (rank, article_id, summary)
    with SessionLocal() as s:
        for rank, aid, summ in items:
            s.add(DigestItem(digest_id=digest_id, article_id=aid, rank=rank, item_summary=summ))
        s.commit()

def fetch_articles(ids: list[int]) -> list[Article]:
    with SessionLocal() as s:
        return s.execute(select(Article).where(Article.id.in_(ids))).scalars().all()
