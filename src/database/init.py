"""Database initialization and connection management."""

import sqlite3
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Sources table - where data comes from
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Terms table - unique terms we're tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT UNIQUE NOT NULL,
            first_seen DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Term occurrences - count of term by source by date
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS term_occurrences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            date DATE NOT NULL,
            count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (term_id) REFERENCES terms(id),
            FOREIGN KEY (source_id) REFERENCES sources(id),
            UNIQUE(term_id, source_id, date)
        )
    """)
    
    # Collection runs - track when we collected data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collection_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            date DATE NOT NULL,
            items_collected INTEGER DEFAULT 0,
            terms_extracted INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources(id)
        )
    """)
    
    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_terms_term ON terms(term)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_occurrences_date ON term_occurrences(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_occurrences_term ON term_occurrences(term_id)")
    
    # Insert default sources
    sources = [
        ("hackernews", "Hacker News - Tech community discussions"),
        ("arxiv", "arXiv - Academic CS/AI papers"),
        ("github", "GitHub Trending - Popular repositories"),
    ]
    
    for name, description in sources:
        cursor.execute(
            "INSERT OR IGNORE INTO sources (name, description) VALUES (?, ?)",
            (name, description)
        )
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DATABASE_PATH}")


if __name__ == "__main__":
    init_database()
