#!/usr/bin/env python3
"""
Cleanup existing failed extractions and apply migration

This script:
1. Runs the migration to add retry columns
2. Resets extraction_attempts for all articles to 0
3. Clears next_extract_at for all articles
4. Updates extraction_status for known skip domains
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.services.database import engine
from app.services.extract_repo import SKIP_DOMAINS

def main():
    print("=" * 80)
    print("CLEANUP AND MIGRATION")
    print("=" * 80)

    # Step 1: Run migration
    print("\n📦 Step 1: Running migration...")
    from scripts.migrate_add_retry_columns import migrate
    migrate()

    # Step 2: Reset extraction attempts
    print("\n🔄 Step 2: Resetting extraction attempts...")
    with engine.connect() as conn:
        # Reset all extraction attempts to 0
        result = conn.execute(text("""
            UPDATE articles
            SET extraction_attempts = 0,
                next_extract_at = NULL
        """))
        conn.commit()
        print(f"✓ Reset {result.rowcount} articles")

        # Mark skip domains as skipped
        print("\n🚫 Step 3: Marking skip domains...")
        skip_domains_str = "', '".join(SKIP_DOMAINS)
        for domain in SKIP_DOMAINS:
            result = conn.execute(text(f"""
                UPDATE articles
                SET extraction_status = 'skipped',
                    extraction_attempts = 0,
                    next_extract_at = NULL
                WHERE url LIKE '%{domain}%'
                AND content_text IS NULL
            """))
            if result.rowcount > 0:
                print(f"  ✓ Marked {result.rowcount} articles from {domain} as skipped")
        conn.commit()

        # Show summary
        print("\n📊 Summary:")
        result = conn.execute(text("""
            SELECT
                extraction_status,
                COUNT(*) as count
            FROM articles
            WHERE content_text IS NULL
            GROUP BY extraction_status
            ORDER BY count DESC
        """))
        for row in result:
            status = row[0] or "(null)"
            count = row[1]
            print(f"  {status}: {count} articles")

    print("\n✅ Cleanup and migration complete!")
    print("\n💡 You can now run the graph and it will:")
    print("   - Skip domains in the skiplist")
    print("   - Retry failed extractions with exponential backoff")
    print("   - Stop retrying after 3 attempts")

if __name__ == "__main__":
    main()
