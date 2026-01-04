# scripts/check_article_sources.py
"""
Check what sources we have in the database.
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


def check_sources(hours: int = 24):
    """Check what sources and domains we have."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with SessionLocal() as session:
        articles = session.query(Article).filter(
            Article.scraped_at >= cutoff
        ).all()

        print(f"\n{'='*70}")
        print(f"Article Sources - Last {hours} hours")
        print(f"{'='*70}\n")

        # Count by source
        source_counts = Counter(a.source for a in articles)
        print("By Source:")
        for source, count in source_counts.most_common():
            print(f"  {source:30s}: {count:3d} articles")

        # Count by domain
        domain_counts = Counter(urlparse(a.url).netloc for a in articles)
        print(f"\nBy Domain:")
        for domain, count in domain_counts.most_common():
            print(f"  {domain:50s}: {count:3d} articles")

        # Show some non-Google News URLs
        print(f"\nSample non-Google News URLs:")
        non_google = [a for a in articles if 'news.google.com' not in a.url][:10]
        for i, article in enumerate(non_google, 1):
            print(f"{i}. {article.url[:80]}...")
            print(f"   Source: {article.source}, Status: {article.extraction_status}")

        print(f"\n{'='*70}\n")


if __name__ == "__main__":
    load_dotenv()
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    check_sources(hours)
