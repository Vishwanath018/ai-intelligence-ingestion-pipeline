# AI Intelligence Ingestion Pipeline

A Python project I built to collect and organize AI-related information from real-world sources.

The pipeline collects:

- AI Startups
- AI Products
- Research Papers
- AI Jobs
- AI News

The collected data is cleaned, validated, deduplicated, resolved, enriched and stored as structured JSON.

---

## System Architecture

```text
                    REAL-WORLD SOURCES
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
    STARTUPS           PRODUCTS           RESEARCH
        |                  |                  |
        +------------------+------------------+
                           |
                  +--------+--------+
                  |                 |
                  v                 v
                JOBS              NEWS
                  |                 |
                  +--------+--------+
                           |
                           v
                  DATA COLLECTION
                           |
                           v
                CLEANING & VALIDATION
                           |
                           v
                  ENTITY RESOLUTION
                           |
                           v
              GITHUB DISCOVERY / STARS
                           |
                           v
                    DATA UNIFICATION
                           |
                           v
                    OUTPUT MANAGER
                           |
                           v
                 STRUCTURED JSON DATA
```

### Main flow

```text
Sources
   ↓
Collectors
   ↓
Cleaning & Validation
   ↓
Entity Resolution
   ↓
GitHub Enrichment
   ↓
Unified Intelligence
   ↓
JSON Output
```

---

## Highlights

- Real-time and full ingestion modes
- Async collection using `asyncio` and `aiohttp`
- Data validation and deduplication
- Entity resolution with fuzzy matching
- GitHub repository and star discovery
- RSS fallback for news collection
- Unified JSON output
- 11 automated tests
- Full run tested with **4,493 real records**

---

## Tech Stack

**Python** · `asyncio` · `aiohttp` · BeautifulSoup · ArXiv · PyGithub · RapidFuzz · Pydantic · pytest

---

## Installation

```powershell
git clone https://github.com/Vishwanath018/ai-intelligence-ingestion-pipeline.git
cd ai-intelligence-ingestion-pipeline

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Create a `.env` file if API credentials are required.

---

## Run

### Live mode

```powershell
python -m src.main --mode live
```

### Full mode

```powershell
python -m src.main --mode full
```

### Tests

```powershell
pytest -q
```

Current result:

```text
11 passed
```

---

## Results

One full ingestion run produced:

| Source | Records |
|---|---:|
| Startups | 1,000 |
| Products | 1,000 |
| Research | 1,000 |
| Jobs | 1,000 |
| News | 493 |
| **Total** | **4,493** |

A live run successfully collected **25 records** across all five sources.

---

## Output

Results are stored in:

```text
data/output/
```

including:

```text
startups.json
products.json
research_papers.json
jobs.json
news.json
entity_mapping_log.json
unified_intelligence.json
```

---

## What I learned

This project helped me understand real-world data ingestion, asynchronous requests, API failures, validation, entity resolution, external API integration and automated testing.

The biggest lesson was that external data sources don't always behave reliably, so the pipeline needs to handle failures instead of assuming every request will succeed.

---

## Future Improvements

- Database storage
- Scheduled ingestion
- Dashboard
- Better entity resolution
- More data sources
- Monitoring

Built as a learning project to understand how a real-world AI data pipeline works.