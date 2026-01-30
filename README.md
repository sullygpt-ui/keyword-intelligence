# Keyword Intelligence

Early-signal keyword trend tracking for domain investment research.

## What It Does

Scans early-stage tech/business sources to identify trending terms *before* they hit mainstream. Helps predict which terms (and domain categories) will be valuable 1-3 years out.

## Phase 1 Sources

1. **Hacker News** — Tech community discussions, job posts, launches
2. **arXiv** — Academic CS/AI papers (cutting-edge research terms)
3. **GitHub Trending** — Popular repos and emerging tech topics

## How It Works

1. **Collect** — Pull content from sources daily
2. **Extract** — Identify meaningful terms/phrases using NLP
3. **Store** — Track term frequency over time
4. **Analyze** — Calculate velocity (which terms are growing fastest)
5. **Report** — Weekly summary of emerging terms

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize the database
python -m src.database.init

# Run collection (all sources)
python -m src.collect

# Generate trending report
python -m src.report
```

## Project Structure

```
keyword-intelligence/
├── src/
│   ├── collectors/      # Source-specific scrapers
│   │   ├── hackernews.py
│   │   ├── arxiv.py
│   │   └── github.py
│   ├── processing/      # NLP and term extraction
│   │   └── extractor.py
│   ├── database/        # Storage and queries
│   │   ├── init.py
│   │   ├── models.py
│   │   └── queries.py
│   ├── analysis/        # Trend calculations
│   │   └── trends.py
│   ├── collect.py       # Main collection script
│   └── report.py        # Generate reports
├── data/                # SQLite database
├── output/              # Generated reports
├── requirements.txt
└── config.py
```

## Future Phases

- **Phase 2**: Add Y Combinator, Product Hunt, patents, Twitter/X
- **Phase 3**: ML-based prediction, category clustering, domain scoring
