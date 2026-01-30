"""Main collection script - run this to collect from all sources."""

import argparse
from datetime import date
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors import HackerNewsCollector, ArxivCollector, GitHubCollector
from src.processing import TermExtractor
from src.database import init_database, store_terms
from src.database.queries import log_collection_run


def collect_source(source_name: str, collector, extractor: TermExtractor):
    """Collect and process data from a single source."""
    print(f"\n{'='*50}")
    print(f"Collecting from: {source_name}")
    print('='*50)
    
    # Collect raw texts
    texts = collector.collect()
    
    if not texts:
        print(f"No texts collected from {source_name}")
        return
    
    # Extract terms
    print(f"Extracting terms from {len(texts)} texts...")
    terms = extractor.extract_terms(texts)
    
    print(f"Found {len(terms)} unique terms")
    
    # Store in database
    stored = store_terms(source_name, terms)
    print(f"Stored {stored} terms in database")
    
    # Log the run
    log_collection_run(source_name, len(texts), len(terms))
    
    # Show top terms
    top_terms = sorted(terms.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"\nTop terms from {source_name}:")
    for term, count in top_terms:
        print(f"  {count:3d} | {term}")


def main():
    parser = argparse.ArgumentParser(description="Collect keyword data from sources")
    parser.add_argument(
        "--source", "-s",
        choices=["hackernews", "arxiv", "github", "all"],
        default="all",
        help="Which source to collect from (default: all)"
    )
    args = parser.parse_args()
    
    # Initialize database
    init_database()
    
    # Initialize extractor (shared across sources)
    extractor = TermExtractor()
    
    # Define collectors
    collectors = {
        "hackernews": HackerNewsCollector(),
        "arxiv": ArxivCollector(),
        "github": GitHubCollector(),
    }
    
    # Collect from selected sources
    if args.source == "all":
        sources_to_collect = collectors.keys()
    else:
        sources_to_collect = [args.source]
    
    for source_name in sources_to_collect:
        collector = collectors[source_name]
        collect_source(source_name, collector, extractor)
    
    print(f"\n{'='*50}")
    print("Collection complete!")
    print(f"Date: {date.today()}")
    print('='*50)


if __name__ == "__main__":
    main()
