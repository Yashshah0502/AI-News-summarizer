"""
Simple script to run scrapers with customizable time window
"""

import sys
from typing import List, Dict

from app.scrapers.googlenews import GoogleNewsScraper
from app.scrapers.timesofindia import TimesOfIndiaScraper
from app.scrapers.techblogs import TechBlogScraper


def print_banner(text):
    """Print a formatted banner"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def run(hours: int = 10) -> List[Dict]:
    """
    Run all scrapers and return collected articles.

    Args:
        hours: Number of hours to look back for articles (default: 10)

    Returns:
        List of article dictionaries from all scrapers
    """
    google_scraper = GoogleNewsScraper(hours_limit=hours)
    toi_scraper = TimesOfIndiaScraper(hours_limit=hours)
    tech_scraper = TechBlogScraper(hours_limit=hours)

    all_articles = []
    all_articles.extend(google_scraper.get_last_24h_articles())
    all_articles.extend(toi_scraper.get_last_24h_articles())
    all_articles.extend(tech_scraper.get_last_24h_articles())
    return all_articles


def main():
    # Default: 24 hours
    hours = 24

    # Check if user specified a different time window
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
        except ValueError:
            print("Usage: python run_scrapers.py [hours]")
            print("Example: python run_scrapers.py 12  (for last 12 hours)")
            print("Example: python run_scrapers.py 48  (for last 48 hours)")
            return

    print_banner(f"NEWS SCRAPERS - LAST {hours} HOURS")

    # Run all scrapers and collect articles
    all_articles = run(hours)

    # Summary
    print_banner("FINAL SUMMARY")
    print(f"Time Window: Last {hours} hours")
    print(f"Total Articles: {len(all_articles)}")

    # Show some sample articles
    print(f"\n📰 Sample Recent Articles:")
    for i, article in enumerate(all_articles[:10], 1):
        print(f"\n{i}. {article['title'][:70]}...")
        print(f"   Source: {article['source']}")
        if article.get('published_time'):
            print(f"   Published: {article['published_time']}")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
