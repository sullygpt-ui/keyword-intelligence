"""
Financial News RSS Scraper

Free alternative to FMP/SEC for Fortune 500 business terminology.
Scrapes financial news RSS feeds from major publications.
"""
import feedparser
import requests
import logging
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from config import ALL_COMPANIES

logger = logging.getLogger(__name__)


# Financial news RSS feeds covering corporate/earnings news
FINANCIAL_NEWS_FEEDS = {
    # Yahoo Finance
    'yahoo_finance': 'https://finance.yahoo.com/rss/topstories',

    # MarketWatch (only topstories works)
    'marketwatch_top': 'https://feeds.marketwatch.com/marketwatch/topstories/',

    # CNBC
    'cnbc_earnings': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135',
    'cnbc_tech': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910',
    'cnbc_finance': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664',

    # Bloomberg (via Google News RSS)
    'bloomberg_via_google': 'https://news.google.com/rss/search?q=site:bloomberg.com+earnings&hl=en-US&gl=US&ceid=US:en',

    # WSJ via Google News
    'wsj_via_google': 'https://news.google.com/rss/search?q=site:wsj.com+quarterly+results&hl=en-US&gl=US&ceid=US:en',

    # Seeking Alpha (market currents only - news feed has XML issues)
    'seeking_alpha_market': 'https://seekingalpha.com/market_currents.xml',
}

# Company-specific Google News RSS (for top Fortune 500 companies)
def get_company_news_feed(ticker: str, company_name: str) -> str:
    """Generate Google News RSS URL for a specific company"""
    query = f"{company_name} earnings quarterly results"
    encoded_query = query.replace(' ', '+')
    return f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"


# Map tickers to company names for news searches
TICKER_TO_NAME = {
    'AAPL': 'Apple',
    'MSFT': 'Microsoft',
    'GOOGL': 'Google Alphabet',
    'AMZN': 'Amazon',
    'META': 'Meta Facebook',
    'NVDA': 'NVIDIA',
    'TSLA': 'Tesla',
    'WMT': 'Walmart',
    'JPM': 'JPMorgan',
    'JNJ': 'Johnson Johnson',
    'UNH': 'UnitedHealth',
    'PG': 'Procter Gamble',
    'HD': 'Home Depot',
    'BAC': 'Bank of America',
    'PFE': 'Pfizer',
    'XOM': 'Exxon Mobil',
    'CVX': 'Chevron',
    'KO': 'Coca Cola',
    'PEP': 'PepsiCo',
    'DIS': 'Disney',
    'NFLX': 'Netflix',
    'INTC': 'Intel',
    'AMD': 'AMD',
    'CRM': 'Salesforce',
    'ORCL': 'Oracle',
}


class FinancialNewsScraper:
    """Scrapes financial news RSS feeds for corporate keyword data"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }

    def fetch_feed(self, feed_name: str, feed_url: str) -> List[Dict]:
        """Fetch and parse a single RSS feed"""
        articles = []
        try:
            logger.debug(f"Fetching feed: {feed_name}")

            # Use requests to fetch with custom headers, then parse
            response = requests.get(feed_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if feed.bozo and not feed.entries:
                logger.warning(f"Feed error for {feed_name}: {feed.bozo_exception}")
                return []

            for entry in feed.entries[:20]:  # Limit per feed
                # Get publication date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d')
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6]).strftime('%Y-%m-%d')
                else:
                    pub_date = datetime.now().strftime('%Y-%m-%d')

                # Skip articles older than 30 days
                if pub_date:
                    article_date = datetime.strptime(pub_date, '%Y-%m-%d')
                    if article_date < datetime.now() - timedelta(days=30):
                        continue

                # Get content
                content = ''
                if hasattr(entry, 'summary'):
                    content = entry.summary
                elif hasattr(entry, 'description'):
                    content = entry.description
                elif hasattr(entry, 'content'):
                    content = entry.content[0].value if entry.content else ''

                # Clean HTML from content
                if content:
                    soup = BeautifulSoup(content, 'html.parser')
                    content = soup.get_text(separator=' ')
                    content = re.sub(r'\s+', ' ', content).strip()

                articles.append({
                    'source_name': feed_name,
                    'source_type': 'financial_news',
                    'title': entry.get('title', ''),
                    'content': content,
                    'url': entry.get('link', ''),
                    'published_date': pub_date,
                })

            logger.info(f"Fetched {len(articles)} articles from {feed_name}")

        except Exception as e:
            logger.error(f"Error fetching {feed_name}: {e}")

        return articles

    def fetch_all_feeds(self) -> List[Dict]:
        """Fetch articles from all financial news feeds"""
        all_articles = []

        # Fetch general financial news feeds
        for feed_name, feed_url in FINANCIAL_NEWS_FEEDS.items():
            articles = self.fetch_feed(feed_name, feed_url)
            all_articles.extend(articles)
            time.sleep(0.5)  # Be polite

        logger.info(f"Total articles fetched from general feeds: {len(all_articles)}")
        return all_articles

    def fetch_company_news(self, tickers: List[str] = None, limit: int = 10) -> List[Dict]:
        """Fetch news for specific companies via Google News RSS"""
        tickers = tickers or list(TICKER_TO_NAME.keys())[:limit]
        all_articles = []

        for ticker in tickers:
            company_name = TICKER_TO_NAME.get(ticker)
            if not company_name:
                continue

            feed_url = get_company_news_feed(ticker, company_name)
            articles = self.fetch_feed(f"company_{ticker}", feed_url)

            # Tag with company ticker
            for article in articles:
                article['ticker'] = ticker

            all_articles.extend(articles)
            time.sleep(1)  # Be extra polite with Google News

        logger.info(f"Total articles fetched for companies: {len(all_articles)}")
        return all_articles

    def get_new_articles(self, db, articles: List[Dict]) -> List[Dict]:
        """Filter out already processed articles"""
        new_articles = []
        for article in articles:
            # Use URL as unique identifier
            identifier = article.get('url', '')
            if identifier and not db.is_source_processed('financial_news', identifier):
                new_articles.append(article)
        return new_articles


def main():
    """Test financial news scraper"""
    logging.basicConfig(level=logging.INFO)

    scraper = FinancialNewsScraper()

    # Test general feeds
    print("\n=== Testing General Financial News Feeds ===")
    articles = scraper.fetch_all_feeds()
    print(f"\nTotal articles: {len(articles)}")

    for i, article in enumerate(articles[:5]):
        print(f"\n--- Article {i+1} ---")
        print(f"Source: {article['source_name']}")
        print(f"Title: {article['title'][:80]}...")
        print(f"Date: {article['published_date']}")
        print(f"Content preview: {article['content'][:200]}...")

    # Test company-specific feeds
    print("\n\n=== Testing Company News Feeds ===")
    company_articles = scraper.fetch_company_news(['AAPL', 'MSFT', 'NVDA'], limit=3)
    print(f"\nTotal company articles: {len(company_articles)}")

    for i, article in enumerate(company_articles[:5]):
        print(f"\n--- Article {i+1} ---")
        print(f"Company: {article.get('ticker', 'N/A')}")
        print(f"Title: {article['title'][:80]}...")


if __name__ == "__main__":
    main()
