"""GitHub trending repositories collector."""

import requests
from bs4 import BeautifulSoup
from typing import List
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import GITHUB_REPOS_PER_RUN


class GitHubCollector:
    """Collect trending repository info from GitHub."""
    
    TRENDING_URL = "https://github.com/trending"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
    
    def collect(self) -> List[str]:
        """
        Collect text from trending repositories.
        
        Returns:
            List of text strings (repo names + descriptions)
        """
        texts = []
        
        # Collect from different time ranges
        for period in ["daily", "weekly"]:
            period_texts = self._collect_trending(period)
            texts.extend(period_texts)
        
        # Collect from specific languages
        for language in ["python", "javascript", "typescript", "rust", "go"]:
            lang_texts = self._collect_trending("daily", language)
            texts.extend(lang_texts)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_texts = []
        for text in texts:
            if text not in seen:
                seen.add(text)
                unique_texts.append(text)
        
        print(f"Collected {len(unique_texts)} text items from GitHub Trending")
        return unique_texts[:GITHUB_REPOS_PER_RUN * 2]  # name + description per repo
    
    def _collect_trending(self, since: str = "daily", language: str = None) -> List[str]:
        """Collect trending repos for a time period and optional language."""
        texts = []
        
        url = self.TRENDING_URL
        if language:
            url = f"{url}/{language}"
        
        params = {"since": since}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # Find repository articles
            articles = soup.find_all("article", class_="Box-row")
            
            for article in articles:
                # Get repo name
                name_elem = article.find("h2")
                if name_elem:
                    repo_name = name_elem.get_text(strip=True).replace(" ", "").replace("\n", "")
                    # Just the repo name without owner
                    if "/" in repo_name:
                        repo_name = repo_name.split("/")[-1]
                    texts.append(repo_name)
                
                # Get description
                desc_elem = article.find("p")
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    if description:
                        texts.append(description)
                
                # Get topics/tags if present
                topic_tags = article.find_all("a", class_="topic-tag")
                for tag in topic_tags:
                    topic = tag.get_text(strip=True)
                    if topic:
                        texts.append(topic)
            
            print(f"  GitHub {since}{f' ({language})' if language else ''}: {len(articles)} repos")
            
        except Exception as e:
            print(f"Error collecting GitHub trending: {e}")
        
        return texts


def collect() -> List[str]:
    """Convenience function to collect from GitHub."""
    collector = GitHubCollector()
    return collector.collect()


if __name__ == "__main__":
    texts = collect()
    print(f"\nSample texts:")
    for text in texts[:10]:
        print(f"  - {text[:100]}...")
