"""
AI-Enhanced Report Generator

Uses Claude to add insightful commentary to keyword reports.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import anthropic

logger = logging.getLogger(__name__)


class AIReportGenerator:
    """Generates AI-enhanced keyword intelligence reports"""

    def __init__(self, api_key: str = None):
        # Use provided key, env var, or raise error
        api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.output_dir = Path(__file__).parent

    def generate_enhanced_report(self, tiered_keywords: Dict, report_date: str) -> str:
        """Generate a full AI-enhanced report"""

        # Build context about the keywords
        context = self._build_keyword_context(tiered_keywords)

        # Generate the AI-enhanced report
        prompt = f"""You are Mike, a domain name investor and enterprise tech consultant who writes a weekly newsletter about emerging technology terminology. You have deep expertise in:
- Enterprise software (Workday, SAP, Salesforce implementations)
- Domain name investing and valuation
- VC/startup ecosystem trends
- Fortune 500 digital transformation

Write a newsletter issue based on this week's keyword intelligence data. Use a conversational, insider tone - like you're sharing intelligence with fellow domain investors and tech watchers.

TODAY'S DATE: {report_date}

KEYWORD DATA:
{context}

Write the newsletter with these sections:

1. **Header** - "What VCs and Fortune 500 Are Talking About This Week" with the date

2. **🔮 EMERGING BUZZ (From VC Land)** - Pick the 3-4 most interesting emerging keywords. For each:
   - The term and where it was mentioned (sources)
   - What it actually means (plain English)
   - "Mike's take" - your honest analysis (be skeptical when warranted, excited when genuine)
   - Domain patterns to watch - discuss naming patterns and compound terms worth exploring (e.g., "[keyword]Platform.com", "Enterprise[keyword].com")

3. **✅ VALIDATED & RISING** - For cross-tier keywords that appear in both VC and mainstream:
   - The timeline of adoption
   - Why it's crossing over now
   - Domain implications

4. **📊 MAINSTREAM CORPORATE** - What Fortune 500 is talking about:
   - Top terms from financial news
   - What it means they're mainstream (domain opportunity low but validation high)

5. **🎯 MIKE'S WEEKLY THESIS** - Your bigger picture analysis:
   - What pattern are you seeing across all the data?
   - Strategic implications for domain investors
   - Predictions for next 12-24 months

6. **📈 TREND TRACKER** - Quick bullets on what's moving up/down

Be specific, be opinionated, suggest domain naming patterns worth exploring. Write like an insider sharing real intelligence, not a generic summary. Around 1500-2000 words total.

IMPORTANT: Do NOT make up specific "facts" that you cannot verify:
- Do NOT claim specific domains are "available" or "taken" (you don't have WHOIS data)
- Do NOT mention specific sale prices unless from the provided data
- Do NOT claim domains are "expiring" or give expiration dates
- DO suggest naming patterns and compound term strategies
- DO discuss general market observations based on the keyword data provided"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            report_content = response.content[0].text
        except Exception as e:
            logger.error(f"Error generating AI report: {e}")
            report_content = self._generate_fallback_report(tiered_keywords, report_date)

        # Save the report
        output_path = self.output_dir / "reports" / f"newsletter_{report_date}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_content)
        logger.info(f"Generated AI newsletter: {output_path}")

        return str(output_path)

    def _build_keyword_context(self, tiered_keywords: Dict) -> str:
        """Build context string from keyword data"""
        lines = []

        lines.append("## EMERGING (Tier 1 - VC Blogs + YC Companies)")
        for kw in tiered_keywords.get('emerging', [])[:15]:
            # Handle both dict and dataclass objects
            if hasattr(kw, 'term'):
                term = kw.term
                score = kw.score
                vc_sources = getattr(kw, 'vc_sources', [])[:3]
                yc_mentions = getattr(kw, 'yc_mentions', 0)
            else:
                term = kw.get('term', '')
                score = kw.get('score', 0)
                vc_sources = kw.get('sources', {}).get('vc_blog', [])[:3]
                yc_mentions = kw.get('yc_mentions', 0)

            lines.append(f"- {term} (Score: {score:.1f})")
            if vc_sources:
                lines.append(f"  VC Sources: {', '.join(vc_sources)}")
            if yc_mentions:
                lines.append(f"  YC Companies mentioning: {yc_mentions}")

        lines.append("\n## VALIDATED (Cross-tier - Appearing in both VC and Mainstream)")
        for kw in tiered_keywords.get('validated', [])[:10]:
            if hasattr(kw, 'term'):
                term = kw.term
                score = kw.score
                vc_sources = getattr(kw, 'vc_sources', [])[:3]
                f500_count = getattr(kw, 'tier3_mentions', 0)
            else:
                term = kw.get('term', '')
                score = kw.get('score', 0)
                vc_sources = kw.get('sources', {}).get('vc_blog', [])[:3]
                f500_count = kw.get('tier3_mentions', 0)

            lines.append(f"- {term} (Score: {score:.1f})")
            lines.append(f"  VC Sources: {', '.join(vc_sources)}")
            lines.append(f"  Fortune 500/News Mentions: {f500_count}")

        lines.append("\n## MAINSTREAM (Tier 3 - Financial News / Fortune 500)")
        for kw in tiered_keywords.get('mainstream', [])[:15]:
            if hasattr(kw, 'term'):
                term = kw.term
                tier3_mentions = getattr(kw, 'tier3_mentions', 1)
                sources = getattr(kw, 'earnings_sources', [])[:5]
            else:
                term = kw.get('term', '')
                tier3_mentions = kw.get('tier3_mentions', 1)
                sources = kw.get('sources', {}).get('earnings_call', [])[:5]

            lines.append(f"- {term} (Mentions: {tier3_mentions})")
            if sources:
                lines.append(f"  Sources: {', '.join(sources)}")

        return '\n'.join(lines)

    def _generate_fallback_report(self, tiered_keywords: Dict, report_date: str) -> str:
        """Generate a basic report if AI fails"""
        lines = [
            f"# What VCs and Fortune 500 Are Talking About This Week",
            f"**Published {report_date}**\n",
            "---\n",
            "## 🔮 EMERGING BUZZ\n"
        ]

        for kw in tiered_keywords.get('emerging', [])[:5]:
            term = kw.term if hasattr(kw, 'term') else kw.get('term', '')
            score = kw.score if hasattr(kw, 'score') else kw.get('score', 0)
            lines.append(f"**{term}**")
            lines.append(f"- Score: {score:.1f}\n")

        lines.append("\n## ✅ VALIDATED & RISING\n")
        for kw in tiered_keywords.get('validated', [])[:5]:
            term = kw.term if hasattr(kw, 'term') else kw.get('term', '')
            score = kw.score if hasattr(kw, 'score') else kw.get('score', 0)
            lines.append(f"**{term}** - Score: {score:.1f}\n")

        lines.append("\n## 📊 MAINSTREAM CORPORATE\n")
        for kw in tiered_keywords.get('mainstream', [])[:5]:
            term = kw.term if hasattr(kw, 'term') else kw.get('term', '')
            lines.append(f"**{term}**\n")

        return '\n'.join(lines)


def main():
    """Test AI report generation"""
    logging.basicConfig(level=logging.INFO)

    # Load the latest JSON report
    json_dir = Path(__file__).parent / "json"
    json_files = sorted(json_dir.glob("keyword_report_*.json"), reverse=True)

    if not json_files:
        print("No JSON reports found. Run main.py first.")
        return

    latest = json_files[0]
    print(f"Loading: {latest}")

    with open(latest) as f:
        data = json.load(f)

    generator = AIReportGenerator()
    report_date = datetime.now().strftime('%Y-%m-%d')

    # Convert flat lists to the expected format
    tiered = {
        'emerging': data.get('emerging', []),
        'validated': data.get('validated', []),
        'mainstream': data.get('mainstream', [])
    }

    path = generator.generate_enhanced_report(tiered, report_date)
    print(f"\nGenerated: {path}")

    # Print preview
    with open(path) as f:
        print("\n" + "=" * 60)
        print(f.read()[:2000])
        print("..." if len(f.read()) > 2000 else "")


if __name__ == "__main__":
    main()
