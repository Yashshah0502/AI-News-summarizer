#!/usr/bin/env python3
"""
Migration: Add extraction retry columns
Adds extraction_attempts and next_extract_at columns to articles table
"""
from sqlalchemy import text
from app.services.database import engine

def migrate():
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'articles'
            AND column_name IN ('extraction_attempts', 'next_extract_at')
        """))
        existing_columns = {row[0] for row in result}

        if 'extraction_attempts' not in existing_columns:
            print("Adding extraction_attempts column...")
            conn.execute(text("""
                ALTER TABLE articles
                ADD COLUMN extraction_attempts INTEGER NOT NULL DEFAULT 0
            """))
            conn.commit()
            print("✓ Added extraction_attempts column")
        else:
            print("✓ extraction_attempts column already exists")

        if 'next_extract_at' not in existing_columns:
            print("Adding next_extract_at column...")
            conn.execute(text("""
                ALTER TABLE articles
                ADD COLUMN next_extract_at TIMESTAMP WITH TIME ZONE
            """))
            conn.commit()
            print("✓ Added next_extract_at column")
        else:
            print("✓ next_extract_at column already exists")

        print("\n✅ Migration complete!")

if __name__ == "__main__":
    migrate()
