"""Data collectors for various sources."""

from .hackernews import HackerNewsCollector
from .arxiv import ArxivCollector
from .github import GitHubCollector

__all__ = ["HackerNewsCollector", "ArxivCollector", "GitHubCollector"]
