# AI News Summarizer

> An intelligent news digest system that automatically scrapes, extracts, ranks, summarizes, and delivers the top AI and tech news stories to your inbox.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16-blue.svg)](https://www.postgresql.org/)
[![LangChain](https://img.shields.io/badge/LangChain-latest-green.svg)](https://langchain.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-orange.svg)](https://openai.com/)

## Features

- **Automated News Scraping** - Collects articles from multiple sources (Times of India, TechCrunch, Anthropic, The Verge, Hacker News)
- **Smart Content Extraction** - Bypasses Cloudflare protection and extracts full article text with 75%+ success rate
- **Intelligent Selection** - Ranks and selects top 10 articles using diversity-aware algorithms
- **AI-Powered Summaries** - Generates concise one-liners and bullet points using OpenAI GPT-4o-mini
- **Email Delivery** - Sends HTML digests with plain text fallback
- **LangGraph Pipeline** - Unified workflow with checkpointing and observability
- **Automatic Cleanup** - Removes articles older than 18 hours to prevent database bloat
- **Robust Error Handling** - Exponential backoff, retry logic, and domain skiplists

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

### Prerequisites

- **Docker** and **Docker Compose** installed
- **Python 3.11+** with [`uv`](https://github.com/astral-sh/uv) package manager
- **OpenAI API key** ([Get one here](https://platform.openai.com/api-keys))
- **Gmail account** with App Password (for email sending)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/AI-News-summarizer.git
   cd AI-News-summarizer
   ```

2. **Set up environment variables**

   Create `.env` file in the project root:
   ```bash
   # OpenAI API
   OPENAI_API_KEY=your-openai-api-key

   # SMTP (Gmail example)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=465
   SMTP_USER=your-email@gmail.com
   SMTP_PASS=your-gmail-app-password
   FROM_EMAIL=your-email@gmail.com
   TO_EMAIL=recipient@example.com
   ```

   Create `docker/.env` for database credentials:
   ```bash
   POSTGRES_DB=newsdb
   POSTGRES_USER=news
   POSTGRES_PASSWORD=your-secure-password
   POSTGRES_PORT=5433
   ```

3. **Start the PostgreSQL database**
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

4. **Initialize the database**
   ```bash
   uv run python scripts/init_db.py
   ```

5. **Run the complete pipeline**
   ```bash
   # Scrape, extract, rank, summarize, and send digest for last 10 hours
   uv run python scripts/run_graph.py 10
   ```

That's it! You should receive a news digest email within a few minutes.

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI News Summarizer Pipeline                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. INGEST                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  TOI     │  │TechCrunch│  │ Anthropic│  │  HackerN │       │
│  │ Scraper  │  │   RSS    │  │   Blog   │  │   News   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       └─────────────┴─────────────┴──────────────┘             │
│                       │                                          │
│                       ▼                                          │
│              ┌────────────────┐                                 │
│              │   PostgreSQL   │  ← UPSERT with deduplication    │
│              │   (Articles)   │                                 │
│              └────────┬───────┘                                 │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. EXTRACT                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  For each article URL:                                   │   │
│  │  • Try Cloudscraper (Cloudflare bypass)                 │   │
│  │  • Fallback to requests with browser headers            │   │
│  │  • Extract text with Trafilatura                        │   │
│  │  • Retry with exponential backoff (max 3 attempts)      │   │
│  │  • Skip known-bad domains                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                       │                                          │
│                       ▼                                          │
│              ┌────────────────┐                                 │
│              │ Articles with  │                                 │
│              │  content_text  │                                 │
│              └────────┬───────┘                                 │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. SELECT                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Ranking Algorithm:                                      │   │
│  │  1. Score by: recency, keywords, source, length         │   │
│  │  2. Top 5 per source (avoid bias)                       │   │
│  │  3. Remove duplicate headlines                          │   │
│  │  4. Pick top 10 overall                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                       │                                          │
│                       ▼                                          │
│              ┌────────────────┐                                 │
│              │  Top 10 IDs    │                                 │
│              └────────┬───────┘                                 │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. SUMMARIZE                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  For each selected article:                             │   │
│  │  • Send title + content to OpenAI GPT-4o-mini           │   │
│  │  • Generate structured output:                          │   │
│  │    - one_liner: "One sentence summary"                  │   │
│  │    - bullets: ["Point 1", "Point 2", "Point 3"]         │   │
│  │  • Validate with Pydantic                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                       │                                          │
│                       ▼                                          │
│              ┌────────────────┐                                 │
│              │   Summaries    │                                 │
│              │  {id: summary} │                                 │
│              └────────┬───────┘                                 │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. PERSIST DIGEST                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • Create digest record (window_start, window_end)      │   │
│  │  • Link articles with summaries                         │   │
│  │  • Assign ranks (1-10)                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                       │                                          │
│                       ▼                                          │
│              ┌────────────────┐                                 │
│              │  Digest in DB  │                                 │
│              └────────┬───────┘                                 │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. EMAIL DELIVERY (not integrated in graph yet)                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • Render digest as HTML + plain text                   │   │
│  │  • Build multipart/alternative email                    │   │
│  │  • Send via SMTP (Gmail App Password)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                       │                                          │
│                       ▼                                          │
│              ┌────────────────┐                                 │
│              │  📧 Inbox      │                                 │
│              └────────┬───────┘                                 │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. CLEANUP                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • Delete articles older than 18 hours                  │   │
│  │  • Delete old digests and digest_items                  │   │
│  │  • Keep database lean                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### LangGraph Pipeline

The system uses LangGraph to orchestrate the workflow as a state machine:

```python
START → ingest → extract → select → summarize → persist_digest → cleanup → END
         ↓         ↓         ↓          ↓             ↓              ↓
      articles  content   top 10    summaries    digest_id    cleanup_stats
```

Each node receives the current state, performs its task, and returns updates. The state is checkpointed at each step for observability and debugging.

## How It Works

### 1. News Scraping (Ingest)

The system scrapes news from multiple sources:

- **Times of India** - Web scraping with category filtering (Technology, Business, Politics)
- **TechCrunch AI** - RSS feed for AI category
- **Anthropic Blog** - Web scraping with Cloudscraper
- **The Verge** - RSS feed for tech news
- **Hacker News** - Front page scraping
- **OpenAI Blog** - RSS feed

**Deduplication:**
- URLs are unique across sources
- If the same article appears from multiple sources, only one copy is stored
- Batch deduplication removes duplicates within a single scrape run
- Database UPSERT (`ON CONFLICT DO UPDATE`) handles duplicates across runs

### 2. Content Extraction

Extracts full article text from URLs:

**Cloudflare Bypass:**
- Detects Cloudflare-protected sites (Times of India, Anthropic, The Verge)
- Uses `cloudscraper` library to mimic Chrome browser

**Retry Logic:**
- Max 3 attempts per article
- Exponential backoff: 5 min → 30 min
- After 3 failures: mark as permanently failed

**Domain Skiplist:**
- Radio sites (wol.fm)
- Social media (twitter.com, reddit.com)
- Video content (youtube.com)
- Sites with 403 errors (retool.com)

**Success Rate:** ~75% overall (100% for major news sites)

### 3. Ranking & Selection

Selects top 10 articles using diversity-aware ranking:

**Scoring Factors:**
- **Recency** - Newer articles get higher scores
- **Keywords** - Boost for AI, ML, LLM, Claude, GPT, etc.
- **Source importance** - Prioritize quality sources
- **Content length** - Minimum threshold for quality

**Diversity Enforcement:**
- Top 5 per source (prevents source bias)
- Removes duplicate headlines (fuzzy matching)
- Ensures balanced coverage across topics

### 4. AI Summarization

Uses OpenAI GPT-4o-mini with structured output:

**Input:**
```
Title: [Article Title]
Content: [First 4000 chars of article]
```

**Output (Pydantic validated):**
```python
{
  "one_liner": "One sentence summary of the article",
  "bullets": [
    "Key point 1",
    "Key point 2",
    "Key point 3"
  ]
}
```

**Why Structured Output?**
- Guaranteed consistent format
- Type-safe with Pydantic validation
- No need for regex parsing

### 5. Email Delivery

Sends beautiful HTML emails with plain text fallback:

**HTML Version:**
- Clickable links to original articles
- Source attribution
- Clean, readable formatting

**Plain Text Version:**
- Fallback for older email clients
- Accessibility-friendly

**SMTP Configuration:**
- Gmail App Password recommended
- SSL/TLS encryption (port 465)
- Multipart/alternative format

### 6. Automatic Cleanup

Deletes data older than 18 hours:
- Prevents database bloat
- Removes stale articles
- Keeps only recent digests

## Project Structure

```
AI-News-summarizer/
│
├── app/
│   ├── scrapers/              # News scraping modules
│   │   ├── googlenews.py      # Google News RSS
│   │   ├── timesofindia.py    # Times of India web scraper
│   │   ├── techblogs.py       # Tech blog scrapers
│   │   └── run_scrapers.py    # Scraper orchestration
│   │
│   ├── services/              # Business logic
│   │   ├── articles_repo.py   # Article database operations
│   │   ├── extractor.py       # Content extraction
│   │   ├── extract_repo.py    # Extraction with retry logic
│   │   ├── ranker.py          # Article scoring
│   │   ├── select_repo.py     # Top-N selection
│   │   ├── summarizer.py      # LLM summarization
│   │   ├── digest_repo.py     # Digest database operations
│   │   ├── email_renderer.py  # Email formatting
│   │   ├── email_message_builder.py  # Email construction
│   │   ├── email_sender.py    # SMTP delivery
│   │   ├── cleanup_repo.py    # Data retention
│   │   └── database.py        # DB connection management
│   │
│   ├── graph/                 # LangGraph pipeline
│   │   ├── state.py           # State schema
│   │   └── build_graph.py     # Graph construction
│   │
│   └── db/
│       └── models.py          # SQLAlchemy models
│
├── scripts/                   # Utility scripts
│   ├── init_db.py             # Initialize database
│   ├── run_graph.py           # Run full pipeline
│   ├── ingest_once.py         # Scrape articles
│   ├── extract_once.py        # Extract content
│   ├── select_top.py          # Select top articles
│   ├── send_digest_email.py   # Send digest
│   ├── send_test_email.py     # Test SMTP
│   ├── preview_email.py       # Preview email
│   ├── cleanup_once.py        # Manual cleanup
│   └── debug_email_send.py    # SMTP debugging
│
├── docker/
│   ├── docker-compose.yml     # PostgreSQL container
│   └── .env                   # Database credentials
│
├── .env                       # API keys & SMTP config
├── README.md                  # This file
├── IMPLEMENTATION.md          # Detailed implementation guide
└── pyproject.toml             # Python dependencies
```

## Configuration

### Environment Variables

**Main `.env` file:**
```bash
# OpenAI API
OPENAI_API_KEY=sk-...

# Database (must match docker/.env)
DATABASE_URL=postgresql://news:password@localhost:5433/newsdb

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-gmail-app-password
FROM_EMAIL=your-email@gmail.com
TO_EMAIL=recipient@example.com
```

**`docker/.env` file:**
```bash
POSTGRES_DB=newsdb
POSTGRES_USER=news
POSTGRES_PASSWORD=your-secure-password
POSTGRES_PORT=5433
```

### Gmail App Password Setup

1. Enable 2-Step Verification on your Google Account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Use this password in `SMTP_PASS` (not your regular Gmail password)

## Usage

### Running the Complete Pipeline

```bash
# Run the full pipeline for last 10 hours
uv run python scripts/run_graph.py 10

# This will:
# 1. Scrape articles from all sources
# 2. Extract content with retry logic
# 3. Rank and select top 10
# 4. Generate AI summaries
# 5. Save digest to database
# 6. Clean up old data (18+ hours)
```

**Note:** Email sending is currently a separate step:
```bash
# After running the graph, send the digest:
uv run python scripts/send_digest_email.py <digest_id>
```

### Individual Commands

**Initialize Database:**
```bash
uv run python scripts/init_db.py
```

**Scrape Articles:**
```bash
# Scrape last 24 hours
uv run python scripts/ingest_once.py 24
```

**Extract Content:**
```bash
# Extract last 24 hours, batch size 80
uv run python scripts/extract_once.py 24 80
```

**Select Top Articles:**
```bash
# Select top 10 from last 10 hours
uv run python scripts/select_top.py 10
```

**Send Email:**
```bash
# Preview first (saves to .eml file)
uv run python scripts/preview_email.py <digest_id>

# Send to recipient
uv run python scripts/send_digest_email.py <digest_id>

# Debug SMTP issues
uv run python scripts/debug_email_send.py <digest_id>
```

**Cleanup:**
```bash
# Delete data older than 18 hours
uv run python scripts/cleanup_once.py
```

### Database Commands

**Check article counts:**
```bash
docker compose -f docker/docker-compose.yml exec db psql -U news -d newsdb -c \
  "SELECT COUNT(*) FROM articles;"
```

**View recent digests:**
```bash
docker compose -f docker/docker-compose.yml exec db psql -U news -d newsdb -c \
  "SELECT id, created_at, window_start, window_end FROM digests ORDER BY created_at DESC LIMIT 5;"
```

**Check extraction status:**
```bash
docker compose -f docker/docker-compose.yml exec db psql -U news -d newsdb -c \
  "SELECT extraction_status, COUNT(*) FROM articles GROUP BY extraction_status;"
```

## Development

### Prerequisites

```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Running Tests

```bash
# Test scrapers
uv run python app/scrapers/test_scrapers.py all

# Test extraction
uv run python scripts/analyze_extractions.py 24

# Test email (doesn't send)
uv run python scripts/preview_email.py <digest_id>

# Test SMTP (sends simple message)
uv run python scripts/send_test_email.py
```

### Adding New News Sources

1. Create scraper function in `app/scrapers/techblogs.py` or create new file
2. Register in `app/scrapers/run_scrapers.py`
3. Test with `uv run python app/scrapers/test_scrapers.py all --save`

Example:
```python
# app/scrapers/techblogs.py
def scrape_new_source(hours: int = 24) -> list[NewsItem]:
    # Fetch RSS feed or scrape website
    # Return list of NewsItem objects
    pass
```

### Database Migrations

```bash
# Add new columns (example)
uv run python scripts/migrate_add_new_columns.py

# Always backup before migrations!
docker compose -f docker/docker-compose.yml exec db pg_dump -U news newsdb > backup.sql
```

## Troubleshooting

### Email Not Arriving

**Symptoms:** SMTP shows success but email doesn't arrive

**Solutions:**
1. **Check spam/junk folder** - Most likely location
2. **Check Gmail Promotions tab** - Digest emails often go here
3. **Verify TO_EMAIL** - Ensure it's correct in `.env`
4. **Try different recipient** - Test with pure Gmail address
5. **Check SMTP debug logs:**
   ```bash
   uv run python scripts/debug_email_send.py <digest_id>
   ```
6. **Look for refused recipients:** Should show `refused: {}`

**For University/Enterprise Email:**
- Contact IT support if emails are blocked
- Check for additional spam filtering after Gmail

### Extraction Failing

**Symptoms:** Low extraction success rate (<50%)

**Solutions:**
1. **Check Cloudscraper installation:**
   ```bash
   uv add cloudscraper
   ```
2. **Verify domain isn't in skiplist** - Check `app/services/extractor.py`
3. **Increase retry attempts** - Edit `MAX_EXTRACTION_ATTEMPTS` in `app/services/extract_repo.py`
4. **Check extraction logs:**
   ```bash
   uv run python scripts/check_extraction_status.py
   ```

### Database Connection Issues

**Symptoms:** `psycopg2.OperationalError: connection refused`

**Solutions:**
1. **Ensure Docker is running:**
   ```bash
   docker compose -f docker/docker-compose.yml ps
   ```
2. **Check port mapping:**
   ```bash
   # Should show 0.0.0.0:5433->5432/tcp
   docker compose -f docker/docker-compose.yml ps
   ```
3. **Verify DATABASE_URL** matches `docker/.env`
4. **Restart containers:**
   ```bash
   docker compose -f docker/docker-compose.yml restart
   ```

### LangGraph Errors

**Symptoms:** `KeyError` in state, missing fields

**Solutions:**
1. **Check state schema** - Ensure all fields in `app/graph/state.py`
2. **Verify node returns** - Each node must return dict with expected keys
3. **Check checkpoints** - View full state after run

## Additional Documentation

- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** - Detailed implementation guide with all steps, challenges, and solutions
- **[API Documentation](https://platform.openai.com/docs)** - OpenAI API reference
- **[LangGraph Docs](https://docs.langchain.com/oss/python/langgraph)** - LangGraph documentation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **[LangChain](https://langchain.com/)** - For LangGraph orchestration framework
- **[OpenAI](https://openai.com/)** - For GPT-4o-mini API
- **[Trafilatura](https://trafilatura.readthedocs.io/)** - For article text extraction
- **[Cloudscraper](https://github.com/VeNoMouS/cloudscraper)** - For Cloudflare bypass

## Contact

For questions or feedback, please open an issue on GitHub.

---

Built with Claude Sonnet 4.5
