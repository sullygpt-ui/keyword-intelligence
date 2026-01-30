"""Database query functions."""

import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional
from .init import get_connection


def get_source_id(conn: sqlite3.Connection, source_name: str) -> int:
    """Get source ID by name."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sources WHERE name = ?", (source_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    raise ValueError(f"Unknown source: {source_name}")


def store_terms(source_name: str, terms: Dict[str, int], collection_date: date = None):
    """
    Store extracted terms in the database.
    
    Args:
        source_name: Name of the source (hackernews, arxiv, github)
        terms: Dictionary of term -> count
        collection_date: Date of collection (defaults to today)
    """
    if collection_date is None:
        collection_date = date.today()
    
    conn = get_connection()
    cursor = conn.cursor()
    source_id = get_source_id(conn, source_name)
    
    terms_stored = 0
    for term, count in terms.items():
        # Insert or get term
        cursor.execute(
            "INSERT OR IGNORE INTO terms (term, first_seen) VALUES (?, ?)",
            (term.lower(), collection_date)
        )
        cursor.execute("SELECT id FROM terms WHERE term = ?", (term.lower(),))
        term_id = cursor.fetchone()[0]
        
        # Upsert occurrence count
        cursor.execute("""
            INSERT INTO term_occurrences (term_id, source_id, date, count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(term_id, source_id, date) 
            DO UPDATE SET count = count + excluded.count
        """, (term_id, source_id, collection_date, count))
        terms_stored += 1
    
    conn.commit()
    conn.close()
    return terms_stored


def get_term_history(term: str, days: int = 30) -> List[Dict]:
    """Get occurrence history for a specific term."""
    conn = get_connection()
    cursor = conn.cursor()
    
    start_date = date.today() - timedelta(days=days)
    
    cursor.execute("""
        SELECT 
            t.term,
            s.name as source,
            o.date,
            o.count
        FROM term_occurrences o
        JOIN terms t ON t.id = o.term_id
        JOIN sources s ON s.id = o.source_id
        WHERE t.term = ? AND o.date >= ?
        ORDER BY o.date DESC
    """, (term.lower(), start_date))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_trending_terms(
    days: int = 7,
    min_occurrences: int = 2,
    limit: int = 50,
    source_name: Optional[str] = None
) -> List[Dict]:
    """
    Get trending terms based on recent growth.
    
    Returns terms ranked by:
    1. Total occurrences in the period
    2. Number of different sources mentioning it
    3. Recency (more recent = higher score)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    start_date = date.today() - timedelta(days=days)
    
    query = """
        SELECT 
            t.term,
            t.first_seen,
            SUM(o.count) as total_count,
            COUNT(DISTINCT o.source_id) as source_count,
            MAX(o.date) as last_seen,
            GROUP_CONCAT(DISTINCT s.name) as sources
        FROM term_occurrences o
        JOIN terms t ON t.id = o.term_id
        JOIN sources s ON s.id = o.source_id
        WHERE o.date >= ?
    """
    params = [start_date]
    
    if source_name:
        query += " AND s.name = ?"
        params.append(source_name)
    
    query += """
        GROUP BY t.id
        HAVING total_count >= ?
        ORDER BY 
            source_count DESC,
            total_count DESC,
            last_seen DESC
        LIMIT ?
    """
    params.extend([min_occurrences, limit])
    
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_all_terms_for_period(days: int = 7) -> List[Dict]:
    """Get all terms with counts for a period, for analysis."""
    conn = get_connection()
    cursor = conn.cursor()
    
    start_date = date.today() - timedelta(days=days)
    
    cursor.execute("""
        SELECT 
            t.term,
            t.first_seen,
            o.date,
            s.name as source,
            o.count
        FROM term_occurrences o
        JOIN terms t ON t.id = o.term_id
        JOIN sources s ON s.id = o.source_id
        WHERE o.date >= ?
        ORDER BY o.date DESC, o.count DESC
    """, (start_date,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def log_collection_run(source_name: str, items: int, terms: int):
    """Log a collection run."""
    conn = get_connection()
    cursor = conn.cursor()
    source_id = get_source_id(conn, source_name)
    
    cursor.execute("""
        INSERT INTO collection_runs (source_id, date, items_collected, terms_extracted, completed_at)
        VALUES (?, ?, ?, ?, ?)
    """, (source_id, date.today(), items, terms, datetime.now()))
    
    conn.commit()
    conn.close()
