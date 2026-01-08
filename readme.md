# AI News Summarizer

An automated system that scrapes AI and tech news from multiple sources, stores articles in a database with deduplication, and prepares them for summarization and email digest delivery.

## Overview

This project collects recent news articles from various sources (Google News, Times of India, tech blogs like OpenAI, Anthropic, TechCrunch, etc.), stores them in a PostgreSQL database, and eliminates duplicates. The goal is to build a daily news digest system that extracts, ranks, summarizes, and emails the most relevant AI/tech news.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ with `uv` package manager

### Setup

1. **Start the PostgreSQL database:**
   ```bash
   cd docker
   docker-compose up -d
   ```

2. **Initialize the database:**
   ```bash
   uv run python scripts/init_db.py
   ```

3. **Run the complete pipeline:**
   ```bash
   # Step 1: Scrape articles from the last 10 hours
   uv run python -m scripts.ingest_once 10

   # Step 2: Extract content from scraped articles
   uv run python -m scripts.extract_once 10 80

   # Step 3: Check results
   uv run python -m scripts.analyze_extractions 10
   ```
## Project Structure

```
├── app/
│   ├── scrapers/           # News scraping modules
│   │   ├── googlenews.py   # Google News RSS scraper
│   │   ├── timesofindia.py # Times of India web scraper
│   │   └── techblogs.py    # Tech blog scrapers (OpenAI, Anthropic, etc.)
│   ├── db/
│   │   ├── models.py       # SQLAlchemy database models
│   │   └── database.py     # Database connection and session management
│   └── repositories/
│       └── articles_repo.py # Database operations for articles
├── scripts/
│   ├── run_scrapers.py     # Run all scrapers with time filter
│   ├── ingest_once.py      # Scrape and save to database
│   └── init_db.py          # Initialize database tables
└── docker/
    ├── docker-compose.yml  # PostgreSQL container setup
    └── .env                # Database credentials
```

## Phase 1: Foundation (Completed)

### Step 1: Database Setup
**Objective:** Set up PostgreSQL in Docker with proper configuration and health checks.

**What was done:**
- Created a `.env` file in the `docker/` folder to store database credentials (name, user, password, port)
- Configured Docker Compose to run PostgreSQL with health checks
- Changed the default port mapping (5432 → custom port) to avoid conflicts
- Verified the database is accessible using `psql` with a test query (`SELECT now();`)

**Analogy:**
- **Postgres** = a filing cabinet for news items
- **Docker** = a sealed appliance that contains the filing cabinet
- **Healthcheck** = the green "ready" LED
- **`SELECT now()` test** = pressing the "self-test" button

**References:**
- [Docker Compose Environment Variables](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
- [PostgreSQL Official Docker Image](https://hub.docker.com/_/postgres)

---

### Step 2: Database Schema Design
**Objective:** Design and create database tables for articles, digests, and their relationships.

**Tables Created:**
1. **`articles`** - Stores scraped articles with unique URLs
   - `id`, `title`, `url` (UNIQUE), `source`, `category`, `scraped_at`, `content_text`, etc.
2. **`digests`** - Stores each digest run (e.g., "last 10 hours")
   - `id`, `created_at`, `summary`, etc.
3. **`digest_items`** - Links digests to selected articles with per-article summaries
   - `digest_id`, `article_id`, `summary`, `rank`

**Why Deduplication Matters:**
- Made `articles.url` UNIQUE to prevent storing the same link twice
- If Google News and TechBlogs both return the same article, only one row is stored
- Example: If `https://example.com/story` appears at 9:30 AM and again at 10:00 AM, the UNIQUE constraint blocks the duplicate

**File Structure:**
- **`models.py`** - Defines what the data looks like (SQLAlchemy models)
- **`database.py`** - Handles how to connect to the DB (Engine, sessions, `create_all()`)
- This separation keeps data models independent from connection logic

**References:**
- [PostgreSQL Constraints Documentation](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [SQLAlchemy Engines and Connections](https://docs.sqlalchemy.org/en/latest/core/connections.html)

---

### Step 3: Article Ingestion with Deduplication
**Objective:** Save scraped articles into the database while preventing duplicates.

**How It Works:**
1. Scrapers return a list of articles (title, URL, source, etc.)
2. **Batch deduplication** - Remove duplicate URLs within the same scrape run
3. **Database UPSERT** - Use PostgreSQL's `ON CONFLICT DO UPDATE` to handle duplicates
   - If the URL exists, update the existing row
   - If the URL is new, insert a new row

**Why We Need Both Deduplication Steps:**
- **Batch dedupe:** The same URL can appear twice in one scrape run (e.g., different categories)
- **UPSERT:** A URL scraped yesterday might appear again today from a different source
- Together they ensure only ONE row per unique URL in the database

**Example Flow:**
```
Google News returns URL=A, URL=B
TechBlogs returns URL=A, URL=C

→ Batch dedupe keeps: A (first occurrence), B, C
→ UPSERT ensures only one DB row exists for A
```

**Non-Technical Explanation:**
> "We save all news links in a small database and keep only one copy of each link so you don't get repeated stories in your email."

**Why This Is the Foundation:**
Everything next depends on this database:
- **Extraction** - Fills `content_text` for each article
- **Ranking** - Picks top articles from the database
- **Summarization** - Reads article text and generates summaries
- **Email Delivery** - Sends the final digest
- **Cleanup** - Deletes articles older than 18 hours

**References:**
- [PostgreSQL INSERT with ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html)
- [UPSERT with UNIQUE Constraints](https://dba.stackexchange.com/questions/315039/)

---

## Scrapers

### News Sources

#### Google News (`googlenews.py`)
- Fetches recent headlines across categories using RSS feeds
- Filters articles to the last N hours based on publish time
- Categories: Technology, Business, World, Science

#### Times of India (`timesofindia.py`)
- Scrapes Times of India sections via web scraping
- Filters by "time ago" text (e.g., "2 hours ago")
- Sections: India, World, Business, Tech

#### Tech Blogs (`techblogs.py`)
- **OpenAI** - News RSS feed (`https://openai.com/news/rss.xml`)
- **Anthropic** - Web scraping of news page
- **TechCrunch AI** - RSS feed for AI category
- **The Verge** - Tech news RSS feed
- **Hacker News** - Front page scraping

### Running Scrapers

```bash
# Test all scrapers (fetch last 24 hours)
uv run python app/scrapers/test_scrapers.py all

# Save results to JSON file
uv run python app/scrapers/test_scrapers.py all --save

# Fetch and save to database (last 10 hours)
uv run python scripts/ingest_once.py 10
```

---

## Database Schema

### Articles Table
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `url` | TEXT | Article URL (UNIQUE) |
| `title` | TEXT | Article headline |
| `source` | TEXT | Source name (e.g., "OpenAI", "Google News") |
| `category` | TEXT | Article category |
| `scraped_at` | TIMESTAMP | When the article was scraped |
| `content_text` | TEXT | Extracted article content (nullable) |

### Digests Table
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `created_at` | TIMESTAMP | Digest creation time |
| `summary` | TEXT | Overall digest summary (nullable) |

### Digest Items Table
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `digest_id` | INTEGER | Foreign key to digests |
| `article_id` | INTEGER | Foreign key to articles |
| `summary` | TEXT | Per-article summary |
| `rank` | INTEGER | Article ranking in digest |

---

## Phase 2: Content Extraction (Completed)

**Objective:** Extract full article text from URLs with robust error handling.

**Status:** **Working!** Successfully extracting ~75% of articles from enabled sources.

### Results

**Success Metrics:**
- **Overall Success Rate:** 73% (58 articles extracted from 79 scraped)
- **Times of India:** 100% success (25/25 articles)
- **Anthropic Blog:** 100% success (10/10 articles)
- **The Verge:** 100% success (10/10 articles)
- **TechCrunch:** 100% success (4/4 articles)
- **Hacker News Links:** ~60% success (9/16 articles)

### How It Works

**For Cloudflare-Protected Sites** (Times of India, Anthropic, The Verge, TechCrunch):
1. Detect Cloudflare protection
2. Use `cloudscraper` library to bypass protection (mimics Chrome browser)
3. Extract article text with Trafilatura
4. Save to database with `extraction_status = "ok"`

**For Standard Sites** (Hacker News links, BBC, GitHub, etc.):
1. Fetch HTML with browser-like headers
2. Extract article text with Trafilatura
3. Retry with exponential backoff if fails (3 attempts)
4. Save to database

### Quick Commands

```bash
# Analyze extraction success/failure rates
uv run python scripts/analyze_extractions.py 24

# Extract content from articles (last 24 hours, batch size 50)
uv run python scripts/extract_once.py 24 50

# Check extracted content in database
uv run python scripts/check_db_content.py 24
```

### Key Features
- Cloudscraper integration for Cloudflare bypass
- Browser-like headers to avoid bot detection
- Retry mechanism with exponential backoff (3 attempts)
- Detailed logging of every extraction attempt
- Domain-level success/failure analytics
- Google News scraper disabled (redirect URLs don't work)


## Phase 3: Ranking & Selection (Next)

**Objective:** Score and select top 10 articles for summarization using diversity-aware ranking.

### Approach: Diversity-Aware Re-Ranking

After extraction, we need to select which articles are worth summarizing and emailing. The approach:

1. **Scoring** - Score each article using simple signals:
   - Recency (newer = higher score)
   - Keyword boosts (AI, ML, LLM, etc.)
   - Source importance
   - Content length

2. **Classification** - Classify articles into topic buckets:
   - Technology
   - Finance/Business
   - World/Politics
   - Other

3. **Top-N per Source** - Shortlist Top 5 articles per source to avoid source bias

4. **Deduplication** - Remove near-identical headlines using similarity matching

5. **Topic Mix Enforcement** - Ensure balanced coverage:
   - Prevent "all tech" digests on heavy tech-news days
   - Balance: Tech + Finance + World
   - Backfill with best remaining if bucket is weak

6. **Final Top 10** - Select final 10 articles for summarization

### Why This Approach?

**Problem:** Without selection, you'd either:
- (a) Send too many stories (overwhelming)
- (b) Waste LLM time summarizing low-value/duplicate items

**Solution:** Diversity-aware re-ranking
- First rank by relevance (recency, keywords, source)
- Then re-rank to avoid repetition and increase topic coverage
- Same approach used in search/recommendation systems

**Non-Technical Explanation:**
> "I collect many news links, then use simple rules to pick the 10 most important and recent stories, while making sure you get a balanced set (some tech, some finance, some world news) and not 10 versions of the same headline. Then we summarize those 10 and email them."

### References
- [Diversity-Aware Ranking (OHARS)](https://ceur-ws.org/Vol-2758/OHARS-paper5.pdf)
- [Relevance vs Diversity in Ranking (ArXiv)](https://arxiv.org/pdf/2204.00539)

---

## Phase 4: LangGraph Pipeline Integration (Completed)

### Step 6: Building the State Graph

**Objective:** Transform individual scripts into a unified workflow graph that manages state and enables observability.

**What Changed:**
Instead of running 3 separate scripts manually:
```bash
uv run python scripts/ingest_once.py 10
uv run python scripts/extract_once.py 10 80
uv run python scripts/select_top.py 10
```

We now run a single command:
```bash
uv run python scripts/run_graph.py 10
```

**How It Works:**

1. **State Management** ([`app/graph/state.py`](app/graph/state.py))
   - Defines `NewsState` TypedDict with all pipeline data
   - State flows through the graph like a clipboard passed between workers
   - Each node reads current state and returns updates (patches)
   - Schema prevents typos and documents what data exists

2. **Graph Construction** ([`app/graph/build_graph.py`](app/graph/build_graph.py))
   - Each pipeline step becomes a **node** (function)
   - **Edges** define execution order (ingest → extract → select)
   - `StateGraph(NewsState)` enforces type safety
   - `compile()` produces a runnable application

3. **Checkpointing & Persistence**
   - `InMemorySaver()` saves state snapshots at each step
   - Enables debugging: see exactly what happened at each node
   - Enables time-travel: replay or resume from any checkpoint
   - Grouped by `thread_id` for run isolation

**Graph Flow:**
```
START → ingest_node → extract_node → select_node → END
         (scrape)      (extract)       (rank)
```

Each node:
- Receives current state
- Performs its task
- Returns state updates (e.g., `{"article_ids": [1,2,3]}`)
- Graph merges updates automatically

**Why This Matters:**

| Manual Scripts | LangGraph Pipeline |
|----------------|-------------------|
| Run 3 commands sequentially | Run 1 command |
| No visibility between steps | Full state snapshots |
| Hard to debug failures | See exactly where it failed |
| Can't resume | Can resume from checkpoint |
| No audit trail | Complete execution history |

**Analogy:**
> "Built an assembly line: the **graph** is the flowchart, the **state** is the clipboard that moves with each item, and **checkpoints** are saved progress so we don't restart from zero if something breaks."

**References:**
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Time-Travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel)

---

### Step 7: LLM-Powered Summarization & Digest Generation (Completed)

**Objective:** Add AI-powered summarization and persist digests to the database using OpenAI API with structured output.

**What We Built:**

#### 1. Summarization Service ([`app/services/summarizer.py`](app/services/summarizer.py))

Uses OpenAI's API with **structured output** to generate consistent summaries:

```python
class ArticleSummary(BaseModel):
    one_liner: str     # Single sentence summary
    bullets: list[str] # 3 key bullet points
```

**Why Structured Output?**
- Guarantees consistent format (always 1 one-liner + 3 bullets)
- Type-safe: Pydantic validates the response
- No need to parse messy text with regex

**Implementation Details:**
- Model: `gpt-4o-mini` (fast and cost-effective)
- Temperature: 0.3 (consistent but not robotic)
- Input: Article title + full content text
- Output: Validated `ArticleSummary` object

**Error Handling:**
- Network failures: Automatic retry with exponential backoff
- Rate limits: Respects OpenAI rate limit headers
- Invalid responses: Pydantic validation catches schema mismatches
- Empty content: Gracefully handles articles with no text

#### 2. Digest Repository ([`app/services/digest_repo.py`](app/services/digest_repo.py))

Manages digest creation and storage:

**Functions:**
- `create_digest(hours)` - Creates new digest record with time window
- `add_items(digest_id, items)` - Links articles to digest with summaries
- `fetch_articles(ids)` - Retrieves articles from database

**Database Schema:**
```sql
digests (id, window_start, window_end, created_at)
  ↓ (1-to-many)
digest_items (digest_id, article_id, rank, item_summary)
```

#### 3. Updated Graph Pipeline

**New Nodes:**
```python
def summarize_node(state):
    # Fetch selected articles from DB
    # Generate summaries using OpenAI
    # Return summaries dict: {article_id: summary}

def persist_digest_node(state):
    # Create new digest in DB
    # Link articles with their summaries
    # Return digest_id
```

**Complete Graph Flow:**
```
START
  ↓
ingest_node (scrape articles)
  ↓
extract_node (extract content with retry logic)
  ↓
select_node (rank & pick top 10)
  ↓
summarize_node (LLM generates summaries)
  ↓
persist_digest_node (save to database)
  ↓
END
```

**Updated State Schema:**
```python
class NewsState(TypedDict, total=False):
    window_hours: int
    article_ids: List[int]
    selected_ids: List[int]
    summaries: Dict[int, Dict[str, Any]]  # NEW
    digest_id: int                         # NEW
```

#### 4. Challenges & Solutions

**Challenge 1: Infinite Extraction Retry Loop**

 **Problem:** Articles failing extraction were retried infinitely, spamming logs:
```
✗ Failed: Trafilatura extraction failed for wol.fm
✗ Failed: Trafilatura extraction failed for wol.fm
✗ Failed: Trafilatura extraction failed for wol.fm
... (forever)
```

**Solution:** Implemented retry logic with exponential backoff
- Added columns: `extraction_attempts`, `next_extract_at`
- Max 3 attempts per article
- Backoff delays: 5 min → 30 min
- After 3 failures: permanently mark as `failed`

**Code Changes:**
```python
# app/services/extract_repo.py
if article.extraction_attempts < MAX_EXTRACTION_ATTEMPTS:
    backoff_minutes = 5 * (6 ** (article.extraction_attempts - 1))
    article.next_extract_at = now + timedelta(minutes=backoff_minutes)
else:
    article.extraction_status = "failed"  # Give up
```

**Challenge 2: Some Domains Always Fail**

 **Problem:** Certain domains (radio sites, minimal blogs, 403 errors) always fail extraction

**Solution:** Created domain skiplist
```python
SKIP_DOMAINS = {
    "wol.fm",           # Radio/audio content
    "bostondynamics.com", # JS-heavy
    "retool.com",       # 403 forbidden
    "twitter.com",      # Social media
}
```
Articles from these domains are marked as `skipped` immediately.

**Challenge 3: Cloudscraper Not Used as Fallback**

 **Problem:** Logs showed `method: requests` even for sites that need Cloudscraper

**Solution:** Always try Cloudscraper on final retry attempt
```python
should_try_cloudscraper = (
    (domain in CLOUDFLARE_PROTECTED_DOMAINS and attempt == 0) or
    (attempt == max_retries - 1)  # Last resort fallback
)
```

**Challenge 4: Missing State Fields**

 **Error:**
```
KeyError: 'summaries'
During task with name 'persist_digest' and id '...'
```

**Solution:** Added missing fields to `NewsState` TypedDict
```python
summaries: Dict[int, Dict[str, Any]]
digest_id: int
```

**Challenge 5: Times of India Technology 404**

 **Problem:** URL `/business/india-business/tech` returned 404

**Solution:** Updated to correct URL
```python
'technology': '/technology/tech-news'  # Fixed
```

#### 5. Final Results

**Example Graph Run:**
```bash
uv run python scripts/run_graph.py 10
```

**Output:**
```
✓ Scraped 84 articles (45 from TOI, 39 from Tech Blogs)
✓ Extracted content from 122 articles (38.9% success rate)
✓ Selected 10 top articles
✓ Generated 10 summaries via OpenAI
✓ Created digest #3 with all items

Final State:
{
  'window_hours': 10,
  'raw_count': 84,
  'article_ids': [910, 911, ...],
  'selected_ids': [119, 120, 125, ...],
  'summaries': {
    910: {
      'one_liner': 'AI-driven tech investments could trigger inflation...',
      'bullets': ['...', '...', '...']
    },
    ...
  },
  'digest_id': 3
}
```

**Database State:**
```sql
SELECT COUNT(*) FROM digests;        -- 3 digests created
SELECT COUNT(*) FROM digest_items;   -- 30 articles summarized (10 per digest)
SELECT COUNT(*) FROM articles WHERE extraction_status = 'ok';  -- 122 successful
```

#### 6. Monitoring & Maintenance

**Check Extraction Status:**
```bash
uv run python scripts/check_extraction_status.py
```

**Cleanup Failed Attempts:**
```bash
uv run python scripts/cleanup_and_migrate.py
```

**View Retry Queue:**
```sql
SELECT url, extraction_attempts, next_extract_at
FROM articles
WHERE next_extract_at IS NOT NULL
ORDER BY next_extract_at;
```

**References:**
- [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [LangChain OpenAI Integration](https://docs.langchain.com/oss/python/integrations/chat/openai)
- [SQLAlchemy ORM Quickstart](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Exponential Backoff Best Practices](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)

---

Step 8
**References:**
8.1
Concept: generate a multipart email that has plain text + HTML so every email client can render it (HTML if possible, text fallback). 
Implementation: read digests + digest_items from Postgres, build a subject like News Digest (Last 10 Hours) and a body where each item is: Title + Source + Link + 2–4 bullets.
https://docs.python.org/3/library/email.examples.html