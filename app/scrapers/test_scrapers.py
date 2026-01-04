"""
Test runner for all news scrapers
Run this script to test individual scrapers or all at once
"""

import sys
import json
from datetime import datetime

try:
    from googlenews import GoogleNewsScraper
    from timesofindia import TimesOfIndiaScraper
    from techblogs import TechBlogScraper
except ImportError:
    # Try importing from app.scrapers if running from project root
    from app.scrapers.googlenews import GoogleNewsScraper
    from app.scrapers.timesofindia import TimesOfIndiaScraper
    from app.scrapers.techblogs import TechBlogScraper


def print_banner(text):
    """Print a formatted banner"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def test_google_news():
    """Test Google News scraper"""
    print_banner("TESTING GOOGLE NEWS SCRAPER")
    scraper = GoogleNewsScraper()
    articles = scraper.get_last_24h_articles()
    return articles


def test_times_of_india():
    """Test Times of India scraper"""
    print_banner("TESTING TIMES OF INDIA SCRAPER")
    scraper = TimesOfIndiaScraper()
    articles = scraper.get_last_24h_articles()
    return articles


def test_tech_blogs():
    """Test Tech Blogs scraper"""
    print_banner("TESTING TECH BLOGS SCRAPER")
    scraper = TechBlogScraper()
    articles = scraper.get_last_24h_articles()
    return articles


def test_all_scrapers():
    """Run all scrapers and combine results"""
    print_banner("TESTING ALL SCRAPERS")

    all_results = {
        'google_news': [],
        'times_of_india': [],
        'tech_blogs': []
    }

    # Test each scraper
    print("1. Running Google News scraper...")
    try:
        all_results['google_news'] = test_google_news()
    except Exception as e:
        print(f"✗ Google News failed: {str(e)}\n")

    print("\n2. Running Times of India scraper...")
    try:
        all_results['times_of_india'] = test_times_of_india()
    except Exception as e:
        print(f"✗ Times of India failed: {str(e)}\n")

    print("\n3. Running Tech Blogs scraper...")
    try:
        all_results['tech_blogs'] = test_tech_blogs()
    except Exception as e:
        print(f"✗ Tech Blogs failed: {str(e)}\n")

    # Summary
    print_banner("SUMMARY")
    total = sum(len(articles) for articles in all_results.values())
    print(f"Total articles scraped: {total}")
    print(f"  - Google News: {len(all_results['google_news'])} articles")
    print(f"  - Times of India: {len(all_results['times_of_india'])} articles")
    print(f"  - Tech Blogs: {len(all_results['tech_blogs'])} articles")

    # Show sample articles
    print_banner("SAMPLE ARTICLES FROM EACH SOURCE")

    for source, articles in all_results.items():
        if articles:
            print(f"\n📰 {source.upper().replace('_', ' ')}:")
            for i, article in enumerate(articles[:3], 1):
                print(f"\n  {i}. {article['title']}")
                print(f"     Source: {article['source']}")
                print(f"     Category: {article.get('category', 'N/A')}")
                print(f"     Link: {article['link'][:60]}...")

    return all_results


def save_results_to_file(results, filename=None):
    """Save scraping results to a JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scraping_results_{timestamp}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Results saved to: {filename}")
    return filename


def main():
    """Main test runner"""
    print("\n" + "🚀 NEWS SCRAPER TEST SUITE ".center(80, "="))

    if len(sys.argv) > 1:
        scraper_name = sys.argv[1].lower()

        if scraper_name == 'google' or scraper_name == 'googlenews':
            results = test_google_news()
        elif scraper_name == 'toi' or scraper_name == 'timesofindia':
            results = test_times_of_india()
        elif scraper_name == 'tech' or scraper_name == 'techblogs':
            results = test_tech_blogs()
        elif scraper_name == 'all':
            results = test_all_scrapers()
            if '--save' in sys.argv:
                save_results_to_file(results)
        else:
            print(f"\n❌ Unknown scraper: {scraper_name}")
            print("\nUsage:")
            print("  python test_scrapers.py [scraper_name] [--save]")
            print("\nAvailable scrapers:")
            print("  - google (or googlenews)")
            print("  - toi (or timesofindia)")
            print("  - tech (or techblogs)")
            print("  - all (runs all scrapers)")
            print("\nOptions:")
            print("  --save : Save results to JSON file (only with 'all')")
            return
    else:
        # Default: run all scrapers
        results = test_all_scrapers()

    print("\n" + "TESTING COMPLETE ".center(80, "=") + "\n")


if __name__ == "__main__":
    main()
