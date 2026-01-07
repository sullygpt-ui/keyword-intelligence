"""
Y Combinator Companies Scraper

Scrapes YC company directory for startup terminology (Tier 2).
"""
import requests
import logging
import time
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)


class YCCompaniesScraper:
    """Scrapes Y Combinator company directory for startup keywords"""

    API_URL = "https://api.ycombinator.com/v0.1/companies"

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

    def fetch_recent_batches(self, batches: List[str] = None) -> List[Dict]:
        """
        Fetch companies from recent YC batches.

        Args:
            batches: List of batch codes like ['W24', 'S24', 'W23']
                    If None, fetches last 4 batches
        """
        if batches is None:
            # Default to recent batches
            current_year = datetime.now().year
            batches = [
                f'W{str(current_year)[-2:]}',  # Winter current year
                f'S{str(current_year - 1)[-2:]}',  # Summer last year
                f'W{str(current_year - 1)[-2:]}',  # Winter last year
                f'S{str(current_year - 2)[-2:]}',  # Summer 2 years ago
            ]

        all_companies = []

        for batch in batches:
            logger.info(f"Fetching YC batch {batch}...")
            companies = self._fetch_batch(batch)
            all_companies.extend(companies)
            time.sleep(0.5)  # Be polite

        logger.info(f"Total YC companies fetched: {len(all_companies)}")
        return all_companies

    def _fetch_batch(self, batch: str) -> List[Dict]:
        """Fetch companies from a specific batch using YC API"""
        companies = []

        try:
            response = requests.get(
                self.API_URL,
                params={'batch': batch},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            hits = data.get('companies', [])

            for hit in hits:
                company = {
                    'source_name': f"YC-{batch}",
                    'source_type': 'yc_batch',
                    'title': hit.get('name', ''),
                    'content': self._build_content(hit),
                    'url': hit.get('url', ''),
                    'published_date': datetime.now().strftime('%Y-%m-%d'),
                    'batch': batch,
                    'tags': hit.get('tags', []),
                }
                companies.append(company)

            logger.info(f"Fetched {len(companies)} companies from {batch}")

        except Exception as e:
            logger.error(f"Error fetching YC batch {batch}: {e}")

        return companies

    def _build_content(self, company: Dict) -> str:
        """Build searchable content from company data"""
        parts = []

        # Company name and one-liner
        if company.get('name'):
            parts.append(company['name'])
        if company.get('oneLiner'):
            parts.append(company['oneLiner'])

        # Long description
        if company.get('longDescription'):
            parts.append(company['longDescription'])

        # Tags (important for keyword extraction)
        tags = company.get('tags', [])
        if tags:
            parts.append(' '.join(tags))

        return ' '.join(parts)

    def get_new_companies(self, db, companies: List[Dict]) -> List[Dict]:
        """Filter out already processed companies"""
        new_companies = []
        for company in companies:
            identifier = company.get('url', '')
            if identifier and not db.is_source_processed('yc_batch', identifier):
                new_companies.append(company)
        return new_companies


def main():
    """Test YC scraper"""
    logging.basicConfig(level=logging.INFO)

    scraper = YCCompaniesScraper()

    # Test with recent batches
    companies = scraper.fetch_recent_batches(['W24', 'S24'])

    print(f"\nFetched {len(companies)} companies")

    for i, company in enumerate(companies[:10]):
        print(f"\n--- {i+1}. {company['title']} ---")
        print(f"Batch: {company['batch']}")
        print(f"Tags: {company.get('tags', [])}")
        print(f"Content preview: {company['content'][:200]}...")


if __name__ == "__main__":
    main()
