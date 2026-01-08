"""
Times of India News Scraper
Scrapes top stories and category news (Tech, Business, Politics) from Times of India
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict
import re


class TimesOfIndiaScraper:
    """Scraper for Times of India articles from the last 24 hours"""

    def __init__(self, hours_limit=24):
        """
        Initialize the scraper

        Args:
            hours_limit: Only include articles from the last N hours (default: 24)
        """
        self.base_url = "https://timesofindia.indiatimes.com"
        self.hours_limit = hours_limit
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.categories = {
            'top_stories': '/home/headlines',
            'technology': '/technology/tech-news',
            'business': '/business',
            'politics': '/india'
        }

    def _parse_relative_time(self, time_str: str) -> datetime:
        """
        Parse relative time strings like '2 hours ago', '5 mins ago', etc.

        Args:
            time_str: Time string to parse

        Returns:
            datetime object or None if can't parse
        """
        if not time_str:
            return None

        time_str = time_str.lower().strip()
        now = datetime.now()

        try:
            # Match patterns like "X hours ago", "X mins ago", "X days ago"
            if 'min' in time_str or 'minute' in time_str:
                mins = int(re.search(r'(\d+)', time_str).group(1))
                return now - timedelta(minutes=mins)
            elif 'hour' in time_str:
                hours = int(re.search(r'(\d+)', time_str).group(1))
                return now - timedelta(hours=hours)
            elif 'day' in time_str:
                days = int(re.search(r'(\d+)', time_str).group(1))
                return now - timedelta(days=days)
            elif 'just now' in time_str or 'now' in time_str:
                return now
        except (AttributeError, ValueError):
            pass

        return None

    def scrape_category(self, category: str) -> List[Dict]:
        """
        Scrape articles from a specific category

        Args:
            category: One of 'top_stories', 'technology', 'business', 'politics'

        Returns:
            List of article dictionaries
        """
        if category not in self.categories:
            raise ValueError(f"Invalid category. Choose from: {list(self.categories.keys())}")

        url = self.base_url + self.categories[category]
        articles = []
        cutoff_time = datetime.now() - timedelta(hours=self.hours_limit)

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article links - TOI uses various structures
            # Method 1: Find article containers with specific classes
            article_elements = soup.find_all(['div', 'li'], class_=re.compile('(uwU81|_2jWI5|brief|BIG_|top-newslist)'))

            # Method 2: Also find direct links to articles
            if not article_elements:
                article_elements = soup.find_all('a', href=re.compile(r'/articleshow/'))

            total_checked = 0
            for element in article_elements[:50]:  # Check more articles to find recent ones
                try:
                    total_checked += 1

                    # Find the link element
                    link_elem = element.find('a') if element.name != 'a' else element
                    if not link_elem:
                        continue

                    # Extract link
                    link = link_elem.get('href', '')
                    if link.startswith('/'):
                        link = self.base_url + link

                    # Skip if not a valid article link
                    if '/articleshow/' not in link:
                        continue

                    # Extract title
                    title = link_elem.get_text(strip=True)
                    if not title or len(title) < 10:
                        # Try to find title in nested elements
                        title_elem = element.find(['h2', 'h3', 'h4', 'span'], class_=re.compile('.*(title|headline).*', re.IGNORECASE))
                        if title_elem:
                            title = title_elem.get_text(strip=True)

                    # Extract time if available
                    time_elem = element.find('span', class_=re.compile('.*(time|date).*', re.IGNORECASE))
                    time_str = time_elem.get_text(strip=True) if time_elem else ''

                    # Try to parse and filter by time
                    article_time = self._parse_relative_time(time_str)
                    if article_time and article_time < cutoff_time:
                        continue  # Skip articles older than cutoff

                    if title and link:
                        articles.append({
                            'title': title,
                            'link': link,
                            'source': 'Times of India',
                            'category': category,
                            'published_time': time_str,
                            'scraped_at': datetime.now().isoformat()
                        })

                        # Stop after getting 20 recent articles
                        if len(articles) >= 20:
                            break

                except Exception as e:
                    # Skip problematic articles
                    continue

            # Remove duplicates based on link
            seen_links = set()
            unique_articles = []
            for article in articles:
                if article['link'] not in seen_links:
                    seen_links.add(article['link'])
                    unique_articles.append(article)

            print(f"✓ Scraped {len(unique_articles)} articles from Times of India - {category} (checked {total_checked}, last {self.hours_limit}h)")
            return unique_articles

        except requests.RequestException as e:
            print(f"✗ Error scraping Times of India {category}: {str(e)}")
            return []

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

        print(f"\n📰 Total articles scraped from Times of India: {len(all_articles)}")
        return all_articles


def main():
    """Test function to run the scraper"""
    print("Starting Times of India Scraper...\n")

    scraper = TimesOfIndiaScraper()
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
