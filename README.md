# Healthcare Payer-Provider Negotiation Monitor

A Streamlit intelligence dashboard that scrapes healthcare news, analyzes it with a local Ollama LLM, and generates inferred payer-side strategic perspectives for Cigna, UnitedHealthcare, and Anthem — focused on the NY/CT/NJ tri-state region.

## What it does

**Every hour** (or on-demand), the system:

1. **Fetches** articles from 23 RSS feeds and 1 scraped page — covering national healthcare outlets plus NY/CT/NJ-specific sources
2. **Filters** for negotiation-relevant keywords and tags articles by state (NY, CT, NJ)
3. **Analyzes** each article with your local Ollama model, scoring relevance 1–10 and extracting parties, negotiation type, key insights, and action signals
4. **Infers payer perspectives** — for each high-scoring article, generates what Cigna, UnitedHealthcare, and Anthem's contracting teams would likely be thinking, using detailed context prompts about each payer's position
5. **Displays everything** in a live Streamlit dashboard with chain-of-thought visibility

## Quick Start

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone/download and enter the directory
cd healthcare-monitor

# Create environment and install deps
uv sync

# Start Ollama (separate terminal)
ollama serve
ollama pull gemma4

# Launch the dashboard
uv run streamlit run app/dashboard.py
```

## Dashboard Tabs

### 🔴 Live Chain of Thought
Watch the LLM analyze each article in real-time. Every step is logged — fetching, scoring, payer inference — with expandable raw LLM responses.

### 📊 Results
Filterable table of scored articles. Filter by state, negotiation type, and minimum score. Each result includes the analysis, action signals, and a link to the source.

### 🗺️ State Breakdown
NY, CT, and NJ each get a panel showing state-specific articles alongside regulatory context (network adequacy rules, CON requirements, Medicaid structures, antitrust environment).

### 🧠 Payer Perspectives
Select Cigna, United, or Anthem to see what each payer's contracting team would likely think about each article. The system uses detailed context prompts encoding each payer's market position, recent disputes, and strategic priorities.

## CLI Usage

```bash
# Test Ollama connection
uv run python -m app.main --test

# Fetch only (no Ollama needed)
uv run python -m app.main --fetch-only

# Run once
uv run python -m app.main

# Run on schedule (every 60 min)
uv run python -m app.main --schedule
```

## Sources (23 RSS + 1 scraped)

### National (12)
MobiHealthNews, Health Leaders Media, MedCity News, Fierce Healthcare, Healthcare Dive, BioPharma Dive, Healthcare IT News, KFF Health News, HFMA, CMS Newsroom, NPR Health, STAT News

### New York (2)
The City (NYC), Gothamist

### Connecticut (4)
CT Mirror Health, CT OHS News, CT News Junkie, CT Examiner

### New Jersey (3)
NJ Spotlight News, New Jersey Monitor, ROI-NJ Healthcare

### Policy, regulatory & trade (2 RSS + 1 scraped)
Health Affairs Journal, PYMNTS Healthcare, AHA News Insurance (scraped)

## Major Providers Tracked

### New York
NewYork-Presbyterian, Mount Sinai, NYU Langone, Northwell, Montefiore, MSK, NYC H+H, Maimonides, Catholic Health LI

### Connecticut
Yale New Haven Health (11 hospitals), Hartford HealthCare (10), Nuvance (7), Trinity Health of NE, Stamford Health, Middlesex Health

### New Jersey
RWJBarnabas (16 hospitals), Hackensack Meridian (16), Atlantic Health (8), Virtua (5), Valley Health, Cooper University, St. Joseph's, Englewood Health

## Payer Perspective Inference

The system generates strategic perspectives for three major payers using detailed context prompts:

- **UnitedHealthcare**: Encodes Oxford/NYC small-group dominance, MA member loss projections, NYP dispute, Optum vertical integration, CMS rate squeeze
- **Anthem/Empire BCBS**: Encodes Mount Sinai dispute lessons, Blue Cross cross-licensing complexity, VBC push, claims review as negotiation lever
- **Cigna/Evernorth**: Encodes employer-market positioning, Evernorth vertical integration, narrow network strategy, competitive differentiation from UHC/Anthem

## State Regulatory Context

Each state's regulatory environment is encoded in the knowledge base:

- **NY**: Community rating, network adequacy (DFS), any willing provider, Managed Care Model Contract, Essential Plan, MCO Provider Tax
- **CT**: OHS cost growth benchmarks, Certificate of Need, antitrust enforcement (Hartford HealthCare case), All-Payer Claims Database
- **NJ**: Out-of-Network Consumer Protection Act, Horizon BCBS dominance, FTC antitrust activity (HMH-Englewood block), charity care requirements

## Project Structure

```
healthcare-monitor/
├── pyproject.toml          # uv/pip dependencies
├── app/
│   ├── __init__.py
│   ├── dashboard.py        # Streamlit UI (main entry)
│   ├── main.py             # CLI entry point
│   ├── knowledge.py        # Providers, payers, regulations, sources, prompts
│   ├── fetcher.py          # RSS + scrape + keyword filtering
│   ├── analyzer.py         # Ollama analysis + payer inference
│   └── persistence.py      # Dedup database
└── data/                   # Created at runtime
    ├── seen_articles.json
    ├── monitor.log
    └── reports/
```

## Customizing

- **Add sources**: Edit `RSS_FEEDS` or `SCRAPE_SOURCES` in `knowledge.py`
- **Add providers/payers**: Edit the `PROVIDERS` / `PAYERS` dicts
- **Add a payer perspective**: Add an entry to `PAYER_INFERENCE_PROMPTS` with context about that payer
- **Change model**: Set `OLLAMA_MODEL` in `knowledge.py` (larger models = better analysis)
- **Adjust sensitivity**: Lower `MIN_RELEVANCE_SCORE` to see more articles
