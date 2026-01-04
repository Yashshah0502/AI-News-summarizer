"""
Tech & AI Blog Scraper
Scrapes latest posts from tech company blogs (Anthropic, OpenAI, etc.)
"""

import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict
import re


class TechBlogScraper:
    """Scraper for tech and AI company blogs from the last 24 hours"""

    def __init__(self, hours_limit=24):
        """
        Initialize the scraper

        Args:
            hours_limit: Only include articles from the last N hours (default: 24)
        """
        self.hours_limit = hours_limit
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # RSS feeds for major tech blogs
        self.blogs = {
            'anthropic': {
                'name': 'Anthropic',
                'url': 'https://www.anthropic.com/news',
                'type': 'web'
            },
            'openai': {
                'name': 'OpenAI',
                'url': 'https://openai.com/news/rss.xml',
                'type': 'rss'
            },
            'techcrunch_ai': {
                'name': 'TechCrunch AI',
                'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
                'type': 'rss'
            },
            'verge_tech': {
                'name': 'The Verge',
                'url': 'https://www.theverge.com/rss/index.xml',
                'type': 'rss'
            },
            'hackernews': {
                'name': 'Hacker News',
                'url': 'https://news.ycombinator.com/',
                'type': 'web'
            }
        }

    def scrape_rss_feed(self, blog_name: str, feed_url: str) -> List[Dict]:
        """
        Scrape articles from an RSS feed

        Args:
            blog_name: Name of the blog
            feed_url: URL of the RSS feed

        Returns:
            List of article dictionaries
        """
        articles = []
        cutoff_time = datetime.now() - timedelta(hours=self.hours_limit)

        try:
            feed = feedparser.parse(feed_url)

            total_checked = 0
            for entry in feed.entries[:30]:  # Check more entries to find recent ones
                try:
                    total_checked += 1

                    # Parse published time
                    pub_time = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_time = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_time = datetime(*entry.updated_parsed[:6])

                    # Filter by time - skip if older than cutoff
                    if pub_time and pub_time < cutoff_time:
                        continue

                    # Extract article data
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '')

                    if title and link:
                        articles.append({
                            'title': title,
                            'link': link,
                            'source': blog_name,
                            'summary': summary[:200] + '...' if len(summary) > 200 else summary,
                            'category': 'tech_blog',
                            'published_time': pub_time.isoformat() if pub_time else '',
                            'scraped_at': datetime.now().isoformat()
                        })

                        # Stop after getting 15 recent articles
                        if len(articles) >= 15:
                            break

                except Exception as e:
                    continue

            print(f"✓ Scraped {len(articles)} articles from {blog_name} (RSS) - last {self.hours_limit}h")

        except Exception as e:
            print(f"✗ Error scraping {blog_name} RSS feed: {str(e)}")

        return articles

    def scrape_anthropic(self) -> List[Dict]:
        """Scrape Anthropic news page"""
        articles = []
        try:
            url = 'https://www.anthropic.com/news'
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article elements (adjust selectors based on actual page structure)
            article_elements = soup.find_all('a', href=re.compile(r'/news/'))

            for element in article_elements[:10]:
                try:
                    title = element.get_text(strip=True)
                    link = element.get('href', '')

                    if link and not link.startswith('http'):
                        link = 'https://www.anthropic.com' + link

                    if title and link and len(title) > 10:
                        articles.append({
                            'title': title,
                            'link': link,
                            'source': 'Anthropic',
                            'category': 'tech_blog',
                            'published_time': '',
                            'scraped_at': datetime.now().isoformat()
                        })

                except Exception as e:
                    continue

            # Remove duplicates
            seen_links = set()
            unique_articles = []
            for article in articles:
                if article['link'] not in seen_links:
                    seen_links.add(article['link'])
                    unique_articles.append(article)

            print(f"✓ Scraped {len(unique_articles)} articles from Anthropic - last {self.hours_limit}h")
            return unique_articles

        except Exception as e:
            print(f"✗ Error scraping Anthropic: {str(e)}")
            return []

    def scrape_openai(self) -> List[Dict]:
        """Scrape OpenAI via official News RSS (avoids /blog 403)."""
        try:
            return self.scrape_rss_feed('OpenAI', self.blogs['openai']['url'])
        except Exception as e:
            print(f"✗ Error scraping OpenAI (RSS): {str(e)}")
            return []

    def scrape_hackernews(self) -> List[Dict]:
        """Scrape Hacker News front page"""
        articles = []
        try:
            url = 'https://news.ycombinator.com/'
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find story titles
            story_elements = soup.find_all('span', class_='titleline')

            for element in story_elements[:15]:
                try:
                    link_elem = element.find('a')
                    if not link_elem:
                        continue

                    title = link_elem.get_text(strip=True)
                    link = link_elem.get('href', '')

                    # Fix relative links
                    if link.startswith('item?id='):
                        link = 'https://news.ycombinator.com/' + link

                    if title and link:
                        articles.append({
                            'title': title,
                            'link': link,
                            'source': 'Hacker News',
                            'category': 'tech_blog',
                            'published_time': '',
                            'scraped_at': datetime.now().isoformat()
                        })

                except Exception as e:
                    continue

            print(f"✓ Scraped {len(articles)} articles from Hacker News - last {self.hours_limit}h")
            return articles

        except Exception as e:
            print(f"✗ Error scraping Hacker News: {str(e)}")
            return []

    def scrape_all(self) -> Dict[str, List[Dict]]:
        """
        Scrape all tech blogs

        Returns:
            Dictionary with blog names as keys and article lists as values
        """
        results = {}

        # Scrape RSS feeds
        results['techcrunch_ai'] = self.scrape_rss_feed('TechCrunch AI', self.blogs['techcrunch_ai']['url'])
        results['verge'] = self.scrape_rss_feed('The Verge', self.blogs['verge_tech']['url'])

        # Scrape web pages
        results['anthropic'] = self.scrape_anthropic()
        results['openai'] = self.scrape_openai()
        results['hackernews'] = self.scrape_hackernews()

        return results

    def get_last_24h_articles(self) -> List[Dict]:
        """
        Scrape all blogs and return combined results

        Returns:
            List of all articles from last 24 hours
        """
        all_articles = []
        results = self.scrape_all()

        for blog, articles in results.items():
            all_articles.extend(articles)

        print(f"\n📰 Total articles scraped from Tech Blogs: {len(all_articles)}")
        return all_articles


def main():
    """Test function to run the scraper"""
    print("🚀 Starting Tech Blog Scraper...\n")

    scraper = TechBlogScraper()
    articles = scraper.get_last_24h_articles()

    # Print sample results
    print("\n" + "="*80)
    print("SAMPLE RESULTS (first 5 articles):")
    print("="*80 + "\n")

    for i, article in enumerate(articles[:5], 1):
        print(f"{i}. {article['title']}")
        print(f"   Source: {article['source']}")
        print(f"   Link: {article['link']}")
        if article.get('summary'):
            print(f"   Summary: {article['summary']}")
        if article['published_time']:
            print(f"   Time: {article['published_time']}")
        print()

    return articles


if __name__ == "__main__":
    main()
