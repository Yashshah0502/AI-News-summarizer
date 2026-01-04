# scripts/reset_failed_extractions.py
"""
Reset failed extractions so they can be retried with improved extraction logic.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.models import Article
from app.services.database import SessionLocal


def reset_failed_extractions(hours: int = 24):
    """Reset extraction_status to NULL for failed articles so they can be retried."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with SessionLocal() as session:
        # Find all failed extractions in the time window
        result = session.query(Article).filter(
            Article.scraped_at >= cutoff,
            Article.extraction_status == "failed",
            Article.content_text.is_(None),
        ).update({"extraction_status": None})

        session.commit()

        print(f"\n{'='*60}")
        print(f"Reset {result} failed extractions from last {hours} hours")
        print("These articles can now be retried with improved extraction.")
        print(f"{'='*60}\n")

        return result


if __name__ == "__main__":
    load_dotenv()
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    reset_failed_extractions(hours)
