"""
Simple script to run scrapers with customizable time window
"""

import sys
from googlenews import GoogleNewsScraper
from timesofindia import TimesOfIndiaScraper
from techblogs import TechBlogScraper


def print_banner(text):
    """Print a formatted banner"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


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

    # Initialize scrapers with custom time window
    google_scraper = GoogleNewsScraper(hours_limit=hours)
    toi_scraper = TimesOfIndiaScraper(hours_limit=hours)
    tech_scraper = TechBlogScraper(hours_limit=hours)

    # Collect all articles
    all_articles = []

    print(f"\n1️⃣  Google News (last {hours} hours)")
    print("-" * 80)
    google_articles = google_scraper.get_last_24h_articles()
    all_articles.extend(google_articles)

    print(f"\n2️⃣  Times of India (last {hours} hours)")
    print("-" * 80)
    toi_articles = toi_scraper.get_last_24h_articles()
    all_articles.extend(toi_articles)

    print(f"\n3️⃣  Tech Blogs (last {hours} hours)")
    print("-" * 80)
    tech_articles = tech_scraper.get_last_24h_articles()
    all_articles.extend(tech_articles)

    # Summary
    print_banner("FINAL SUMMARY")
    print(f"Time Window: Last {hours} hours")
    print(f"Total Articles: {len(all_articles)}")
    print(f"  - Google News: {len(google_articles)} articles")
    print(f"  - Times of India: {len(toi_articles)} articles")
    print(f"  - Tech Blogs: {len(tech_articles)} articles")

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
