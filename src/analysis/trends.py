"""Trend analysis and velocity calculations."""

from datetime import date, timedelta
from typing import Dict, List
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database import get_all_terms_for_period, get_term_history


def calculate_velocity(term: str, days: int = 14) -> Dict:
    """
    Calculate the velocity (rate of change) for a term.
    
    Compares the term's frequency in the recent half vs older half
    of the time period.
    
    Returns:
        Dict with velocity metrics
    """
    history = get_term_history(term, days=days)
    
    if not history:
        return {"term": term, "velocity": 0, "trend": "no_data"}
    
    # Split into recent and older periods
    midpoint = date.today() - timedelta(days=days // 2)
    
    recent_count = sum(r["count"] for r in history if r["date"] >= str(midpoint))
    older_count = sum(r["count"] for r in history if r["date"] < str(midpoint))
    
    # Calculate velocity
    if older_count == 0:
        if recent_count > 0:
            velocity = float('inf')  # New term
            trend = "new"
        else:
            velocity = 0
            trend = "no_data"
    else:
        velocity = (recent_count - older_count) / older_count
        if velocity > 0.5:
            trend = "rising"
        elif velocity < -0.5:
            trend = "falling"
        else:
            trend = "stable"
    
    return {
        "term": term,
        "recent_count": recent_count,
        "older_count": older_count,
        "velocity": velocity if velocity != float('inf') else 999,
        "trend": trend
    }


def find_emerging_terms(days: int = 7, min_count: int = 2) -> List[Dict]:
    """
    Find terms that are newly emerging (first appeared recently).
    
    These are potentially the most valuable early signals.
    """
    all_data = get_all_terms_for_period(days=days)
    
    if not all_data:
        return []
    
    # Group by term
    term_data = {}
    for record in all_data:
        term = record["term"]
        if term not in term_data:
            term_data[term] = {
                "term": term,
                "first_seen": record["first_seen"],
                "total_count": 0,
                "sources": set()
            }
        term_data[term]["total_count"] += record["count"]
        term_data[term]["sources"].add(record["source"])
    
    # Filter to recent first appearances
    cutoff = date.today() - timedelta(days=days)
    
    emerging = []
    for term, data in term_data.items():
        first_seen = data["first_seen"]
        if isinstance(first_seen, str):
            first_seen = date.fromisoformat(first_seen)
        
        if first_seen >= cutoff and data["total_count"] >= min_count:
            emerging.append({
                "term": term,
                "first_seen": str(data["first_seen"]),
                "count": data["total_count"],
                "source_count": len(data["sources"]),
                "sources": list(data["sources"])
            })
    
    # Sort by count (higher = more signal)
    emerging.sort(key=lambda x: x["count"], reverse=True)
    
    return emerging


def analyze_term(term: str) -> Dict:
    """Get comprehensive analysis for a single term."""
    velocity_data = calculate_velocity(term)
    history = get_term_history(term, days=30)
    
    return {
        "term": term,
        "velocity": velocity_data,
        "history": history,
        "total_mentions": sum(r["count"] for r in history),
        "sources": list(set(r["source"] for r in history))
    }
