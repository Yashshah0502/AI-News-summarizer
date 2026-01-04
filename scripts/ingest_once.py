# scripts/ingest_once.py
import sys
from dotenv import load_dotenv
from sqlalchemy import select, func

from app.services.database import init_db, SessionLocal
from app.services.articles_repo import upsert_articles
from app.db.models import Article

from app.scrapers import run_scrapers


def count_articles() -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(Article)) or 0


def main():
    load_dotenv()
    init_db()

    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    before = count_articles()
    items = run_scrapers.run(hours=hours)
    ids = upsert_articles(items)
    after = count_articles()

    new_rows = after - before
    updated_rows = len(ids) - new_rows  # approximate, but useful

    print(
        f"scraped={len(items)} returned={len(ids)} new={new_rows} updated~={updated_rows} "
        f"total={after} hours={hours}"
    )


if __name__ == "__main__":
    main()
