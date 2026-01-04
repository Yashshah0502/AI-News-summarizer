# app/services/select_repo.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import select

from app.db.models import Article
from app.services.database import SessionLocal
from app.services.ranker import select_top_diverse

def pick_and_mark(hours: int = 10, per_source: int = 5, final_n: int = 10,
                  topic_targets: Optional[Dict[str, int]] = None) -> List[int]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with SessionLocal() as session:
        rows = session.execute(
            select(Article)
            .where(Article.scraped_at >= cutoff)
            .where(Article.extraction_status == "ok")
            .where(Article.content_text.is_not(None))
        ).scalars().all()

        picked = select_top_diverse(rows, per_source=per_source, final_n=final_n, topic_targets=topic_targets)

        ids: List[int] = []
        for rank, (a, topic, score) in enumerate(picked, start=1):
            a.importance_score = float(score)
            a.reason_selected = f"rank={rank};topic={topic}"
            ids.append(a.id)

        session.commit()
        return ids
