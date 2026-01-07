"""
Report Generator

Generates JSON, Markdown, and HTML reports from keyword analysis.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import asdict

from processing.scoring import KeywordScore
from config import OUTPUT_DIR, WEEKLY_LIMIT

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates reports in multiple formats"""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(
        self,
        tiered_keywords: Dict[str, List[KeywordScore]],
        report_date: str = None
    ) -> Dict[str, Path]:
        """Generate all report formats"""
        report_date = report_date or datetime.now().strftime('%Y-%m-%d')

        paths = {}

        # Generate JSON
        json_path = self.generate_json(tiered_keywords, report_date)
        paths['json'] = json_path

        # Generate Markdown
        md_path = self.generate_markdown(tiered_keywords, report_date)
        paths['markdown'] = md_path

        # Generate HTML widget
        html_path = self.generate_html_widget(tiered_keywords, report_date)
        paths['html'] = html_path

        return paths

    def generate_json(
        self,
        tiered_keywords: Dict[str, List[KeywordScore]],
        report_date: str
    ) -> Path:
        """Generate JSON report"""
        output = {
            'report_date': report_date,
            'generated_at': datetime.now().isoformat(),
            'tier1_emerging': [self._score_to_dict(s) for s in tiered_keywords.get('emerging', [])],
            'tier2_validated': [self._score_to_dict(s) for s in tiered_keywords.get('validated', [])],
            'tier3_mainstream': [self._score_to_dict(s) for s in tiered_keywords.get('mainstream', [])],
        }

        output_path = self.output_dir / 'json' / f'keyword_report_{report_date}.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        logger.info(f"Generated JSON report: {output_path}")
        return output_path

    def _score_to_dict(self, score: KeywordScore) -> Dict:
        """Convert KeywordScore to dictionary for JSON"""
        return {
            'term': score.term,
            'score': score.score,
            'tier1_mentions': score.tier1_mentions,
            'tier3_mentions': score.tier3_mentions,
            'vc_sources': score.vc_sources,
            'earnings_sources': score.earnings_sources,
            'first_seen': score.first_seen,
            'is_cross_tier': score.is_cross_tier,
            'trend': score.trend,
            'percent_change': score.percent_change,
            'urls': score.urls[:3] if score.urls else []
        }

    def generate_markdown(
        self,
        tiered_keywords: Dict[str, List[KeywordScore]],
        report_date: str
    ) -> Path:
        """Generate Markdown report"""
        lines = []

        # Header
        lines.append(f"# Keyword Intelligence Report")
        lines.append(f"**Week of {report_date}**")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Emerging (Tier 1)
        lines.append("## EMERGING BUZZ (Tier 1)")
        lines.append("*Terms gaining traction in VC blogs and YC startups*")
        lines.append("")

        emerging = tiered_keywords.get('emerging', [])
        if emerging:
            for i, score in enumerate(emerging[:10], 1):
                trend_icon = self._get_trend_icon(score.trend)
                sources = ', '.join(score.vc_sources[:3]) if score.vc_sources else 'N/A'
                lines.append(f"{i}. **{score.term}** {trend_icon}")
                lines.append(f"   - Score: {score.score} | Sources: {sources}")
                lines.append(f"   - First seen: {score.first_seen}")
                if score.urls:
                    lines.append(f"   - [Source]({score.urls[0]})")
                lines.append("")
        else:
            lines.append("*No emerging terms this week*")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Validated (Cross-tier)
        lines.append("## VALIDATED & RISING (Cross-tier)")
        lines.append("*Terms appearing in both VC discourse AND Fortune 500 earnings*")
        lines.append("")

        validated = tiered_keywords.get('validated', [])
        if validated:
            for i, score in enumerate(validated[:10], 1):
                trend_icon = self._get_trend_icon(score.trend)
                change = f"+{score.percent_change}%" if score.percent_change > 0 else f"{score.percent_change}%"
                lines.append(f"{i}. **{score.term}** {trend_icon} ({change})")
                lines.append(f"   - Score: {score.score}")
                lines.append(f"   - VC Sources: {', '.join(score.vc_sources[:3])}")
                lines.append(f"   - F500 Mentions: {score.tier3_mentions}")
                lines.append("")
        else:
            lines.append("*No cross-tier validated terms this week*")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Mainstream (Tier 3)
        lines.append("## MAINSTREAM CORPORATE (Tier 3)")
        lines.append("*Hot terms in Fortune 500 earnings calls*")
        lines.append("")

        mainstream = tiered_keywords.get('mainstream', [])
        if mainstream:
            for i, score in enumerate(mainstream[:10], 1):
                trend_icon = self._get_trend_icon(score.trend)
                industries = ', '.join(score.earnings_sources[:5]) if score.earnings_sources else 'N/A'
                lines.append(f"{i}. **{score.term}** {trend_icon}")
                lines.append(f"   - Mentions: {score.tier3_mentions} | Companies: {industries}")
                lines.append("")
        else:
            lines.append("*No mainstream terms this week*")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Mike's Weekly Thesis (placeholder)
        lines.append("## MIKE'S WEEKLY THESIS")
        lines.append("*[Add your analysis here]*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Trend Tracker
        lines.append("## TREND TRACKER")
        lines.append("")
        lines.append("| Term | This Week | Trend | First Seen |")
        lines.append("|------|-----------|-------|------------|")

        all_keywords = emerging[:5] + validated[:5] + mainstream[:5]
        for score in all_keywords:
            trend_icon = self._get_trend_icon(score.trend)
            lines.append(f"| {score.term} | {score.score} | {trend_icon} | {score.first_seen} |")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"*Generated by Keyword Intelligence System on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

        # Write file
        output_path = self.output_dir / 'reports' / f'keyword_report_{report_date}.md'
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))

        logger.info(f"Generated Markdown report: {output_path}")
        return output_path

    def _get_trend_icon(self, trend: str) -> str:
        """Get emoji icon for trend"""
        icons = {
            'up': '📈',
            'down': '📉',
            'stable': '➡️',
            'new': '🆕'
        }
        return icons.get(trend, '')

    def generate_html_widget(
        self,
        tiered_keywords: Dict[str, List[KeywordScore]],
        report_date: str
    ) -> Path:
        """Generate HTML widget for WordPress sidebar"""
        html = f'''<!DOCTYPE html>
<html>
<head>
    <style>
        .keyword-widget {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 300px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .keyword-widget h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #333;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 5px;
        }}
        .keyword-widget ul {{
            list-style: none;
            padding: 0;
            margin: 0 0 15px 0;
        }}
        .keyword-widget li {{
            padding: 4px 0;
            font-size: 13px;
            display: flex;
            justify-content: space-between;
        }}
        .keyword-widget .term {{
            color: #1a1a1a;
            font-weight: 500;
        }}
        .keyword-widget .trend {{
            font-size: 12px;
        }}
        .keyword-widget .section-emerging {{ border-left: 3px solid #10b981; padding-left: 10px; }}
        .keyword-widget .section-validated {{ border-left: 3px solid #f59e0b; padding-left: 10px; }}
        .keyword-widget .section-mainstream {{ border-left: 3px solid #3b82f6; padding-left: 10px; }}
        .keyword-widget .updated {{
            font-size: 11px;
            color: #666;
            text-align: right;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="keyword-widget">
        <div class="section-emerging">
            <h3>🔥 Emerging</h3>
            <ul>
'''
        # Add emerging keywords
        for score in tiered_keywords.get('emerging', [])[:5]:
            trend = self._get_trend_icon(score.trend)
            html += f'                <li><span class="term">{score.term}</span><span class="trend">{trend}</span></li>\n'

        html += '''            </ul>
        </div>

        <div class="section-validated">
            <h3>✅ Validated</h3>
            <ul>
'''
        # Add validated keywords
        for score in tiered_keywords.get('validated', [])[:5]:
            trend = self._get_trend_icon(score.trend)
            html += f'                <li><span class="term">{score.term}</span><span class="trend">{trend}</span></li>\n'

        html += '''            </ul>
        </div>

        <div class="section-mainstream">
            <h3>📊 Mainstream</h3>
            <ul>
'''
        # Add mainstream keywords
        for score in tiered_keywords.get('mainstream', [])[:5]:
            trend = self._get_trend_icon(score.trend)
            html += f'                <li><span class="term">{score.term}</span><span class="trend">{trend}</span></li>\n'

        html += f'''            </ul>
        </div>

        <div class="updated">Updated: {report_date}</div>
    </div>
</body>
</html>
'''

        output_path = self.output_dir / 'widgets' / f'keyword_widget_{report_date}.html'
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(html)

        logger.info(f"Generated HTML widget: {output_path}")
        return output_path


def main():
    """Test report generation"""
    logging.basicConfig(level=logging.INFO)

    # Create test data
    from processing.scoring import KeywordScore

    test_keywords = {
        'emerging': [
            KeywordScore(
                term='agentic AI',
                keyword_id=1,
                score=85.0,
                tier1_mentions=12,
                tier3_mentions=0,
                yc_mentions=5,
                vc_sources=['a16z', 'sequoia'],
                earnings_sources=[],
                first_seen='2026-01-01',
                is_cross_tier=False,
                trend='new',
                percent_change=0,
                urls=['https://a16z.com/agentic-ai']
            ),
        ],
        'validated': [
            KeywordScore(
                term='embedded payments',
                keyword_id=2,
                score=120.0,
                tier1_mentions=8,
                tier3_mentions=34,
                yc_mentions=3,
                vc_sources=['bessemer', 'greylock'],
                earnings_sources=['AAPL', 'SQ', 'PYPL'],
                first_seen='2025-06-15',
                is_cross_tier=True,
                trend='up',
                percent_change=25.5,
                urls=[]
            ),
        ],
        'mainstream': [
            KeywordScore(
                term='digital twin',
                keyword_id=3,
                score=95.0,
                tier1_mentions=2,
                tier3_mentions=47,
                yc_mentions=0,
                vc_sources=[],
                earnings_sources=['GE', 'CAT', 'SIEMENS'],
                first_seen='2024-03-01',
                is_cross_tier=False,
                trend='up',
                percent_change=15.0,
                urls=[]
            ),
        ],
    }

    generator = ReportGenerator()
    paths = generator.generate_all(test_keywords)

    print("\nGenerated reports:")
    for format_name, path in paths.items():
        print(f"  {format_name}: {path}")


if __name__ == "__main__":
    main()
