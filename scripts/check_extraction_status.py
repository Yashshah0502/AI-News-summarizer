#!/usr/bin/env python3
"""
Check extraction status and show retry queue
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.services.database import engine
from datetime import datetime

def main():
    print("=" * 80)
    print("EXTRACTION STATUS REPORT")
    print("=" * 80)

    with engine.connect() as conn:
        # Overall stats
        print("\n📊 Overall Statistics:")
        result = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE content_text IS NOT NULL) as extracted,
                COUNT(*) FILTER (WHERE content_text IS NULL) as not_extracted,
                COUNT(*) as total
            FROM articles
        """))
        row = result.fetchone()
        extracted, not_extracted, total = row[0], row[1], row[2]
        pct = (extracted / total * 100) if total > 0 else 0
        print(f"  Total articles: {total}")
        print(f"  Extracted: {extracted} ({pct:.1f}%)")
        print(f"  Not extracted: {not_extracted}")

        # Extraction status breakdown
        print("\n📋 Articles Without Content (by status):")
        result = conn.execute(text("""
            SELECT
                COALESCE(extraction_status, '(null)') as status,
                COUNT(*) as count,
                ROUND(AVG(extraction_attempts), 1) as avg_attempts
            FROM articles
            WHERE content_text IS NULL
            GROUP BY extraction_status
            ORDER BY count DESC
        """))
        for row in result:
            status, count, avg_attempts = row[0], row[1], row[2] or 0
            print(f"  {status:15} {count:5} articles (avg {avg_attempts} attempts)")

        # Retry queue
        print("\n⏰ Retry Queue (articles in cooldown):")
        result = conn.execute(text("""
            SELECT
                url,
                extraction_attempts,
                next_extract_at
            FROM articles
            WHERE content_text IS NULL
            AND next_extract_at IS NOT NULL
            ORDER BY next_extract_at
            LIMIT 10
        """))
        rows = result.fetchall()
        if rows:
            for row in rows:
                url, attempts, next_at = row[0], row[1], row[2]
                time_left = (next_at - datetime.now()).total_seconds() / 60
                print(f"  [{attempts} attempts] {url[:60]}...")
                print(f"    → Retry in {time_left:.0f} minutes ({next_at.strftime('%H:%M:%S')})")
        else:
            print("  (No articles in cooldown)")

        # Failed domains breakdown
        print("\n❌ Top Failed Domains:")
        result = conn.execute(text("""
            SELECT
                SUBSTRING(url FROM 'https?://([^/]+)') as domain,
                COUNT(*) as count
            FROM articles
            WHERE extraction_status = 'failed'
            GROUP BY domain
            ORDER BY count DESC
            LIMIT 10
        """))
        for row in result:
            domain, count = row[0], row[1]
            if domain:
                print(f"  {domain:40} {count:3} failures")

        # Ready for extraction
        print("\n✅ Ready for Extraction Now:")
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM articles
            WHERE content_text IS NULL
            AND (extraction_status IS NULL OR extraction_attempts < 3)
            AND (next_extract_at IS NULL OR next_extract_at <= NOW())
            AND extraction_status != 'skipped'
        """))
        ready_count = result.fetchone()[0]
        print(f"  {ready_count} articles ready to be extracted")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
