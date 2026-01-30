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


# Terms that are too obvious/established to be "emerging"
ESTABLISHED_TERMS = {
    # Well-known AI/ML terms (already mainstream)
    "model", "models", "machine", "learning", "neural", "network", "networks",
    "deep", "training", "inference", "algorithm", "algorithms", "prediction",
    "classification", "regression", "supervised", "unsupervised",
    
    # Established tech companies/products
    "google", "microsoft", "amazon", "apple", "meta", "facebook", "openai",
    "github", "aws", "azure", "cloud", "linux", "windows", "android", "ios",
    
    # Generic tech terms
    "api", "sdk", "framework", "library", "database", "server", "client",
    "frontend", "backend", "fullstack", "devops", "deployment", "container",
    "docker", "kubernetes", "microservice", "microservices",
    
    # Common programming terms
    "python", "javascript", "typescript", "rust", "golang", "java", "cpp",
    "function", "class", "object", "variable", "method", "interface",
    
    # Generic research terms
    "performance", "accuracy", "benchmark", "evaluation", "experiment",
    "dataset", "method", "approach", "technique", "system", "systems",
    "framework", "architecture", "implementation", "analysis", "result",
    "results", "study", "research", "paper", "propose", "proposed",
    
    # Overly generic
    "high", "low", "large", "small", "new", "novel", "efficient", "effective",
    "state", "art", "level", "multi", "single", "real", "end", "based",
    "generation", "image", "text", "video", "audio", "language", "natural",
    "process", "processing", "information", "knowledge", "task", "tasks",
    "feature", "features", "input", "output", "layer", "layers",
    "common", "within", "effect", "demand", "previous", "production", "build",
    "train", "alternative", "provide", "provider", "require", "present",
    "introduce", "traditional", "current", "specific", "general", "different",
    "standard", "complex", "simple", "main", "various", "multiple", "single",
    "available", "existing", "potential", "significant", "recent", "future",
    "possible", "important", "necessary", "similar", "related", "relevant",
    "experiments", "experiment", "experimental", "sample", "samples",
    "representation", "representations", "metric", "metrics", "assessment",
    "additional", "central", "region", "series", "soft", "base", "driven",
    "hard", "final", "initial", "original", "second", "total", "full",
    "control", "policy", "reward", "conditioning", "prefix", "community",
    "vision", "confidence", "repository", "star", "stars", "fork", "forks",
    "finally", "specifically", "increasing", "higher", "lower", "changes",
    "settings", "guidance", "directly", "across", "clearly", "typically",
    "overall", "therefore", "however", "although", "meanwhile", "hence",
    "state-of", "the-art", "state-of-the-art",
}


def get_emerging_terms(days: int = 7, min_count: int = 2, limit: int = 30) -> List[Dict]:
    """
    Find genuinely EMERGING terms - new or rapidly growing.
    
    Filters out:
    - Established/obvious terms
    - Single-source mentions (need cross-validation)
    - Very low counts (noise)
    
    Prioritizes:
    - Terms first seen recently
    - Terms appearing in academic sources (arXiv) = earlier signal
    - Terms in multiple sources = validation
    """
    all_data = get_all_terms_for_period(days=days)
    
    if not all_data:
        return []
    
    # Group by term
    term_stats = {}
    for record in all_data:
        term = record["term"]
        
        # Skip established terms
        if term.lower() in ESTABLISHED_TERMS:
            continue
        
        # Skip very short terms (likely noise)
        if len(term) < 4:
            continue
            
        if term not in term_stats:
            term_stats[term] = {
                "term": term,
                "first_seen": record["first_seen"],
                "total_count": 0,
                "sources": set(),
                "arxiv_count": 0,
                "hn_count": 0,
                "github_count": 0,
            }
        
        term_stats[term]["total_count"] += record["count"]
        term_stats[term]["sources"].add(record["source"])
        
        if record["source"] == "arxiv":
            term_stats[term]["arxiv_count"] += record["count"]
        elif record["source"] == "hackernews":
            term_stats[term]["hn_count"] += record["count"]
        elif record["source"] == "github":
            term_stats[term]["github_count"] += record["count"]
    
    # Calculate emergence score
    cutoff = date.today() - timedelta(days=days)
    
    emerging = []
    for term, stats in term_stats.items():
        # Require minimum count
        if stats["total_count"] < min_count:
            continue
        
        # Calculate emergence score
        score = 0
        
        # Bonus for being new (first seen within period)
        first_seen = stats["first_seen"]
        if isinstance(first_seen, str):
            first_seen = date.fromisoformat(first_seen)
        
        if first_seen >= cutoff:
            score += 50  # Big bonus for truly new terms
        
        # Bonus for arXiv presence (academic = early signal)
        if stats["arxiv_count"] > 0:
            score += 20
            # Extra bonus if arXiv-heavy (research term not yet mainstream)
            arxiv_ratio = stats["arxiv_count"] / stats["total_count"]
            if arxiv_ratio > 0.5:
                score += 15  # Mostly academic = very early
        
        # Bonus for cross-source validation
        source_count = len(stats["sources"])
        if source_count >= 2:
            score += 10 * source_count
        
        # Bonus for count (but diminishing - we don't want already-popular)
        # Sweet spot is moderate count, not too high
        if 5 <= stats["total_count"] <= 30:
            score += 10  # Goldilocks zone
        elif stats["total_count"] > 50:
            score -= 10  # Penalty for already being popular
        
        stats["emergence_score"] = score
        stats["source_count"] = source_count
        stats["sources"] = list(stats["sources"])
        stats["is_new"] = first_seen >= cutoff
        
        emerging.append(stats)
    
    # Sort by emergence score
    emerging.sort(key=lambda x: x["emergence_score"], reverse=True)
    
    return emerging[:limit]


def get_arxiv_only_terms(days: int = 7, min_count: int = 2, limit: int = 20) -> List[Dict]:
    """
    Find terms that appear in arXiv but NOT in HN/GitHub yet.
    These are the earliest signals - academic research that hasn't
    hit practitioner awareness.
    """
    all_data = get_all_terms_for_period(days=days)
    
    if not all_data:
        return []
    
    # Group by term
    term_stats = {}
    for record in all_data:
        term = record["term"]
        
        if term.lower() in ESTABLISHED_TERMS:
            continue
            
        if len(term) < 4:
            continue
            
        if term not in term_stats:
            term_stats[term] = {
                "term": term,
                "first_seen": record["first_seen"],
                "arxiv_count": 0,
                "other_count": 0,
            }
        
        if record["source"] == "arxiv":
            term_stats[term]["arxiv_count"] += record["count"]
        else:
            term_stats[term]["other_count"] += record["count"]
    
    # Filter to arXiv-only terms
    arxiv_only = []
    for term, stats in term_stats.items():
        if stats["arxiv_count"] >= min_count and stats["other_count"] == 0:
            arxiv_only.append({
                "term": term,
                "count": stats["arxiv_count"],
                "first_seen": stats["first_seen"],
                "signal": "arxiv_only"
            })
    
    arxiv_only.sort(key=lambda x: x["count"], reverse=True)
    return arxiv_only[:limit]
