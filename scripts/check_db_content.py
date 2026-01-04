# scripts/check_db_content.py
"""
Check database for successfully extracted articles.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.models import Article
from app.services.database import SessionLocal


def check_content(hours: int = 24):
    """Check extracted content in the database."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with SessionLocal() as session:
        # Get successful extractions
        successful = session.query(Article).filter(
            Article.scraped_at >= cutoff,
            Article.extraction_status == "ok",
            Article.content_text.isnot(None)
        ).all()

        print(f"\n{'='*70}")
        print(f"Database Content Check - Last {hours} hours")
        print(f"{'='*70}\n")

        if not successful:
            print("No successfully extracted articles found.")
            return

        print(f"Found {len(successful)} successfully extracted articles:\n")

        for i, article in enumerate(successful[:5], 1):  # Show first 5
            print(f"{i}. {article.title[:60]}...")
            print(f"   URL: {article.url[:70]}...")
            print(f"   Source: {article.source}")
            print(f"   Content length: {len(article.content_text)} chars")
            print(f"   Preview: {article.content_text[:150]}...")
            print()

        if len(successful) > 5:
            print(f"   ... and {len(successful) - 5} more articles")

        print(f"{'='*70}\n")


if __name__ == "__main__":
    load_dotenv()
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    check_content(hours)
