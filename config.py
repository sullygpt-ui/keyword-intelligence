"""Configuration settings for keyword intelligence."""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Database
DATABASE_PATH = DATA_DIR / "keywords.db"

# Collection settings
HACKERNEWS_STORIES_PER_RUN = 100  # Top/new stories to fetch
ARXIV_PAPERS_PER_RUN = 100       # Papers to fetch per category
GITHUB_REPOS_PER_RUN = 50        # Trending repos to fetch

# arXiv categories to track (CS and related)
ARXIV_CATEGORIES = [
    "cs.AI",   # Artificial Intelligence
    "cs.LG",   # Machine Learning
    "cs.CL",   # Computation and Language (NLP)
    "cs.CV",   # Computer Vision
    "cs.CR",   # Cryptography and Security
    "cs.DC",   # Distributed Computing
    "cs.SE",   # Software Engineering
]

# Term extraction settings
MIN_TERM_LENGTH = 3
MAX_TERM_LENGTH = 50
MIN_TERM_FREQUENCY = 2  # Minimum times a term must appear to be stored

# Terms to ignore (common words that aren't useful signals)
STOP_TERMS = {
    # Generic tech words (too common)
    "software", "hardware", "computer", "system", "systems", "application",
    "applications", "technology", "technologies", "platform", "platforms",
    "solution", "solutions", "service", "services", "tool", "tools",
    "data", "database", "server", "servers", "code", "coding",
    "developer", "developers", "engineering", "engineer", "engineers",
    "programming", "program", "programs", "project", "projects",
    
    # Generic business words
    "company", "companies", "business", "startup", "startups",
    "product", "products", "market", "markets", "customer", "customers",
    "user", "users", "team", "teams", "work", "working",
    
    # Common verbs/adjectives
    "using", "based", "new", "better", "best", "good", "great",
    "simple", "easy", "fast", "open", "source", "free",
    "really", "actually", "probably", "pretty", "much", "many",
    "thing", "things", "something", "anything", "everything",
    "way", "ways", "point", "points", "part", "parts",
    "lot", "lots", "bit", "kind", "sort", "type",
    "people", "person", "world", "life", "right", "wrong",
    "same", "different", "other", "another", "most", "more",
    "less", "few", "some", "any", "all", "every", "each",
    "want", "need", "like", "know", "think", "make", "take",
    "get", "got", "going", "come", "coming", "look", "looking",
    "try", "trying", "use", "used", "find", "found", "give",
    
    # Time-related
    "year", "years", "month", "months", "day", "days", "today",
    "week", "weeks", "time", "first", "last", "next", "now",
    "ago", "since", "still", "always", "never", "often",
    
    # Web/HTML cruft
    "quot", "href", "http", "https", "www", "com", "org", "net",
    "html", "rel", "nofollow", "amp", "x27", "x2f", "gt", "lt",
    
    # Common pronouns/articles (spaCy should catch but just in case)
    "the", "that", "this", "these", "those", "what", "which",
    "who", "whom", "whose", "where", "when", "why", "how",
    "been", "being", "have", "has", "had", "having",
    "does", "did", "doing", "done", "would", "could", "should",
    "will", "shall", "might", "must", "can", "may",
    "with", "from", "they", "their", "them", "there", "here",
    "just", "only", "also", "even", "about", "into", "over",
    "such", "than", "very", "well", "back", "down", "away",
}

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
