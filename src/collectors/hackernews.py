"""Hacker News collector using the official API."""

import requests
from typing import List, Dict
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import HACKERNEWS_STORIES_PER_RUN


class HackerNewsCollector:
    """Collect stories and comments from Hacker News."""
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self):
        self.session = requests.Session()
    
    def collect(self) -> List[str]:
        """
        Collect text from top and new stories.
        
        Returns:
            List of text strings (titles + comment snippets)
        """
        texts = []
        
        # Get top stories
        top_ids = self._get_story_ids("topstories")[:HACKERNEWS_STORIES_PER_RUN // 2]
        
        # Get new stories  
        new_ids = self._get_story_ids("newstories")[:HACKERNEWS_STORIES_PER_RUN // 2]
        
        all_ids = list(set(top_ids + new_ids))
        
        print(f"Collecting {len(all_ids)} HN stories...")
        
        for story_id in all_ids:
            story = self._get_item(story_id)
            if story:
                # Add title
                if story.get("title"):
                    texts.append(story["title"])
                
                # Add text if it's an Ask HN or Show HN
                if story.get("text"):
                    texts.append(story["text"])
                
                # Get top comments for more context
                if story.get("kids"):
                    for comment_id in story["kids"][:3]:  # Top 3 comments
                        comment = self._get_item(comment_id)
                        if comment and comment.get("text"):
                            texts.append(comment["text"])
        
        print(f"Collected {len(texts)} text items from Hacker News")
        return texts
    
    def _get_story_ids(self, endpoint: str) -> List[int]:
        """Get story IDs from an endpoint (topstories, newstories, etc.)."""
        try:
            response = self.session.get(f"{self.BASE_URL}/{endpoint}.json")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {endpoint}: {e}")
            return []
    
    def _get_item(self, item_id: int) -> Dict:
        """Get a single item (story or comment) by ID."""
        try:
            response = self.session.get(f"{self.BASE_URL}/item/{item_id}.json")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching item {item_id}: {e}")
            return {}


def collect() -> List[str]:
    """Convenience function to collect from Hacker News."""
    collector = HackerNewsCollector()
    return collector.collect()


if __name__ == "__main__":
    texts = collect()
    print(f"\nSample texts:")
    for text in texts[:5]:
        print(f"  - {text[:100]}...")
