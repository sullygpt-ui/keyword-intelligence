"""
SQLite database schema and operations for Keyword Intelligence System
"""
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Keywords table
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY,
                    term TEXT UNIQUE NOT NULL,
                    normalized_term TEXT,
                    first_seen DATE,
                    last_updated DATE
                );

                -- Mentions table (one row per mention)
                CREATE TABLE IF NOT EXISTS mentions (
                    id INTEGER PRIMARY KEY,
                    keyword_id INTEGER,
                    source_type TEXT,  -- 'vc_blog', 'yc_batch', 'earnings_call'
                    source_name TEXT,  -- e.g., 'a16z', 'AAPL', 'YC-W24'
                    mention_date DATE,
                    context TEXT,      -- Surrounding text snippet
                    url TEXT,          -- Link to source
                    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
                );

                -- Weekly scores (for trend tracking)
                CREATE TABLE IF NOT EXISTS weekly_scores (
                    id INTEGER PRIMARY KEY,
                    keyword_id INTEGER,
                    week_start DATE,
                    tier1_mentions INTEGER DEFAULT 0,
                    tier3_mentions INTEGER DEFAULT 0,
                    yc_mentions INTEGER DEFAULT 0,
                    score FLOAT,
                    FOREIGN KEY (keyword_id) REFERENCES keywords(id),
                    UNIQUE(keyword_id, week_start)
                );

                -- Processed sources (to avoid re-processing)
                CREATE TABLE IF NOT EXISTS processed_sources (
                    id INTEGER PRIMARY KEY,
                    source_type TEXT,
                    source_identifier TEXT,  -- URL or transcript ID
                    processed_date DATE,
                    UNIQUE(source_type, source_identifier)
                );

                -- Create indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_mentions_keyword ON mentions(keyword_id);
                CREATE INDEX IF NOT EXISTS idx_mentions_source ON mentions(source_type, source_name);
                CREATE INDEX IF NOT EXISTS idx_mentions_date ON mentions(mention_date);
                CREATE INDEX IF NOT EXISTS idx_weekly_scores_week ON weekly_scores(week_start);
            """)
            conn.commit()

    def get_or_create_keyword(self, term: str, normalized_term: Optional[str] = None) -> int:
        """Get existing keyword ID or create new one"""
        today = date.today().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM keywords WHERE term = ?",
                (term,)
            )
            row = cursor.fetchone()
            if row:
                conn.execute(
                    "UPDATE keywords SET last_updated = ? WHERE id = ?",
                    (today, row['id'])
                )
                conn.commit()
                return row['id']

            cursor = conn.execute(
                """INSERT INTO keywords (term, normalized_term, first_seen, last_updated)
                   VALUES (?, ?, ?, ?)""",
                (term, normalized_term or term.lower(), today, today)
            )
            conn.commit()
            return cursor.lastrowid

    def add_mention(
        self,
        keyword_id: int,
        source_type: str,
        source_name: str,
        mention_date: str,
        context: str,
        url: Optional[str] = None
    ):
        """Add a keyword mention"""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO mentions
                   (keyword_id, source_type, source_name, mention_date, context, url)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (keyword_id, source_type, source_name, mention_date, context, url)
            )
            conn.commit()

    def is_source_processed(self, source_type: str, source_identifier: str) -> bool:
        """Check if a source has already been processed"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT 1 FROM processed_sources
                   WHERE source_type = ? AND source_identifier = ?""",
                (source_type, source_identifier)
            )
            return cursor.fetchone() is not None

    def mark_source_processed(self, source_type: str, source_identifier: str):
        """Mark a source as processed"""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO processed_sources
                   (source_type, source_identifier, processed_date)
                   VALUES (?, ?, ?)""",
                (source_type, source_identifier, date.today().isoformat())
            )
            conn.commit()

    def get_keyword_mentions(
        self,
        keyword_id: int,
        source_type: Optional[str] = None,
        since_date: Optional[str] = None
    ) -> List[Dict]:
        """Get mentions for a keyword"""
        query = "SELECT * FROM mentions WHERE keyword_id = ?"
        params = [keyword_id]

        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)

        if since_date:
            query += " AND mention_date >= ?"
            params.append(since_date)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_weekly_stats(self, week_start: str) -> List[Dict]:
        """Get all keyword stats for a specific week"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT k.term, k.first_seen, ws.*
                   FROM weekly_scores ws
                   JOIN keywords k ON k.id = ws.keyword_id
                   WHERE ws.week_start = ?
                   ORDER BY ws.score DESC""",
                (week_start,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def save_weekly_score(
        self,
        keyword_id: int,
        week_start: str,
        tier1_mentions: int,
        tier3_mentions: int,
        yc_mentions: int,
        score: float
    ):
        """Save or update weekly score for a keyword"""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO weekly_scores
                   (keyword_id, week_start, tier1_mentions, tier3_mentions, yc_mentions, score)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(keyword_id, week_start) DO UPDATE SET
                   tier1_mentions = excluded.tier1_mentions,
                   tier3_mentions = excluded.tier3_mentions,
                   yc_mentions = excluded.yc_mentions,
                   score = excluded.score""",
                (keyword_id, week_start, tier1_mentions, tier3_mentions, yc_mentions, score)
            )
            conn.commit()

    def get_all_keywords_with_stats(self, since_date: Optional[str] = None) -> List[Dict]:
        """Get all keywords with their mention counts by source type"""
        query = """
            SELECT
                k.id,
                k.term,
                k.normalized_term,
                k.first_seen,
                k.last_updated,
                COUNT(CASE WHEN m.source_type = 'vc_blog' THEN 1 END) as vc_mentions,
                COUNT(CASE WHEN m.source_type = 'yc_batch' THEN 1 END) as yc_mentions,
                COUNT(CASE WHEN m.source_type IN ('earnings_call', 'sec_filing', 'financial_news') THEN 1 END) as earnings_mentions,
                COUNT(*) as total_mentions
            FROM keywords k
            LEFT JOIN mentions m ON k.id = m.keyword_id
        """
        params = []

        if since_date:
            query += " WHERE m.mention_date >= ?"
            params.append(since_date)

        query += " GROUP BY k.id ORDER BY total_mentions DESC"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_keyword_sources(self, keyword_id: int) -> Dict[str, List[str]]:
        """Get unique sources that mentioned a keyword"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT DISTINCT source_type, source_name, url
                   FROM mentions WHERE keyword_id = ?
                   ORDER BY source_type, source_name""",
                (keyword_id,)
            )
            sources = {'vc_blog': [], 'yc_batch': [], 'earnings_call': [], 'sec_filing': [], 'financial_news': []}
            urls = []
            for row in cursor.fetchall():
                source_type = row['source_type']
                # Combine sec_filing and financial_news into earnings_call for scoring purposes
                if source_type in ('sec_filing', 'financial_news'):
                    if row['source_name'] not in sources.get('earnings_call', []):
                        sources['earnings_call'].append(row['source_name'])
                elif row['source_name'] not in sources.get(source_type, []):
                    sources.setdefault(source_type, []).append(row['source_name'])
                if row['url']:
                    urls.append(row['url'])
            sources['urls'] = list(set(urls))
            return sources

    def get_previous_week_score(self, keyword_id: int, current_week: str) -> Optional[float]:
        """Get the score from the previous week for trend calculation"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT score FROM weekly_scores
                   WHERE keyword_id = ? AND week_start < ?
                   ORDER BY week_start DESC LIMIT 1""",
                (keyword_id, current_week)
            )
            row = cursor.fetchone()
            return row['score'] if row else None
