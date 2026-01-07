"""
Configuration for Keyword Intelligence System
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# API Keys (set via environment variables)
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
WORDPRESS_URL = os.getenv("WORDPRESS_URL", "https://sullysblog.com/xmlrpc.php")
WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME", "")
WORDPRESS_PASSWORD = os.getenv("WORDPRESS_PASSWORD", "")

# VC Blog RSS Feeds
VC_BLOGS = {
    'a16z': 'https://a16z.com/blog/feed/',
    'sequoia': 'https://sequoiacap.com/feed/',
    'greylock': 'https://greylock.com/feed/',
    # Note: Some VC blogs don't have public RSS feeds
    # 'bessemer': 'https://www.bvp.com/atlas/rss',  # No longer available
    # 'nfx': 'https://www.nfx.com/feed',  # No longer available
    # 'first_round': 'https://review.firstround.com/feed',  # No longer available
}

# Fortune 500 companies to track (by sector)
FMP_COMPANIES = {
    'tech': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'CRM', 'ORCL', 'ADBE', 'IBM', 'INTC', 'CSCO', 'AMD', 'QCOM'],
    'retail': ['WMT', 'TGT', 'HD', 'COST', 'NKE', 'LOW', 'TJX', 'ROSS', 'DG', 'DLTR'],
    'industrial': ['GE', 'CAT', 'BA', 'HON', 'MMM', 'UPS', 'RTX', 'LMT', 'DE', 'EMR'],
    'healthcare': ['JNJ', 'UNH', 'PFE', 'ABT', 'TMO', 'MRK', 'LLY', 'ABBV', 'CVS', 'CI'],
    'financial': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'C', 'AXP', 'SCHW', 'USB'],
}

# Flatten company list
ALL_COMPANIES = [ticker for sector in FMP_COMPANIES.values() for ticker in sector]

# Processing settings
MIN_KEYWORD_LENGTH = 2  # Minimum words in phrase
MAX_KEYWORD_LENGTH = 4  # Maximum words in phrase
MIN_MENTIONS = 2        # Minimum mentions to include in report
WEEKLY_LIMIT = 50       # Top N keywords to report per tier

# Rate limiting
FMP_RATE_LIMIT_SECONDS = 12  # 5 calls/minute = 1 call every 12 seconds
FMP_DAILY_LIMIT = 250        # Free tier daily limit
RSS_DELAY_SECONDS = 2        # Delay between RSS feed fetches

# Database
DATABASE_PATH = DATA_DIR / "keywords.db"

# Common business jargon to filter out
FILTER_PHRASES = {
    # Generic business terms
    'fiscal year', 'going forward', 'shareholder value', 'quarterly results',
    'year over year', 'quarter over quarter', 'revenue growth', 'profit margin',
    'operating income', 'net income', 'gross margin', 'free cash flow',
    'capital expenditure', 'balance sheet', 'income statement', 'cash flow',
    'earnings per share', 'market share', 'customer satisfaction', 'strategic priority',
    'core business', 'competitive advantage', 'value proposition', 'key driver',
    'organic growth', 'bottom line', 'top line', 'cost reduction',
    'operational efficiency', 'strong performance', 'challenging environment',
    'guidance range', 'full year', 'first quarter', 'second quarter',
    'third quarter', 'fourth quarter', 'year end', 'last year',
    'prior year', 'current quarter', 'next quarter', 'fiscal quarter',

    # Generic tech terms (too broad)
    'software development', 'data center', 'cloud computing', 'machine learning',
    'artificial intelligence', 'digital transformation',

    # Common filler phrases
    'thank you', 'good morning', 'good afternoon', 'good evening',
    'great question', 'next question', 'operator please',
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = DATA_DIR / "keyword_intelligence.log"
