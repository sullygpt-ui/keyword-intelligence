#!/usr/bin/env python3
"""
Keyword Intelligence System - Main Orchestration Script

Runs the complete keyword analysis pipeline:
1. Scrape VC blogs for emerging terms (Tier 1)
2. Scrape YC company directory for startup terminology (Tier 2)
3. Scrape financial news for corporate terminology (Tier 3)
4. Extract and normalize keywords
5. Score and rank keywords
6. Generate reports

Usage:
    python main.py                    # Run full pipeline (VC + YC + financial news)
    python main.py --vc-only          # Only scrape VC blogs
    python main.py --yc-only          # Only scrape YC companies
    python main.py --news-only        # Only scrape financial news
    python main.py --sec-only         # Only fetch SEC filings (disabled by default)
    python main.py --earnings-only    # Only fetch FMP earnings (requires paid API)
    python main.py --report-only      # Only generate reports (use existing data)
    python main.py --no-yc            # Skip YC scraping
    python main.py --no-news          # Skip financial news scraping
"""
import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_PATH, LOG_FILE, LOG_LEVEL, DATA_DIR
from database.models import Database
from scrapers.vc_blogs import VCBlogScraper
from scrapers.fmp_earnings import FMPEarningsScraper
from scrapers.sec_edgar import SECEdgarScraper
from scrapers.financial_news import FinancialNewsScraper
from scrapers.yc_companies import YCCompaniesScraper
from processing.keyword_extraction import KeywordExtractor
from processing.scoring import KeywordScorer
from output.report_generator import ReportGenerator

# Setup logging
def setup_logging():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger(__name__)


def get_week_start() -> str:
    """Get the Monday of the current week as YYYY-MM-DD"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime('%Y-%m-%d')


def process_posts(db: Database, extractor: KeywordExtractor, posts: list, source_type: str):
    """Extract keywords from posts and store in database"""
    for post in posts:
        # Combine title and content for extraction
        text = f"{post.get('title', '')} {post.get('content', '')}"
        keywords = extractor.extract_keywords(text)

        source_name = post.get('source_name', 'unknown')
        mention_date = post.get('published_date') or post.get('date') or datetime.now().strftime('%Y-%m-%d')
        url = post.get('url', '')

        for keyword_term, count in keywords:
            if count < 1:
                continue

            # Get or create keyword
            keyword_id = db.get_or_create_keyword(keyword_term)

            # Get context snippet
            context = text[:500] if text else ''

            # Add mention
            db.add_mention(
                keyword_id=keyword_id,
                source_type=source_type,
                source_name=source_name,
                mention_date=mention_date,
                context=context,
                url=url
            )

        # Mark source as processed
        identifier = url if source_type == 'vc_blog' else f"{source_name}-{post.get('year', '')}-Q{post.get('quarter', '')}"
        db.mark_source_processed(source_type, identifier)


def run_vc_scraping(db: Database, extractor: KeywordExtractor) -> int:
    """Scrape VC blogs and process keywords"""
    logger.info("Starting VC blog scraping...")

    scraper = VCBlogScraper()
    posts = scraper.fetch_all_feeds()

    # Filter out already processed
    new_posts = scraper.get_new_posts(db, posts)
    logger.info(f"Found {len(new_posts)} new posts to process")

    if new_posts:
        process_posts(db, extractor, new_posts, 'vc_blog')

    return len(new_posts)


def run_earnings_scraping(db: Database, extractor: KeywordExtractor) -> int:
    """Fetch earnings transcripts and process keywords"""
    logger.info("Starting earnings transcript fetching...")

    try:
        scraper = FMPEarningsScraper()
    except ValueError as e:
        logger.warning(f"FMP scraping skipped: {e}")
        return 0

    transcripts = scraper.get_recent_transcripts_for_companies(days_back=90)

    # Filter out already processed
    new_transcripts = scraper.get_new_transcripts(db, transcripts)
    logger.info(f"Found {len(new_transcripts)} new transcripts to process")

    if new_transcripts:
        # Extract Q&A section for better keyword extraction
        for t in new_transcripts:
            t['content'] = scraper.extract_qa_section(t['content'])

        process_posts(db, extractor, new_transcripts, 'earnings_call')

    return len(new_transcripts)


def run_sec_scraping(db: Database, extractor: KeywordExtractor) -> int:
    """Fetch SEC filings and process keywords (free alternative to FMP)"""
    logger.info("Starting SEC EDGAR filing fetch...")

    scraper = SECEdgarScraper()

    # Get 10-K and 10-Q filings from top companies
    filings = scraper.get_company_filings_with_content(
        tickers=None,  # Uses default list from config
        filing_types=['10-K', '10-Q'],
        limit_per_company=1,
        delay=0.5
    )

    # Filter out already processed
    new_filings = scraper.get_new_filings(db, filings)
    logger.info(f"Found {len(new_filings)} new SEC filings to process")

    if new_filings:
        process_posts(db, extractor, new_filings, 'sec_filing')

    return len(new_filings)


def run_yc_scraping(db: Database, extractor: KeywordExtractor) -> int:
    """Fetch YC company data and process keywords (Tier 2 source)"""
    logger.info("Starting YC batch scraping...")

    scraper = YCCompaniesScraper()

    # Fetch from recent batches (last 4 by default)
    companies = scraper.fetch_recent_batches()

    # Filter out already processed
    new_companies = scraper.get_new_companies(db, companies)
    logger.info(f"Found {len(new_companies)} new YC companies to process")

    if new_companies:
        process_posts(db, extractor, new_companies, 'yc_batch')

    return len(new_companies)


def run_financial_news_scraping(db: Database, extractor: KeywordExtractor) -> int:
    """Fetch financial news articles and process keywords (free Tier 3 source)"""
    logger.info("Starting financial news scraping...")

    scraper = FinancialNewsScraper()

    # Fetch from general financial news feeds
    articles = scraper.fetch_all_feeds()

    # Also fetch company-specific news for top companies
    company_articles = scraper.fetch_company_news(limit=15)
    articles.extend(company_articles)

    # Filter out already processed
    new_articles = scraper.get_new_articles(db, articles)
    logger.info(f"Found {len(new_articles)} new financial news articles to process")

    if new_articles:
        process_posts(db, extractor, new_articles, 'financial_news')

    return len(new_articles)


def run_scoring(db: Database) -> dict:
    """Score all keywords and categorize by tier"""
    logger.info("Scoring keywords...")

    week_start = get_week_start()
    scorer = KeywordScorer(db)

    # Calculate scores for all keywords
    all_scores = scorer.score_all_keywords(week_start)
    logger.info(f"Scored {len(all_scores)} keywords")

    # Categorize by tier
    tiered = scorer.get_tier_keywords(all_scores)

    logger.info(f"Emerging: {len(tiered['emerging'])}, Validated: {len(tiered['validated'])}, Mainstream: {len(tiered['mainstream'])}")

    return tiered


def run_report_generation(tiered_keywords: dict) -> dict:
    """Generate all report formats"""
    logger.info("Generating reports...")

    generator = ReportGenerator()
    report_date = datetime.now().strftime('%Y-%m-%d')

    paths = generator.generate_all(tiered_keywords, report_date)

    for format_name, path in paths.items():
        logger.info(f"Generated {format_name}: {path}")

    return paths


def main():
    parser = argparse.ArgumentParser(description='Keyword Intelligence System')
    parser.add_argument('--vc-only', action='store_true', help='Only scrape VC blogs')
    parser.add_argument('--yc-only', action='store_true', help='Only scrape YC companies')
    parser.add_argument('--news-only', action='store_true', help='Only scrape financial news')
    parser.add_argument('--sec-only', action='store_true', help='Only fetch SEC filings')
    parser.add_argument('--earnings-only', action='store_true', help='Only fetch FMP earnings (requires paid API)')
    parser.add_argument('--report-only', action='store_true', help='Only generate reports')
    parser.add_argument('--no-yc', action='store_true', help='Skip YC company scraping')
    parser.add_argument('--no-news', action='store_true', help='Skip financial news scraping')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    setup_logging()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Keyword Intelligence System Starting")
    logger.info("=" * 60)

    # Initialize components
    db = Database(DATABASE_PATH)
    extractor = KeywordExtractor()

    stats = {
        'vc_posts': 0,
        'yc_companies': 0,
        'financial_news': 0,
        'sec_filings': 0,
        'earnings_transcripts': 0,
        'reports': {}
    }

    try:
        # Run appropriate pipelines
        if not args.report_only:
            # Check if running a specific-only mode
            specific_only = args.vc_only or args.yc_only or args.news_only or args.sec_only or args.earnings_only

            # VC Blogs (Tier 1)
            if args.vc_only or not specific_only:
                stats['vc_posts'] = run_vc_scraping(db, extractor)

            # YC Companies (Tier 2)
            if args.yc_only or (not specific_only and not args.no_yc):
                stats['yc_companies'] = run_yc_scraping(db, extractor)

            # Financial News (Tier 3 - free, runs by default)
            if args.news_only or (not specific_only and not args.no_news):
                stats['financial_news'] = run_financial_news_scraping(db, extractor)

            # SEC Filings (Tier 3 - free alternative)
            # Note: SEC has strict bot protections, disabled by default
            # Enable with --sec-only flag when needed
            if args.sec_only:
                stats['sec_filings'] = run_sec_scraping(db, extractor)

            # FMP Earnings (Tier 3 - requires paid API)
            if args.earnings_only:
                stats['earnings_transcripts'] = run_earnings_scraping(db, extractor)

        # Always score and generate reports
        tiered_keywords = run_scoring(db)
        stats['reports'] = run_report_generation(tiered_keywords)

        # Summary
        logger.info("=" * 60)
        logger.info("Pipeline Complete!")
        logger.info(f"  VC Posts Processed: {stats['vc_posts']}")
        logger.info(f"  YC Companies Processed: {stats['yc_companies']}")
        logger.info(f"  Financial News Processed: {stats['financial_news']}")
        logger.info(f"  SEC Filings Processed: {stats['sec_filings']}")
        logger.info(f"  Earnings Transcripts Processed: {stats['earnings_transcripts']}")
        logger.info(f"  Reports Generated: {len(stats['reports'])}")
        logger.info("=" * 60)

        # Print report locations
        print("\n📊 Reports generated:")
        for format_name, path in stats['reports'].items():
            print(f"   {format_name}: {path}")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
