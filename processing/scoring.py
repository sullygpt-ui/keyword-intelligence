"""
Keyword Scoring Algorithm

Calculates relevance scores for keywords based on:
- Source tier (VC blogs vs earnings calls)
- Cross-tier validation
- Trend momentum
- Recency
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class KeywordScore:
    """Represents a scored keyword"""
    term: str
    keyword_id: int
    score: float
    tier1_mentions: int  # VC blogs + YC
    tier3_mentions: int  # Earnings calls
    yc_mentions: int
    vc_sources: List[str]
    earnings_sources: List[str]
    first_seen: str
    is_cross_tier: bool
    trend: str  # 'up', 'down', 'stable', 'new'
    percent_change: float
    urls: List[str]


class KeywordScorer:
    """Calculates keyword scores based on mentions and patterns"""

    # Scoring weights
    VC_BLOG_WEIGHT = 10        # Per VC blog mentioning
    YC_COMPANY_WEIGHT = 0.5    # Per YC company using term
    EARNINGS_WEIGHT = 1        # Per earnings mention (capped)
    EARNINGS_CAP = 50          # Maximum earnings contribution
    CROSS_TIER_BONUS = 50      # Bonus for appearing in both tiers
    NEW_KEYWORD_BONUS = 20     # Bonus for first-time appearance
    TREND_MULTIPLIER = 0.5     # Multiplier for percent increase

    def __init__(self, db):
        self.db = db

    def calculate_score(
        self,
        keyword_id: int,
        term: str,
        vc_mentions: int,
        yc_mentions: int,
        earnings_mentions: int,
        vc_sources: List[str],
        earnings_sources: List[str],
        first_seen: str,
        current_week: str,
        urls: List[str] = None
    ) -> KeywordScore:
        """Calculate the relevance score for a keyword"""
        score = 0.0

        # Tier 1 (VC/YC) scoring
        unique_vc_sources = len(set(vc_sources))
        score += unique_vc_sources * self.VC_BLOG_WEIGHT
        score += yc_mentions * self.YC_COMPANY_WEIGHT

        tier1_mentions = vc_mentions + yc_mentions

        # Tier 3 (Earnings) scoring with cap
        tier3_score = min(earnings_mentions, self.EARNINGS_CAP) * self.EARNINGS_WEIGHT
        score += tier3_score

        # Cross-tier validation bonus
        is_cross_tier = tier1_mentions > 0 and earnings_mentions > 0
        if is_cross_tier:
            score += self.CROSS_TIER_BONUS

        # Recency bonus (first seen this week)
        is_new = first_seen >= current_week
        if is_new:
            score += self.NEW_KEYWORD_BONUS

        # Trend calculation
        prev_score = self.db.get_previous_week_score(keyword_id, current_week)
        trend, percent_change = self._calculate_trend(prev_score, score)

        # Trend momentum bonus
        if trend == 'up' and percent_change > 0:
            score += percent_change * self.TREND_MULTIPLIER

        return KeywordScore(
            term=term,
            keyword_id=keyword_id,
            score=round(score, 2),
            tier1_mentions=tier1_mentions,
            tier3_mentions=earnings_mentions,
            yc_mentions=yc_mentions,
            vc_sources=list(set(vc_sources)),
            earnings_sources=list(set(earnings_sources)),
            first_seen=first_seen,
            is_cross_tier=is_cross_tier,
            trend=trend if not is_new else 'new',
            percent_change=round(percent_change, 1),
            urls=urls or []
        )

    def _calculate_trend(
        self,
        prev_score: Optional[float],
        current_score: float
    ) -> Tuple[str, float]:
        """Calculate trend direction and percent change"""
        if prev_score is None or prev_score == 0:
            return 'new', 0.0

        percent_change = ((current_score - prev_score) / prev_score) * 100

        if percent_change > 10:
            return 'up', percent_change
        elif percent_change < -10:
            return 'down', percent_change
        else:
            return 'stable', percent_change

    def score_all_keywords(self, week_start: str) -> List[KeywordScore]:
        """Score all keywords in the database"""
        keywords = self.db.get_all_keywords_with_stats()
        scores = []

        for kw in keywords:
            sources = self.db.get_keyword_sources(kw['id'])

            score = self.calculate_score(
                keyword_id=kw['id'],
                term=kw['term'],
                vc_mentions=kw['vc_mentions'],
                yc_mentions=kw['yc_mentions'],
                earnings_mentions=kw['earnings_mentions'],
                vc_sources=sources.get('vc_blog', []),
                earnings_sources=sources.get('earnings_call', []),
                first_seen=kw['first_seen'],
                current_week=week_start,
                urls=sources.get('urls', [])
            )

            # Save weekly score to database
            self.db.save_weekly_score(
                keyword_id=kw['id'],
                week_start=week_start,
                tier1_mentions=score.tier1_mentions,
                tier3_mentions=score.tier3_mentions,
                yc_mentions=score.yc_mentions,
                score=score.score
            )

            scores.append(score)

        # Sort by score descending
        scores.sort(key=lambda x: x.score, reverse=True)

        return scores

    def get_tier_keywords(
        self,
        scores: List[KeywordScore],
        limit: int = 20
    ) -> Dict[str, List[KeywordScore]]:
        """
        Categorize keywords into tiers:
        - emerging: Tier 1 only (VC/YC, not yet in earnings)
        - validated: Cross-tier (both Tier 1 and Tier 3)
        - mainstream: Tier 3 heavy (mostly earnings mentions)
        """
        emerging = []
        validated = []
        mainstream = []

        for score in scores:
            if score.is_cross_tier:
                validated.append(score)
            elif score.tier1_mentions > 0 and score.tier3_mentions == 0:
                emerging.append(score)
            elif score.tier3_mentions > score.tier1_mentions:
                mainstream.append(score)
            else:
                # Default to emerging if more Tier 1
                emerging.append(score)

        return {
            'emerging': emerging[:limit],
            'validated': validated[:limit],
            'mainstream': mainstream[:limit]
        }


def main():
    """Test scoring"""
    logging.basicConfig(level=logging.INFO)

    # Would need database to test fully
    print("Scoring module loaded successfully")
    print(f"VC Blog Weight: {KeywordScorer.VC_BLOG_WEIGHT}")
    print(f"Cross-tier Bonus: {KeywordScorer.CROSS_TIER_BONUS}")
    print(f"New Keyword Bonus: {KeywordScorer.NEW_KEYWORD_BONUS}")


if __name__ == "__main__":
    main()
