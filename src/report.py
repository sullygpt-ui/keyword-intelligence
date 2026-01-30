"""Generate trending term reports."""

import argparse
from datetime import date, timedelta
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OUTPUT_DIR
from src.database import get_trending_terms, get_term_history
from src.analysis.trends import get_emerging_terms, get_arxiv_only_terms


def generate_report(days: int = 7, limit: int = 50, output_file: str = None):
    """Generate a trending terms report."""
    
    print(f"\n{'='*60}")
    print(f"KEYWORD INTELLIGENCE REPORT")
    print(f"Period: Last {days} days (as of {date.today()})")
    print('='*60)
    
    # Get trending terms
    trending = get_trending_terms(days=days, limit=limit)
    
    if not trending:
        print("\nNo data found. Run collection first:")
        print("  python -m src.collect")
        return
    
    # Build report content
    lines = []
    lines.append(f"# Keyword Intelligence Report")
    lines.append(f"**Generated:** {date.today()}")
    lines.append(f"**Period:** Last {days} days")
    lines.append(f"")
    lines.append(f"## Top Trending Terms")
    lines.append(f"")
    lines.append(f"| Rank | Term | Count | Sources | First Seen |")
    lines.append(f"|------|------|-------|---------|------------|")
    
    for i, term_data in enumerate(trending, 1):
        term = term_data["term"]
        count = term_data["total_count"]
        sources = term_data["source_count"]
        first_seen = term_data["first_seen"]
        source_list = term_data["sources"]
        
        lines.append(f"| {i} | **{term}** | {count} | {sources} ({source_list}) | {first_seen} |")
        
        # Print to console too
        print(f"{i:3d}. {term:30s} | count: {count:3d} | sources: {sources} | {source_list}")
    
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Breakdown by Source")
    lines.append(f"")
    
    # Get source-specific trends
    for source in ["hackernews", "arxiv", "github"]:
        source_trending = get_trending_terms(days=days, limit=20, source_name=source)
        if source_trending:
            lines.append(f"### {source.title()}")
            lines.append(f"")
            for term_data in source_trending[:10]:
                lines.append(f"- **{term_data['term']}** ({term_data['total_count']})")
            lines.append(f"")
    
    # Write to file
    if output_file is None:
        output_file = OUTPUT_DIR / f"report_{date.today()}.md"
    else:
        output_file = Path(output_file)
    
    report_content = "\n".join(lines)
    output_file.write_text(report_content)
    
    print(f"\n{'='*60}")
    print(f"Report saved to: {output_file}")
    print('='*60)


def generate_emerging_report(days: int = 7, limit: int = 30):
    """Generate a report focused on EMERGING terms, not just popular ones."""
    
    print(f"\n{'='*60}")
    print(f"🚀 EMERGING TERMS REPORT")
    print(f"Period: Last {days} days (as of {date.today()})")
    print(f"Focus: New & growing terms, not already-mainstream")
    print('='*60)
    
    # Get emerging terms
    emerging = get_emerging_terms(days=days, limit=limit)
    
    if not emerging:
        print("\nNo emerging terms found. Need more data - run collection for a few days.")
        return
    
    print(f"\n📈 TOP EMERGING TERMS (by emergence score)")
    print(f"{'Term':<30} {'Score':>6} {'Count':>6} {'Sources':>8} {'New?':>5}")
    print("-" * 60)
    
    for term_data in emerging[:20]:
        term = term_data["term"]
        score = term_data["emergence_score"]
        count = term_data["total_count"]
        sources = term_data["source_count"]
        is_new = "✨" if term_data["is_new"] else ""
        
        print(f"{term:<30} {score:>6} {count:>6} {sources:>8} {is_new:>5}")
    
    # Get arXiv-only terms (earliest signals)
    arxiv_only = get_arxiv_only_terms(days=days, limit=15)
    
    if arxiv_only:
        print(f"\n🔬 ARXIV-ONLY TERMS (academic signals not yet in HN/GitHub)")
        print(f"{'Term':<30} {'Count':>6}")
        print("-" * 40)
        
        for term_data in arxiv_only[:10]:
            print(f"{term_data['term']:<30} {term_data['count']:>6}")
    
    # Save report
    output_file = OUTPUT_DIR / f"emerging_{date.today()}.md"
    
    lines = [
        f"# Emerging Terms Report - {date.today()}",
        f"",
        f"## Top Emerging Terms",
        f"",
        f"| Term | Score | Count | Sources | New? |",
        f"|------|-------|-------|---------|------|",
    ]
    
    for term_data in emerging[:20]:
        new_marker = "✨" if term_data["is_new"] else ""
        lines.append(f"| {term_data['term']} | {term_data['emergence_score']} | {term_data['total_count']} | {term_data['source_count']} | {new_marker} |")
    
    if arxiv_only:
        lines.extend([
            f"",
            f"## arXiv-Only Terms (Earliest Signals)",
            f"",
        ])
        for term_data in arxiv_only[:10]:
            lines.append(f"- **{term_data['term']}** ({term_data['count']})")
    
    output_file.write_text("\n".join(lines))
    print(f"\nReport saved to: {output_file}")


def show_term_detail(term: str, days: int = 30):
    """Show detailed history for a specific term."""
    print(f"\n{'='*60}")
    print(f"TERM DETAIL: {term}")
    print('='*60)
    
    history = get_term_history(term, days=days)
    
    if not history:
        print(f"No data found for term: {term}")
        return
    
    print(f"\nOccurrences over last {days} days:")
    print(f"{'Date':<12} {'Source':<15} {'Count':<6}")
    print("-" * 35)
    
    for record in history:
        print(f"{record['date']:<12} {record['source']:<15} {record['count']:<6}")


def main():
    parser = argparse.ArgumentParser(description="Generate keyword trend reports")
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=7,
        help="Number of days to analyze (default: 7)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=50,
        help="Number of top terms to show (default: 50)"
    )
    parser.add_argument(
        "--term", "-t",
        type=str,
        help="Show detail for a specific term"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (default: output/report_DATE.md)"
    )
    parser.add_argument(
        "--emerging", "-e",
        action="store_true",
        help="Show emerging terms report (filters out mainstream terms)"
    )
    args = parser.parse_args()
    
    if args.term:
        show_term_detail(args.term, days=args.days)
    elif args.emerging:
        generate_emerging_report(days=args.days, limit=args.limit)
    else:
        generate_report(days=args.days, limit=args.limit, output_file=args.output)


if __name__ == "__main__":
    main()
