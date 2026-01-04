"""
Google News Scraper
Scrapes top stories and category news (Tech, Business, Politics) from Google News using RSS feeds
"""

import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict
import re


class GoogleNewsScraper:
    """Scraper for Google News articles from the last 24 hours"""

    def __init__(self, hours_limit=24):
        """
        Initialize the scraper

        Args:
            hours_limit: Only include articles from the last N hours (default: 24)
        """
        self.base_url = "https://news.google.com"
        self.rss_base = "https://news.google.com/rss"
        self.hours_limit = hours_limit
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Using RSS feeds for better reliability
        self.categories = {
            'top_stories': f'{self.rss_base}',
            'technology': f'{self.rss_base}/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB',
            'business': f'{self.rss_base}/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB',
            'politics': f'{self.rss_base}/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRFZ4ZERBU0FtVnVLQUFQAQ'
        }

    def scrape_category(self, category: str) -> List[Dict]:
        """
        Scrape articles from a specific category using RSS feed

        Args:
            category: One of 'top_stories', 'technology', 'business', 'politics'

        Returns:
            List of article dictionaries
        """
        if category not in self.categories:
            raise ValueError(f"Invalid category. Choose from: {list(self.categories.keys())}")

        url = self.categories[category]
        articles = []

        # Calculate cutoff time for filtering
        cutoff_time = datetime.now() - timedelta(hours=self.hours_limit)

        try:
            # Parse RSS feed
            feed = feedparser.parse(url)

            # Check if feed was parsed successfully
            if not feed.entries:
                print(f"⚠ No entries found in Google News - {category}")
                return articles

            total_checked = 0
            for entry in feed.entries[:50]:  # Check more entries to find enough recent ones
                try:
                    total_checked += 1

                    # Extract title
                    title = entry.get('title', '')

                    # Extract link
                    link = entry.get('link', '')

                    # Extract published time
                    pub_time = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_time = datetime(*entry.published_parsed[:6])

                    # Filter by time - only include articles within the time limit
                    if pub_time and pub_time < cutoff_time:
                        continue  # Skip articles older than the cutoff

                    # Extract source from title (Google News format: "Title - Source")
                    source = 'Google News'
                    if ' - ' in title:
                        # Source is usually at the end
                        parts = title.rsplit(' - ', 1)
                        if len(parts) == 2:
                            source = parts[1]

                    if title and link:
                        articles.append({
                            'title': title,
                            'link': link,
                            'source': source,
                            'category': category,
                            'published_time': pub_time.isoformat() if pub_time else '',
                            'scraped_at': datetime.now().isoformat()
                        })

                        # Stop after getting 20 recent articles
                        if len(articles) >= 20:
                            break

                except Exception as e:
                    # Skip problematic articles
                    continue

            print(f"✓ Scraped {len(articles)} articles from Google News - {category} (checked {total_checked}, last {self.hours_limit}h)")

        except Exception as e:
            print(f"✗ Error scraping Google News {category}: {str(e)}")

        return articles

    def scrape_all(self) -> Dict[str, List[Dict]]:
        """
        Scrape all categories

        Returns:
            Dictionary with category names as keys and article lists as values
        """
        results = {}

        for category in self.categories.keys():
            results[category] = self.scrape_category(category)

        return results

    def get_last_24h_articles(self) -> List[Dict]:
        """
        Scrape all categories and return combined results

        Returns:
            List of all articles from last 24 hours
        """
        all_articles = []
        results = self.scrape_all()

        for category, articles in results.items():
            all_articles.extend(articles)

        print(f"\n📰 Total articles scraped from Google News: {len(all_articles)}")
        return all_articles


def main():
    """Test function to run the scraper"""
    print("🚀 Starting Google News Scraper...\n")

    scraper = GoogleNewsScraper()
    articles = scraper.get_last_24h_articles()

    # Print sample results
    print("\n" + "="*80)
    print("SAMPLE RESULTS (first 5 articles):")
    print("="*80 + "\n")

    for i, article in enumerate(articles[:5], 1):
        print(f"{i}. {article['title']}")
        print(f"   Category: {article['category']}")
        print(f"   Source: {article['source']}")
        print(f"   Link: {article['link']}")
        print(f"   Time: {article['published_time']}")
        print()

    return articles


if __name__ == "__main__":
    main()
