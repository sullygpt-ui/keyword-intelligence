"""
Keyword Extraction Module

Uses NLP to extract meaningful multi-word phrases from text content.
"""
import re
import logging
from typing import List, Set, Tuple
from collections import Counter

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from config import MIN_KEYWORD_LENGTH, MAX_KEYWORD_LENGTH, FILTER_PHRASES

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """Extracts meaningful keyword phrases from text"""

    def __init__(self):
        self.nlp = None
        self.filter_phrases = {p.lower() for p in FILTER_PHRASES}
        self._load_spacy()

    def _load_spacy(self):
        """Load spaCy model"""
        if not SPACY_AVAILABLE:
            logger.warning("spaCy not installed, using basic extraction")
            return

        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model")
        except OSError:
            logger.warning("spaCy model not found. Run: python -m spacy download en_core_web_sm")
            self.nlp = None

    def extract_keywords(self, text: str) -> List[Tuple[str, int]]:
        """
        Extract keywords from text.
        Returns list of (keyword, count) tuples.
        """
        if not text:
            return []

        if self.nlp:
            return self._extract_with_spacy(text)
        else:
            return self._extract_basic(text)

    def _extract_with_spacy(self, text: str) -> List[Tuple[str, int]]:
        """Extract keywords using spaCy NLP"""
        # Process text (limit to 100k chars to avoid memory issues)
        doc = self.nlp(text[:100000])

        phrases = []

        # Build set of person names to filter
        person_names = set()
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                person_names.add(ent.text.lower())
                # Also add parts of the name
                for part in ent.text.split():
                    person_names.add(part.lower())

        # Extract noun chunks (noun phrases)
        for chunk in doc.noun_chunks:
            phrase = self._clean_phrase(chunk.text)
            # Skip if it contains a person name
            if any(name in phrase.lower() for name in person_names if len(name) > 2):
                continue
            if self._is_valid_phrase(phrase):
                phrases.append(phrase)

        # Also extract named entities that look like concepts (NOT people or places)
        for ent in doc.ents:
            if ent.label_ in {'PRODUCT', 'EVENT', 'WORK_OF_ART', 'LAW'}:
                phrase = self._clean_phrase(ent.text)
                if self._is_valid_phrase(phrase):
                    phrases.append(phrase)

        # Extract n-grams that match technology/business patterns
        tech_phrases = self._extract_tech_patterns(text)
        phrases.extend(tech_phrases)

        # Normalize all phrases to lowercase for deduplication
        normalized_phrases = [p.lower() for p in phrases]

        # Count and return
        counter = Counter(normalized_phrases)
        return counter.most_common()

    def _extract_basic(self, text: str) -> List[Tuple[str, int]]:
        """Basic extraction without spaCy"""
        words = text.lower().split()
        phrases = []

        # Extract 2-4 word n-grams
        for n in range(MIN_KEYWORD_LENGTH, MAX_KEYWORD_LENGTH + 1):
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                phrase = self._clean_phrase(phrase)
                if self._is_valid_phrase(phrase):
                    phrases.append(phrase)

        counter = Counter(phrases)
        return counter.most_common()

    def _extract_tech_patterns(self, text: str) -> List[str]:
        """Extract phrases matching technology/business patterns"""
        phrases = []

        # Common tech term patterns
        patterns = [
            # AI/ML terms
            r'\b(agentic\s+\w+)\b',
            r'\b(\w+\s+AI)\b',
            r'\b(AI\s+\w+)\b',
            r'\b(\w+\s+learning)\b',
            r'\b(generative\s+\w+)\b',

            # Tech infrastructure
            r'\b(\w+\s+computing)\b',
            r'\b(\w+\s+infrastructure)\b',
            r'\b(\w+\s+platform)\b',
            r'\b(\w+\s+as\s+a\s+service)\b',

            # Business models
            r'\b(\w+\s+SaaS)\b',
            r'\b(vertical\s+\w+)\b',
            r'\b(\w+\s+marketplace)\b',
            r'\b(embedded\s+\w+)\b',

            # Fintech
            r'\b(\w+\s+payments)\b',
            r'\b(\w+\s+banking)\b',
            r'\b(\w+\s+fintech)\b',

            # Enterprise
            r'\b(\w+\s+automation)\b',
            r'\b(\w+\s+observability)\b',
            r'\b(\w+\s+orchestration)\b',

            # Industry specific
            r'\b(digital\s+twin\w*)\b',
            r'\b(supply\s+chain\s+\w+)\b',
            r'\b(predictive\s+\w+)\b',
        ]

        text_lower = text.lower()
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                phrase = self._clean_phrase(match)
                if self._is_valid_phrase(phrase):
                    phrases.append(phrase)

        return phrases

    def _clean_phrase(self, phrase: str) -> str:
        """Clean and normalize a phrase"""
        # Remove extra whitespace
        phrase = ' '.join(phrase.split())

        # Remove leading/trailing punctuation
        phrase = re.sub(r'^[^\w]+|[^\w]+$', '', phrase)

        # Normalize case (lowercase, but preserve common acronyms)
        words = []
        for word in phrase.split():
            if word.isupper() and len(word) <= 5:
                words.append(word)  # Keep acronyms
            else:
                words.append(word.lower())

        return ' '.join(words)

    def _is_valid_phrase(self, phrase: str) -> bool:
        """Check if a phrase is a valid keyword"""
        if not phrase:
            return False

        words = phrase.split()
        phrase_lower = phrase.lower()

        # Check word count
        if len(words) < MIN_KEYWORD_LENGTH or len(words) > MAX_KEYWORD_LENGTH:
            return False

        # Filter out common jargon
        if phrase_lower in self.filter_phrases:
            return False

        # Stopwords that invalidate phrases
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                     'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'this',
                     'that', 'these', 'those', 'it', 'its', 'we', 'our', 'you', 'your',
                     'they', 'their', 'he', 'she', 'him', 'her', 'i', 'my', 'me'}

        # Filter phrases that START with a stopword (removes "the ai", "of ai", etc.)
        if words[0].lower() in stopwords:
            return False

        # Filter phrases that END with a stopword
        if words[-1].lower() in stopwords:
            return False

        # Filter out phrases that are just stopwords
        meaningful_words = [w for w in words if w.lower() not in stopwords]
        if len(meaningful_words) < 1:
            return False

        # Filter social media and website terms
        social_terms = {'share', 'linkedin', 'facebook', 'twitter', 'post', 'click',
                        'subscribe', 'newsletter', 'email', 'sign up', 'read more',
                        'learn more', 'view all', 'see more', 'follow', 'like'}
        if any(term in phrase_lower for term in social_terms):
            return False

        # Filter VC firm names and generic company terms
        vc_firms = {'sequoia', 'greylock', 'andreessen', 'a16z', 'bessemer', 'accel',
                    'benchmark', 'kleiner', 'nfx', 'lightspeed', 'index ventures',
                    'first round', 'capital', 'ventures', 'partners', 'portfolio'}
        if any(firm in phrase_lower for firm in vc_firms):
            return False

        # Filter out phrases with numbers only
        if all(w.isdigit() for w in words):
            return False

        # Filter out very short phrases (< 5 chars total)
        if len(phrase) < 5:
            return False

        # Filter out phrases with only single-letter words
        if all(len(w) <= 1 for w in words):
            return False

        # Filter out generic terms
        generic_terms = {'new way', 'first time', 'next step', 'last year', 'next year',
                         'more than', 'less than', 'most important', 'new era',
                         'big data', 'best practices', 'key takeaways', 'main point',
                         'related topics', 'funding announcement', 'business users',
                         'ai future', 'ai era', 'news article', 'blog post',
                         'where ai', 'just the beginning', 'little impact', 'ai remains',
                         'ai trade', 'says ai', 'nearly 70', 'top shape'}
        if phrase_lower in generic_terms:
            return False

        # Filter financial news noise terms
        news_noise = {'yahoo finance', 'marketwatch', 'cnbc', 'reuters', 'bloomberg',
                      'seeking alpha', 'wall street', 'stock market', 'market cap',
                      'stock price', 'share price', 'stock dips', 'stock rises',
                      'stock falls', 'stock gains', 'stocks to watch', 'trading day',
                      'market close', 'market open', 'earnings report', 'earnings call',
                      'quarterly results', 'fiscal quarter', 'revenue growth',
                      'upbeat outlook', 'costco dips', 'broadcom stock', 'money challenge',
                      'finance earnings', 'finance video', 'analyst rating', 'buy rating',
                      'hold rating', 'sell rating', 'price target', 'ticker symbol',
                      'morning squawk', 'five key', 'key things', 'weak revenue',
                      'down ai', 'ai stocks', 'new year', 'quarterly earnings',
                      'earnings preview', 'earnings news', 'google news', 'news search',
                      'trader trafigura', 'kratos defense', 'venezuela oil'}
        if any(noise in phrase_lower for noise in news_noise):
            return False

        # Filter company stock terms (ticker + stock/shares/price)
        stock_pattern = re.compile(r'\b(stock|shares|price|dips|rises|falls|gains|jumps|drops)\b', re.IGNORECASE)
        if stock_pattern.search(phrase_lower):
            return False

        # Filter out person names (two or three capitalized words that look like names)
        # Check original phrase before lowercasing
        original_words = phrase.split()
        if len(original_words) in [2, 3]:
            # If all words start with capital and rest lowercase, likely a name
            looks_like_name = all(
                w[0].isupper() and (len(w) == 1 or w[1:].islower())
                for w in original_words if w and not w.isupper()
            )
            if looks_like_name and not any(w.isupper() for w in original_words):
                # Additional check: common name patterns
                common_titles = {'mr', 'mrs', 'ms', 'dr', 'prof'}
                if original_words[0].lower() not in common_titles:
                    # Likely a person name like "John Smith" or "Mary Jane Watson"
                    return False

        return True

    def extract_from_posts(self, posts: List[dict]) -> List[Tuple[str, int, List[str]]]:
        """
        Extract keywords from multiple posts.
        Returns list of (keyword, total_count, source_names) tuples.
        """
        keyword_sources = {}  # keyword -> set of source names
        keyword_counts = Counter()

        for post in posts:
            text = f"{post.get('title', '')} {post.get('content', '')}"
            keywords = self.extract_keywords(text)

            source = post.get('source_name', 'unknown')

            for keyword, count in keywords:
                keyword_counts[keyword] += count
                if keyword not in keyword_sources:
                    keyword_sources[keyword] = set()
                keyword_sources[keyword].add(source)

        # Combine results
        results = []
        for keyword, count in keyword_counts.most_common():
            sources = list(keyword_sources.get(keyword, []))
            results.append((keyword, count, sources))

        return results


def main():
    """Test keyword extraction"""
    logging.basicConfig(level=logging.INFO)

    extractor = KeywordExtractor()

    test_text = """
    The rise of agentic AI is transforming enterprise software. Companies are now
    exploring vertical SaaS solutions with embedded payments and AI-powered automation.
    Digital twin technology is seeing adoption across manufacturing and healthcare.
    Supply chain visibility has become a top priority following recent disruptions.
    Generative AI applications are moving from experimental to production deployments.
    The platform economy continues to evolve with new marketplace models.
    """

    keywords = extractor.extract_keywords(test_text)

    print("\nExtracted Keywords:")
    for keyword, count in keywords[:20]:
        print(f"  {keyword}: {count}")


if __name__ == "__main__":
    main()
