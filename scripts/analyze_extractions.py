# scripts/analyze_extractions.py
"""
Analyze extraction success/failure patterns to identify problematic domains.
"""
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.models import Article
from app.services.database import SessionLocal


def analyze_extractions(hours: int = 24):
    """Analyze extraction patterns and show which domains are failing."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with SessionLocal() as session:
        articles = session.query(Article).filter(
            Article.scraped_at >= cutoff
        ).all()

        total = len(articles)
        if total == 0:
            print(f"No articles found in last {hours} hours")
            return

        # Count by status
        status_counts = Counter(a.extraction_status for a in articles)

        # Count by domain and status
        success_by_domain = Counter()
        failed_by_domain = Counter()

        for article in articles:
            domain = urlparse(article.url).netloc
            if article.extraction_status == "ok":
                success_by_domain[domain] += 1
            elif article.extraction_status == "failed":
                failed_by_domain[domain] += 1

        # Print report
        print(f"\n{'='*70}")
        print(f"Extraction Analysis - Last {hours} hours")
        print(f"{'='*70}\n")

        print(f"Total articles: {total}")
        print(f"  ✓ Successful: {status_counts.get('ok', 0)} ({status_counts.get('ok', 0)/total*100:.1f}%)")
        print(f"  ✗ Failed: {status_counts.get('failed', 0)} ({status_counts.get('failed', 0)/total*100:.1f}%)")
        print(f"  ○ Not attempted: {status_counts.get(None, 0)} ({status_counts.get(None, 0)/total*100:.1f}%)")

        if failed_by_domain:
            print(f"\n{'─'*70}")
            print("Top failing domains:")
            print(f"{'─'*70}")
            for domain, count in failed_by_domain.most_common(10):
                total_for_domain = success_by_domain[domain] + failed_by_domain[domain]
                fail_rate = (count / total_for_domain) * 100
                print(f"  {domain:50s} {count:3d} failed / {total_for_domain:3d} total ({fail_rate:5.1f}%)")

        if success_by_domain:
            print(f"\n{'─'*70}")
            print("Top successful domains:")
            print(f"{'─'*70}")
            for domain, count in success_by_domain.most_common(10):
                total_for_domain = success_by_domain[domain] + failed_by_domain[domain]
                success_rate = (count / total_for_domain) * 100
                print(f"  {domain:50s} {count:3d} / {total_for_domain:3d} ({success_rate:5.1f}%)")

        print(f"\n{'='*70}\n")


if __name__ == "__main__":
    import sys
    load_dotenv()
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    analyze_extractions(hours)
