"""arXiv paper collector using the arxiv API."""

import arxiv
from typing import List
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import ARXIV_PAPERS_PER_RUN, ARXIV_CATEGORIES


class ArxivCollector:
    """Collect paper titles and abstracts from arXiv."""
    
    def __init__(self):
        self.client = arxiv.Client()
    
    def collect(self) -> List[str]:
        """
        Collect text from recent CS papers.
        
        Returns:
            List of text strings (titles + abstracts)
        """
        texts = []
        papers_per_category = ARXIV_PAPERS_PER_RUN // len(ARXIV_CATEGORIES)
        
        print(f"Collecting papers from {len(ARXIV_CATEGORIES)} arXiv categories...")
        
        for category in ARXIV_CATEGORIES:
            category_texts = self._collect_category(category, papers_per_category)
            texts.extend(category_texts)
        
        print(f"Collected {len(texts)} text items from arXiv")
        return texts
    
    def _collect_category(self, category: str, max_results: int) -> List[str]:
        """Collect papers from a specific category."""
        texts = []
        
        try:
            # Search for recent papers in category
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            for paper in self.client.results(search):
                # Add title
                if paper.title:
                    texts.append(paper.title)
                
                # Add abstract
                if paper.summary:
                    texts.append(paper.summary)
            
            print(f"  {category}: {len(texts) // 2} papers")
            
        except Exception as e:
            print(f"Error collecting from {category}: {e}")
        
        return texts


def collect() -> List[str]:
    """Convenience function to collect from arXiv."""
    collector = ArxivCollector()
    return collector.collect()


if __name__ == "__main__":
    texts = collect()
    print(f"\nSample texts:")
    for text in texts[:5]:
        print(f"  - {text[:100]}...")
