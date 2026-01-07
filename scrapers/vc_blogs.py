"""
VC Blog RSS Feed Scraper

Scrapes top VC blogs for emerging technology and business terms.
"""
import feedparser
import requests
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re

from config import VC_BLOGS, RSS_DELAY_SECONDS

logger = logging.getLogger(__name__)


class VCBlogScraper:
    """Scrapes VC blog RSS feeds for content"""

    def __init__(self):
        self.blogs = VC_BLOGS
        self.user_agent = "KeywordIntelligence/1.0 (https://sullysblog.com)"

    def fetch_feed(self, name: str, url: str) -> List[Dict]:
        """Fetch and parse a single RSS feed"""
        posts = []
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            for entry in feed.entries:
                post = self._parse_entry(entry, name, url)
                if post:
                    posts.append(post)

            logger.info(f"Fetched {len(posts)} posts from {name}")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch {name} feed: {e}")
        except Exception as e:
            logger.error(f"Error parsing {name} feed: {e}")

        return posts

    def _parse_entry(self, entry, source_name: str, feed_url: str) -> Optional[Dict]:
        """Parse a single RSS entry"""
        try:
            # Get publication date
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d')
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6]).strftime('%Y-%m-%d')
            else:
                pub_date = datetime.now().strftime('%Y-%m-%d')

            # Get content
            content = ""
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].get('value', '')
            elif hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description

            # Strip HTML tags for text processing
            text_content = self._strip_html(content)

            # Get title
            title = entry.get('title', '')

            # Get URL
            url = entry.get('link', '')

            return {
                'source_name': source_name,
                'source_type': 'vc_blog',
                'title': title,
                'content': text_content,
                'html_content': content,
                'url': url,
                'published_date': pub_date,
                'feed_url': feed_url,
            }

        except Exception as e:
            logger.error(f"Error parsing entry from {source_name}: {e}")
            return None

    def _strip_html(self, html_content: str) -> str:
        """Remove HTML tags and clean text"""
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()

        # Get text
        text = soup.get_text(separator=' ')

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def fetch_all_feeds(self) -> List[Dict]:
        """Fetch all configured VC blog feeds"""
        all_posts = []

        for name, url in self.blogs.items():
            logger.info(f"Fetching {name}...")
            posts = self.fetch_feed(name, url)
            all_posts.extend(posts)

            # Rate limiting
            time.sleep(RSS_DELAY_SECONDS)

        logger.info(f"Total posts fetched: {len(all_posts)}")
        return all_posts

    def get_new_posts(self, db, posts: List[Dict]) -> List[Dict]:
        """Filter out already processed posts"""
        new_posts = []
        for post in posts:
            if not db.is_source_processed('vc_blog', post['url']):
                new_posts.append(post)
        return new_posts


def main():
    """Test the scraper"""
    logging.basicConfig(level=logging.INFO)
    scraper = VCBlogScraper()
    posts = scraper.fetch_all_feeds()

    print(f"\nFetched {len(posts)} total posts")
    for post in posts[:5]:
        print(f"\n--- {post['source_name']} ---")
        print(f"Title: {post['title']}")
        print(f"Date: {post['published_date']}")
        print(f"URL: {post['url']}")
        print(f"Content preview: {post['content'][:200]}...")


if __name__ == "__main__":
    main()
