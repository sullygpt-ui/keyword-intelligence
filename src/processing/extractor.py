"""Term extraction from text using NLP."""

import re
from collections import Counter
from typing import Dict, List, Set
import spacy
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import MIN_TERM_LENGTH, MAX_TERM_LENGTH, MIN_TERM_FREQUENCY, STOP_TERMS


class TermExtractor:
    """Extract meaningful terms from text using NLP."""
    
    def __init__(self):
        """Initialize the extractor with spaCy model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Downloading spaCy model...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")
        
        # Disable unnecessary pipeline components for speed
        self.nlp.disable_pipes(["parser", "ner"])
        
        self.stop_terms = STOP_TERMS
    
    def extract_terms(self, texts: List[str]) -> Dict[str, int]:
        """
        Extract terms from a list of texts.
        
        Args:
            texts: List of text strings to process
            
        Returns:
            Dictionary of term -> count
        """
        all_terms = Counter()
        
        for text in texts:
            terms = self._extract_from_text(text)
            all_terms.update(terms)
        
        # Filter by minimum frequency
        filtered = {
            term: count 
            for term, count in all_terms.items() 
            if count >= MIN_TERM_FREQUENCY
        }
        
        return filtered
    
    def _extract_from_text(self, text: str) -> List[str]:
        """Extract terms from a single text."""
        if not text or not isinstance(text, str):
            return []
        
        # Clean text
        text = self._clean_text(text)
        
        # Process with spaCy
        doc = self.nlp(text)
        
        terms = []
        
        # Extract single tokens (nouns, proper nouns, adjectives that might be tech terms)
        for token in doc:
            if self._is_valid_token(token):
                term = token.lemma_.lower()
                if self._is_valid_term(term):
                    terms.append(term)
        
        # Extract noun chunks (multi-word terms like "machine learning")
        # Re-enable parser temporarily for this
        doc2 = self.nlp.make_doc(text)
        for chunk in self.nlp.get_pipe("parser")(doc2).noun_chunks if "parser" in self.nlp.pipe_names else []:
            chunk_text = chunk.text.lower().strip()
            if self._is_valid_compound_term(chunk_text):
                terms.append(chunk_text)
        
        # Also extract compound patterns directly
        compound_terms = self._extract_compound_terms(text)
        terms.extend(compound_terms)
        
        return terms
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove HTML entities
        text = re.sub(r'&#?x?[0-9a-fA-F]+;?', ' ', text)
        text = re.sub(r'&\w+;', ' ', text)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'www\.\S+', '', text)
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        # Remove common URL parts
        text = re.sub(r'\b(href|nofollow|rel|http|https|www|com|org|net|io)\b', ' ', text)
        # Remove special characters but keep hyphens in words
        text = re.sub(r'[^\w\s\-]', ' ', text)
        # Remove standalone single characters and numbers
        text = re.sub(r'\b\w\b', ' ', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _is_valid_token(self, token) -> bool:
        """Check if a spaCy token should be extracted."""
        # Skip stopwords, punctuation, numbers
        if token.is_stop or token.is_punct or token.is_digit:
            return False
        # Only nouns, proper nouns, and some adjectives
        if token.pos_ not in ("NOUN", "PROPN", "ADJ"):
            return False
        return True
    
    def _is_valid_term(self, term: str) -> bool:
        """Check if a term is valid for tracking."""
        # Length check
        if len(term) < MIN_TERM_LENGTH or len(term) > MAX_TERM_LENGTH:
            return False
        # Not a stop term
        if term in self.stop_terms:
            return False
        # Not purely numeric
        if term.isdigit():
            return False
        # Has at least some letters
        if not any(c.isalpha() for c in term):
            return False
        return True
    
    def _is_valid_compound_term(self, term: str) -> bool:
        """Check if a compound term is valid."""
        words = term.split()
        # Must be 2-4 words
        if len(words) < 2 or len(words) > 4:
            return False
        # Total length check
        if len(term) < MIN_TERM_LENGTH or len(term) > MAX_TERM_LENGTH:
            return False
        # Not all stop words
        if all(w in self.stop_terms for w in words):
            return False
        return True
    
    def _extract_compound_terms(self, text: str) -> List[str]:
        """Extract compound technical terms using patterns."""
        compounds = []
        text_lower = text.lower()
        
        # Common tech compound patterns
        patterns = [
            r'\b(\w+[\-]\w+)\b',  # Hyphenated terms like "open-source"
            r'\b(\w+\.js|\w+\.py|\w+\.ai)\b',  # Tech frameworks
            r'\b([A-Z][a-z]+[A-Z]\w+)\b',  # CamelCase terms
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._is_valid_term(match.lower()):
                    compounds.append(match.lower())
        
        return compounds


# Convenience function
def extract_terms(texts: List[str]) -> Dict[str, int]:
    """Extract terms from texts using default extractor."""
    extractor = TermExtractor()
    return extractor.extract_terms(texts)
