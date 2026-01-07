"""
Financial Modeling Prep (FMP) Earnings Transcript Scraper

Fetches Fortune 500 earnings call transcripts for mainstream business term tracking.
"""
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from config import FMP_API_KEY, ALL_COMPANIES, FMP_RATE_LIMIT_SECONDS, FMP_DAILY_LIMIT

logger = logging.getLogger(__name__)


class FMPEarningsScraper:
    """Fetches earnings call transcripts from Financial Modeling Prep API"""

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or FMP_API_KEY
        if not self.api_key:
            raise ValueError("FMP API key required. Set FMP_API_KEY environment variable.")
        self.daily_calls = 0
        self.companies = ALL_COMPANIES

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make a rate-limited API request"""
        if self.daily_calls >= FMP_DAILY_LIMIT:
            logger.warning("Daily API limit reached")
            return None

        if params is None:
            params = {}
        params['apikey'] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=30)
            self.daily_calls += 1

            if response.status_code == 429:
                logger.warning("Rate limit hit, waiting...")
                time.sleep(60)
                return self._make_request(endpoint, params)

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None

    def get_transcript(self, ticker: str, year: int, quarter: int) -> Optional[Dict]:
        """Get a single earnings transcript"""
        endpoint = f"earning_call_transcript/{ticker}"
        params = {'year': year, 'quarter': quarter}

        data = self._make_request(endpoint, params)

        if data and len(data) > 0:
            transcript = data[0]
            return {
                'source_name': ticker,
                'source_type': 'earnings_call',
                'title': f"{ticker} Q{quarter} {year} Earnings Call",
                'content': transcript.get('content', ''),
                'date': transcript.get('date', ''),
                'quarter': quarter,
                'year': year,
                'url': f"https://financialmodelingprep.com/earnings-call-transcript/{ticker}",
            }

        return None

    def get_latest_transcripts(self, ticker: str, limit: int = 1) -> List[Dict]:
        """Get the most recent transcripts for a ticker"""
        endpoint = f"earning_call_transcript/{ticker}"

        data = self._make_request(endpoint)
        transcripts = []

        if data:
            for transcript in data[:limit]:
                transcripts.append({
                    'source_name': ticker,
                    'source_type': 'earnings_call',
                    'title': f"{ticker} Earnings Call",
                    'content': transcript.get('content', ''),
                    'date': transcript.get('date', ''),
                    'quarter': transcript.get('quarter'),
                    'year': transcript.get('year'),
                    'url': f"https://financialmodelingprep.com/earnings-call-transcript/{ticker}",
                })

        return transcripts

    def get_recent_transcripts_for_companies(
        self,
        companies: List[str] = None,
        days_back: int = 90
    ) -> List[Dict]:
        """Fetch recent transcripts for a list of companies"""
        companies = companies or self.companies
        all_transcripts = []
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        for i, ticker in enumerate(companies):
            if self.daily_calls >= FMP_DAILY_LIMIT:
                logger.warning(f"Daily limit reached after {i} companies")
                break

            logger.info(f"Fetching transcripts for {ticker} ({i+1}/{len(companies)})")

            transcripts = self.get_latest_transcripts(ticker, limit=1)

            for transcript in transcripts:
                if transcript['date'] and transcript['date'] >= cutoff_date:
                    all_transcripts.append(transcript)

            # Rate limiting
            time.sleep(FMP_RATE_LIMIT_SECONDS)

        logger.info(f"Fetched {len(all_transcripts)} transcripts")
        return all_transcripts

    def extract_qa_section(self, content: str) -> str:
        """Extract Q&A section from transcript (where buzzwords often appear)"""
        if not content:
            return ""

        # Common markers for Q&A section
        qa_markers = [
            "question-and-answer session",
            "q&a session",
            "questions and answers",
            "operator:",
            "our first question",
            "we'll now begin the question",
        ]

        content_lower = content.lower()
        qa_start = len(content)

        for marker in qa_markers:
            pos = content_lower.find(marker)
            if pos != -1 and pos < qa_start:
                qa_start = pos

        if qa_start < len(content):
            return content[qa_start:]

        # If no Q&A marker found, return last 60% of content (Q&A is usually at end)
        return content[int(len(content) * 0.4):]

    def get_new_transcripts(self, db, transcripts: List[Dict]) -> List[Dict]:
        """Filter out already processed transcripts"""
        new_transcripts = []
        for transcript in transcripts:
            identifier = f"{transcript['source_name']}-{transcript.get('year', '')}-Q{transcript.get('quarter', '')}"
            if not db.is_source_processed('earnings_call', identifier):
                new_transcripts.append(transcript)
        return new_transcripts


def main():
    """Test the scraper"""
    import os
    logging.basicConfig(level=logging.INFO)

    if not os.getenv("FMP_API_KEY"):
        print("Set FMP_API_KEY environment variable to test")
        return

    scraper = FMPEarningsScraper()

    # Test with a few companies
    test_companies = ['AAPL', 'MSFT', 'GOOGL']
    transcripts = scraper.get_recent_transcripts_for_companies(test_companies)

    print(f"\nFetched {len(transcripts)} transcripts")
    for t in transcripts:
        print(f"\n--- {t['source_name']} ---")
        print(f"Title: {t['title']}")
        print(f"Date: {t['date']}")
        print(f"Content preview: {t['content'][:300]}...")


if __name__ == "__main__":
    main()
