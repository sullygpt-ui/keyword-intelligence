"""
SEC EDGAR Filings Scraper

Free alternative to FMP for Fortune 500 business terminology.
Scrapes 10-K and 10-Q filings for MD&A sections.
"""
import requests
import time
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from config import ALL_COMPANIES

logger = logging.getLogger(__name__)


# Company ticker to CIK mapping (SEC uses CIK numbers)
# This is a subset - will fetch dynamically for others
TICKER_TO_CIK = {
    'AAPL': '0000320193',
    'MSFT': '0000789019',
    'GOOGL': '0001652044',
    'AMZN': '0001018724',
    'META': '0001326801',
    'NVDA': '0001045810',
    'TSLA': '0001318605',
    'WMT': '0000104169',
    'JPM': '0000019617',
    'JNJ': '0000200406',
    'UNH': '0000731766',
    'PG': '0000080424',
    'HD': '0000354950',
    'BAC': '0000070858',
    'PFE': '0000078003',
}


class SECEdgarScraper:
    """Scrapes SEC EDGAR for company filings"""

    BASE_URL = "https://www.sec.gov"
    EDGAR_API = "https://data.sec.gov"

    def __init__(self):
        self.headers = {
            'User-Agent': 'KeywordIntelligence mike@sullysblog.com',
            'Accept-Encoding': 'gzip, deflate',
        }
        self.cik_cache = TICKER_TO_CIK.copy()

    def get_cik(self, ticker: str) -> Optional[str]:
        """Get CIK for a ticker symbol"""
        if ticker in self.cik_cache:
            return self.cik_cache[ticker]

        # Load SEC's full company tickers list (cached)
        if not hasattr(self, '_ticker_map'):
            try:
                url = f"{self.EDGAR_API}/files/company_tickers.json"
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                # Build ticker to CIK map
                self._ticker_map = {}
                for entry in data.values():
                    t = entry.get('ticker', '').upper()
                    cik = str(entry.get('cik_str', '')).zfill(10)
                    self._ticker_map[t] = cik
                logger.info(f"Loaded {len(self._ticker_map)} tickers from SEC")
            except Exception as e:
                logger.error(f"Failed to load SEC ticker list: {e}")
                self._ticker_map = {}

        cik = self._ticker_map.get(ticker.upper())
        if cik:
            self.cik_cache[ticker] = cik
        return cik

    def get_recent_filings(self, ticker: str, filing_types: List[str] = None, limit: int = 5) -> List[Dict]:
        """Get recent filings for a company"""
        filing_types = filing_types or ['10-K', '10-Q']
        cik = self.get_cik(ticker)

        if not cik:
            logger.warning(f"No CIK found for {ticker}")
            return []

        filings = []
        try:
            # Get company submissions
            url = f"{self.EDGAR_API}/submissions/CIK{cik}.json"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            recent = data.get('filings', {}).get('recent', {})

            forms = recent.get('form', [])
            accessions = recent.get('accessionNumber', [])
            dates = recent.get('filingDate', [])

            count = 0
            for i, form in enumerate(forms):
                if count >= limit:
                    break
                if form in filing_types:
                    filings.append({
                        'ticker': ticker,
                        'cik': cik,
                        'form': form,
                        'accession': accessions[i],  # Keep dashes intact
                        'date': dates[i],
                    })
                    count += 1

        except Exception as e:
            logger.error(f"Error fetching filings for {ticker}: {e}")

        return filings

    def get_filing_content(self, filing: Dict) -> Optional[str]:
        """Extract text content from a filing"""
        try:
            cik = filing['cik'].lstrip('0')  # Remove leading zeros for URL
            accession = filing['accession']  # Has dashes like 0000320193-25-000079
            accession_folder = accession.replace('-', '')  # Remove dashes for folder path

            # List files in the filing folder
            folder_url = f"{self.BASE_URL}/Archives/edgar/data/{cik}/{accession_folder}/"
            logger.debug(f"Fetching filing folder: {folder_url}")

            response = requests.get(folder_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            # Parse the directory listing to find the main document
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find links to .htm files (the main filing document)
            main_doc = None
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Look for the main filing document (usually the largest .htm file, not R files)
                if href.endswith('.htm') and not href.startswith('R') and 'index' not in href.lower():
                    # Prefer files that look like the main document
                    if filing['form'].lower().replace('-', '') in href.lower() or 'aapl' in href.lower() or len(href) > 15:
                        main_doc = href
                        break
                    if not main_doc:
                        main_doc = href

            if not main_doc:
                # Fallback: look for any .htm
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '.htm' in href.lower() and 'index' not in href.lower():
                        main_doc = href
                        break

            if not main_doc:
                logger.warning(f"No main document found for {filing['ticker']}")
                return None

            # Fetch the document
            doc_url = f"{self.BASE_URL}/Archives/edgar/data/{cik}/{accession_folder}/{main_doc}"
            logger.debug(f"Fetching document: {doc_url}")
            doc_response = requests.get(doc_url, headers=self.headers, timeout=60)
            doc_response.raise_for_status()

            # Parse HTML and extract text
            soup = BeautifulSoup(doc_response.content, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'table']):
                element.decompose()

            text = soup.get_text(separator=' ')

            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)

            return text[:200000]  # Limit size

        except Exception as e:
            logger.error(f"Error fetching filing content: {e}")
            return None

    def extract_mda_section(self, text: str) -> str:
        """Extract Management Discussion & Analysis section"""
        if not text:
            return ""

        text_lower = text.lower()

        # Common MD&A section markers
        start_markers = [
            "management's discussion and analysis",
            "management discussion and analysis",
            "item 7. management",
            "item 7 management",
            "md&a",
        ]

        end_markers = [
            "item 8",
            "item 7a",
            "quantitative and qualitative disclosures",
            "financial statements and supplementary data",
        ]

        # Find start
        start_pos = len(text)
        for marker in start_markers:
            pos = text_lower.find(marker)
            if pos != -1 and pos < start_pos:
                start_pos = pos

        if start_pos == len(text):
            # No MD&A found, return a portion of the text
            return text[10000:50000] if len(text) > 50000 else text

        # Find end
        end_pos = len(text)
        search_start = start_pos + 1000  # Skip past the heading
        for marker in end_markers:
            pos = text_lower.find(marker, search_start)
            if pos != -1 and pos < end_pos:
                end_pos = pos

        return text[start_pos:end_pos]

    def get_company_filings_with_content(
        self,
        tickers: List[str] = None,
        filing_types: List[str] = None,
        limit_per_company: int = 1,
        delay: float = 0.5
    ) -> List[Dict]:
        """Get filings with extracted content for multiple companies"""
        tickers = tickers or ALL_COMPANIES[:20]  # Limit to 20 companies by default
        filing_types = filing_types or ['10-K', '10-Q']

        all_filings = []

        for i, ticker in enumerate(tickers):
            logger.info(f"Fetching SEC filings for {ticker} ({i+1}/{len(tickers)})")

            filings = self.get_recent_filings(ticker, filing_types, limit_per_company)

            for filing in filings:
                content = self.get_filing_content(filing)
                if content:
                    mda = self.extract_mda_section(content)
                    all_filings.append({
                        'source_name': ticker,
                        'source_type': 'sec_filing',
                        'title': f"{ticker} {filing['form']} Filing",
                        'content': mda,
                        'date': filing['date'],
                        'form': filing['form'],
                        'url': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={filing['cik']}&type={filing['form']}",
                    })

                time.sleep(delay)  # Be nice to SEC servers

            time.sleep(delay)

        logger.info(f"Fetched {len(all_filings)} SEC filings")
        return all_filings

    def get_new_filings(self, db, filings: List[Dict]) -> List[Dict]:
        """Filter out already processed filings"""
        new_filings = []
        for filing in filings:
            identifier = f"{filing['source_name']}-{filing['form']}-{filing['date']}"
            if not db.is_source_processed('sec_filing', identifier):
                new_filings.append(filing)
        return new_filings


def main():
    """Test SEC scraper"""
    logging.basicConfig(level=logging.INFO)

    scraper = SECEdgarScraper()

    # Test with a few companies
    test_tickers = ['AAPL', 'MSFT', 'NVDA']
    filings = scraper.get_company_filings_with_content(test_tickers, limit_per_company=1)

    print(f"\nFetched {len(filings)} filings")
    for f in filings:
        print(f"\n--- {f['source_name']} {f['form']} ---")
        print(f"Date: {f['date']}")
        print(f"Content length: {len(f['content'])} chars")
        print(f"Preview: {f['content'][:500]}...")


if __name__ == "__main__":
    main()
