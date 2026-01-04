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
   uv run python scripts/ingest_once.py 10

   # Step 2: Extract content from scraped articles
   uv run python scripts/extract_once.py 10 80

   # Step 3: Check results
   uv run python scripts/analyze_extractions.py 10
   ```

### Testing & Daily Workflow

See **[TESTING_AND_WORKFLOW.md](TESTING_AND_WORKFLOW.md)** for:
- Complete testing guide
- Database verification commands
- Daily workflow options
- Troubleshooting common issues
- SQL queries for inspecting data

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

## Phase 2: Content Extraction ✅ (Completed)

**Objective:** Extract full article text from URLs with robust error handling.

**Status:** ✅ **Working!** Successfully extracting ~75% of articles from enabled sources.

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
- ✅ Cloudscraper integration for Cloudflare bypass
- ✅ Browser-like headers to avoid bot detection
- ✅ Retry mechanism with exponential backoff (3 attempts)
- ✅ Detailed logging of every extraction attempt
- ✅ Domain-level success/failure analytics
- ✅ Google News scraper disabled (redirect URLs don't work)

### Documentation
- 📘 [docs/EXTRACTION_STATUS_REPORT.md](docs/EXTRACTION_STATUS_REPORT.md) - Complete technical breakdown
- 📘 [docs/QUICK_STATUS.md](docs/QUICK_STATUS.md) - Visual summary
- 📘 [docs/EXTRACTION_FIXES.md](docs/EXTRACTION_FIXES.md) - Usage guide

---

## Next Steps

- **Phase 3: Ranking** - Score and select top articles for the digest
- **Phase 4: Summarization** - Use LLMs to generate article summaries
- **Phase 5: Email Delivery** - Send daily digest emails
- **Phase 6: Automation** - Schedule daily runs with cron/scheduler
- **Phase 7: Cleanup** - Delete articles older than 18 hours

---

## License

MIT
