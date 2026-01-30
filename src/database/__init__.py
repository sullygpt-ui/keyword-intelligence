"""Database module for keyword storage and retrieval."""

from .init import init_database, get_connection
from .queries import (
    store_terms,
    get_term_history,
    get_trending_terms,
    get_all_terms_for_period,
)

__all__ = [
    "init_database",
    "get_connection", 
    "store_terms",
    "get_term_history",
    "get_trending_terms",
    "get_all_terms_for_period",
]
