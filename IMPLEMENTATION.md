# Implementation Guide - AI News Summarizer

This document provides a detailed walkthrough of how the AI News Summarizer was built, including all the steps taken, challenges encountered, solutions implemented, and references used.

## Table of Contents

1. [Phase 1: Foundation](#phase-1-foundation)
2. [Phase 2: Content Extraction](#phase-2-content-extraction)
3. [Phase 3: Ranking & Selection](#phase-3-ranking--selection)
4. [Phase 4: LangGraph Pipeline Integration](#phase-4-langgraph-pipeline-integration)
5. [Phase 5: Email Delivery & Cleanup](#phase-5-email-delivery--cleanup)
6. [Technical Challenges & Solutions](#technical-challenges--solutions)
7. [References & Resources](#references--resources)

---

## Phase 1: Foundation

### Step 1: Database Setup

**Objective:** Set up PostgreSQL in Docker with proper configuration and health checks.

**What was done:**
- Created a `.env` file in the `docker/` folder to store database credentials (name, user, password, port)
- Configured Docker Compose to run PostgreSQL with health checks
- Changed the default port mapping (5432 → 5433) to avoid conflicts
- Verified the database is accessible using `psql` with a test query (`SELECT now();`)

**Implementation Details:**

```yaml
# docker/docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "${POSTGRES_PORT:-5433}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Verification:**
```bash
docker compose -f docker/docker-compose.yml exec db psql -U news -d newsdb -c "SELECT now();"
```

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
   ```python
   id: int (PK)
   url: str (UNIQUE)
   title: str
   source: str
   category: str | None
   published_at: datetime | None
   scraped_at: datetime
   content_text: str | None
   extraction_status: str | None
   extraction_attempts: int (default: 0)
   next_extract_at: datetime | None
   importance_score: float | None
   reason_selected: str | None
   ```

2. **`digests`** - Stores each digest run (e.g., "last 10 hours")
   ```python
   id: int (PK)
   created_at: datetime
   window_start: datetime
   window_end: datetime
   overall_summary: str | None
   ```

3. **`digest_items`** - Links digests to selected articles with per-article summaries
   ```python
   id: int (PK)
   digest_id: int (FK → digests.id)
   article_id: int (FK → articles.id)
   rank: int
   item_summary: str
   ```

**Why Deduplication Matters:**
- Made `articles.url` UNIQUE to prevent storing the same link twice
- If Google News and TechBlogs both return the same article, only one row is stored
- Example: If `https://example.com/story` appears at 9:30 AM and again at 10:00 AM, the UNIQUE constraint blocks the duplicate

**File Structure:**
- **`app/db/models.py`** - Defines what the data looks like (SQLAlchemy models)
- **`app/services/database.py`** - Handles how to connect to the DB (Engine, sessions, `create_all()`)
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

**Implementation:**

```python
# app/services/articles_repo.py
def upsert_articles(items: list[NewsItem]) -> list[int]:
    # Batch dedupe: keep first occurrence of each URL
    seen = set()
    unique = []
    for item in items:
        if item.url not in seen:
            seen.add(item.url)
            unique.append(item)

    # UPSERT to database
    stmt = insert(Article).values([...]).on_conflict_do_update(
        index_elements=['url'],
        set_={'title': ..., 'scraped_at': ...}
    ).returning(Article.id)
```

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

**References:**
- [PostgreSQL INSERT with ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html)
- [UPSERT with UNIQUE Constraints](https://dba.stackexchange.com/questions/315039/)

---

## Phase 2: Content Extraction

**Objective:** Extract full article text from URLs with robust error handling.

**Status:** Successfully extracting ~75% of articles from enabled sources.

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

### Implementation Details

```python
# app/services/extractor.py
def extract_article_text(url: str, max_retries: int = 3) -> tuple[str | None, str]:
    domain = urlparse(url).netloc

    for attempt in range(max_retries):
        # Try cloudscraper for Cloudflare sites or as last resort
        if domain in CLOUDFLARE_PROTECTED_DOMAINS or attempt == max_retries - 1:
            html = fetch_with_cloudscraper(url)
        else:
            html = fetch_with_requests(url)

        if html:
            text = trafilatura.extract(html)
            if text:
                return text, "ok"

        time.sleep(2 ** attempt)  # Exponential backoff

    return None, "Extraction failed"
```

### Key Features

- **Cloudscraper integration** for Cloudflare bypass
- **Browser-like headers** to avoid bot detection
- **Retry mechanism** with exponential backoff (3 attempts)
- **Detailed logging** of every extraction attempt
- **Domain-level analytics** for success/failure tracking
- **Skiplist** for domains that always fail (radio sites, minimal blogs, etc.)

### Domain Skiplist

```python
SKIP_DOMAINS = {
    "wol.fm",              # Radio/audio content
    "twitter.com", "x.com", # Social media
    "youtube.com",         # Video content
    "reddit.com",          # Forum content
    "retool.com",          # 403 forbidden
    "bostondynamics.com",  # JS-heavy, trafilatura fails
    "donotnotify.com",     # Minimal HTML
    "minha.sh",            # Custom layout
    "ronjeffries.com",     # Minimal blog
    "www.thebignewsletter.com",  # Complex layout
}
```

### Commands

```bash
# Extract content from articles (last 24 hours, batch size 80)
uv run python scripts/extract_once.py 24 80

# Analyze extraction success/failure rates
uv run python scripts/analyze_extractions.py 24

# Check extracted content in database
uv run python scripts/check_db_content.py 24
```

---

## Phase 3: Ranking & Selection

**Objective:** Score and select top 10 articles for summarization using diversity-aware ranking.

### Approach: Diversity-Aware Re-Ranking

After extraction, we need to select which articles are worth summarizing and emailing. The approach:

1. **Scoring** - Score each article using simple signals:
   - Recency (newer = higher score)
   - Keyword boosts (AI, ML, LLM, Claude, GPT, etc.)
   - Source importance
   - Content length (minimum threshold)

2. **Top-N per Source** - Shortlist Top 5 articles per source to avoid source bias
   - Prevents "all Times of India" or "all Hacker News" digests
   - Ensures diversity across sources

3. **Deduplication** - Remove near-identical headlines using similarity matching
   - Compare titles using fuzzy matching
   - Remove duplicates that are >80% similar

4. **Final Top 10** - Select final 10 articles based on combined score
   - Sort by importance score
   - Pick top 10 for summarization

### Implementation

```python
# app/services/select_repo.py
def pick_and_mark(hours: int, per_source: int = 5, final_n: int = 10) -> list[int]:
    # 1. Fetch successfully extracted articles
    articles = fetch_articles_with_content(hours)

    # 2. Score each article
    for article in articles:
        article.importance_score = calculate_score(article)

    # 3. Top N per source
    shortlist = []
    by_source = group_by_source(articles)
    for source, articles in by_source.items():
        top = sorted(articles, key=lambda a: a.importance_score, reverse=True)[:per_source]
        shortlist.extend(top)

    # 4. Deduplicate similar titles
    unique = remove_duplicates(shortlist)

    # 5. Final top N
    final = sorted(unique, key=lambda a: a.importance_score, reverse=True)[:final_n]

    # 6. Mark as selected and save
    for rank, article in enumerate(final, start=1):
        article.reason_selected = f"Rank {rank}, Score: {article.importance_score:.2f}"

    save_to_database(final)
    return [a.id for a in final]
```

### Why This Approach?

**Problem:** Without selection, you'd either:
- (a) Send too many stories (overwhelming)
- (b) Waste LLM time summarizing low-value/duplicate items

**Solution:** Diversity-aware re-ranking
- First rank by relevance (recency, keywords, source)
- Then re-rank to avoid repetition and increase coverage
- Same approach used in search/recommendation systems

**Non-Technical Explanation:**
> "I collect many news links, then use simple rules to pick the 10 most important and recent stories, while making sure you get a balanced set from different sources and not 10 versions of the same headline. Then we summarize those 10 and email them."

### References
- [Diversity-Aware Ranking (OHARS)](https://ceur-ws.org/Vol-2758/OHARS-paper5.pdf)
- [Relevance vs Diversity in Ranking (ArXiv)](https://arxiv.org/pdf/2204.00539)

---

## Phase 4: LangGraph Pipeline Integration

### Step 6: Building the State Graph

**Objective:** Transform individual scripts into a unified workflow graph that manages state and enables observability.

**What Changed:**

Instead of running 4 separate scripts manually:
```bash
uv run python scripts/ingest_once.py 10
uv run python scripts/extract_once.py 10 80
uv run python scripts/select_top.py 10
uv run python scripts/send_digest_email.py <digest_id>
```

We now run a single command:
```bash
uv run python scripts/run_graph.py 10
```

**How It Works:**

1. **State Management** (`app/graph/state.py`)
   - Defines `NewsState` TypedDict with all pipeline data
   - State flows through the graph like a clipboard passed between workers
   - Each node reads current state and returns updates (patches)
   - Schema prevents typos and documents what data exists

2. **Graph Construction** (`app/graph/build_graph.py`)
   - Each pipeline step becomes a **node** (function)
   - **Edges** define execution order
   - `StateGraph(NewsState)` enforces type safety
   - `compile()` produces a runnable application

3. **Checkpointing & Persistence**
   - `InMemorySaver()` saves state snapshots at each step
   - Enables debugging: see exactly what happened at each node
   - Enables time-travel: replay or resume from any checkpoint
   - Grouped by `thread_id` for run isolation

**Graph Flow:**
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
cleanup_node (delete old data)
  ↓
END
```

Each node:
- Receives current state
- Performs its task
- Returns state updates (e.g., `{"article_ids": [1,2,3]}`)
- Graph merges updates automatically

**State Schema:**

```python
# app/graph/state.py
class NewsState(TypedDict, total=False):
    window_hours: int              # Input: time window in hours
    raw_count: int                 # Output from ingest_node
    article_ids: List[int]         # Output from ingest_node
    extracted_attempted: int       # Output from extract_node
    extraction_stats: Dict[str, int]  # Output from extract_node
    selected_ids: List[int]        # Output from select_node
    summaries: Dict[int, Dict[str, Any]]  # Output from summarize_node
    digest_id: int                 # Output from persist_digest_node
    cleanup_stats: Dict[str, Any]  # Output from cleanup_node
```

**Why This Matters:**

| Manual Scripts | LangGraph Pipeline |
|----------------|-------------------|
| Run 4-5 commands sequentially | Run 1 command |
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

### Step 7: LLM-Powered Summarization & Digest Generation

**Objective:** Add AI-powered summarization and persist digests to the database using OpenAI API with structured output.

**What We Built:**

#### 1. Summarization Service (`app/services/summarizer.py`)

Uses OpenAI's API with **structured output** to generate consistent summaries:

```python
class ArticleSummary(BaseModel):
    one_liner: str     # Single sentence summary
    bullets: list[str] # 3 key bullet points

def summarize(title: str, content: str) -> ArticleSummary:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    structured_llm = llm.with_structured_output(ArticleSummary)

    prompt = f"""
    Summarize this article in one sentence and 3 key bullet points:

    Title: {title}
    Content: {content[:4000]}
    """

    return structured_llm.invoke([HumanMessage(content=prompt)])
```

**Why Structured Output?**
- Guarantees consistent format (always 1 one-liner + 3 bullets)
- Type-safe: Pydantic validates the response
- No need to parse messy text with regex

**Implementation Details:**
- Model: `gpt-4o-mini` (fast and cost-effective)
- Temperature: 0.3 (consistent but not robotic)
- Input: Article title + full content text (truncated to 4000 chars)
- Output: Validated `ArticleSummary` object

**Error Handling:**
- Network failures: Automatic retry with exponential backoff
- Rate limits: Respects OpenAI rate limit headers
- Invalid responses: Pydantic validation catches schema mismatches
- Empty content: Gracefully handles articles with no text

#### 2. Digest Repository (`app/services/digest_repo.py`)

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
    articles = fetch_articles(state["selected_ids"])

    # Generate summaries using OpenAI
    summaries = {}
    for article in articles:
        summary = summarize(article.title, article.content_text or "")
        summaries[article.id] = summary.model_dump()

    return {"summaries": summaries}

def persist_digest_node(state):
    # Create new digest in DB
    digest_id = create_digest(state["window_hours"])

    # Link articles with their summaries
    items = []
    for rank, article_id in enumerate(state["selected_ids"], start=1):
        summary = state["summaries"][article_id]
        items.append((rank, article_id, format_summary(summary)))

    add_items(digest_id, items)
    return {"digest_id": digest_id}
```

---

## Phase 5: Email Delivery & Cleanup

### Step 8: Email Composition and Delivery

**Objective:** Compose and send email digests with proper HTML formatting and SMTP delivery.

#### 8.1 Email Rendering (`app/services/email_renderer.py`)

Converts digest data into two email bodies: plain text + HTML.

**Implementation:**

```python
def render_digest(digest_id: int) -> tuple[str, str, str]:
    # Fetch digest and items from database
    digest = get_digest(digest_id)
    items = get_digest_items(digest_id)

    # Generate subject
    subject = f"News Digest (Last 10 Hours) — Top {len(items)} — {timestamp}"

    # Generate text body
    text_lines = [subject, f"Window: {digest.window_start} → {digest.window_end}", ""]
    for rank, title, url, source, summary in items:
        text_lines.append(f"{rank}) {title} [{source}]")
        text_lines.append(summary)
        text_lines.append(url)
        text_lines.append("")
    text_body = "\n".join(text_lines)

    # Generate HTML body
    html_parts = [
        f"<h2>{escape(subject)}</h2>",
        f"<p><em>Window: {escape(window)}</em></p>",
        "<h3>Top stories</h3><ol>"
    ]
    for rank, title, url, source, summary in items:
        html_parts.append(
            f'<li><a href="{escape(url)}">{escape(title)}</a> '
            f'<small>[{escape(source)}]</small>'
            f'<div style="margin-top:6px">{escape(summary).replace(chr(10), "<br>")}</div>'
            '</li>'
        )
    html_parts.append("</ol>")
    html_body = "\n".join(html_parts)

    return subject, text_body, html_body
```

**Why Two Bodies?**
- Modern email clients display HTML (rich formatting, clickable links)
- Older clients or accessibility tools fall back to plain text
- Standard practice for professional emails

#### 8.2 Email Message Builder (`app/services/email_message_builder.py`)

Creates a proper multipart/alternative email message:

```python
def build_email_message(subject: str, text_body: str, html_body: str,
                       from_email: str, to_email: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    # Add headers to improve deliverability
    msg["X-Mailer"] = "AI-News-Summarizer"
    msg["List-Unsubscribe"] = f"<mailto:{from_email}?subject=unsubscribe>"

    # Set text body
    msg.set_content(text_body)

    # Add HTML alternative
    msg.add_alternative(html_body, subtype="html")

    return msg
```

**Deliverability Headers:**
- `X-Mailer`: Identifies the sending application
- `List-Unsubscribe`: Provides unsubscribe mechanism (reduces spam score)

#### 8.3 SMTP Sender (`app/services/email_sender.py`)

Sends the email via SMTP:

```python
def send_email(msg: EmailMessage) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASS"]

    if port == 465:
        # SSL/TLS (Gmail default)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(user, pwd)
            refused = server.send_message(msg)
            print("refused:", refused)
    else:
        # STARTTLS (commonly 587)
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(user, pwd)
            refused = server.send_message(msg)
            print("refused:", refused)
```

**SMTP Configuration:**
- **Gmail**: Use App Password (requires 2-Step Verification)
- **Port 465**: SSL/TLS (encrypted from start)
- **Port 587**: STARTTLS (upgrade to encryption)

**Environment Variables:**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
FROM_EMAIL=your-email@gmail.com
TO_EMAIL=recipient@example.com
```

#### 8.4 Testing Email Delivery

**Preview Email (without sending):**
```bash
uv run python scripts/preview_email.py <digest_id>
```

This saves a `.eml` file that can be opened locally to preview formatting.

**Send Test Email:**
```bash
uv run python scripts/send_test_email.py
```

Sends a simple "hello" email to verify SMTP credentials.

**Send Digest Email:**
```bash
uv run python scripts/send_digest_email.py <digest_id>
```

Sends the full digest with all articles and summaries.

**Debug Email Sending:**
```bash
uv run python scripts/debug_email_send.py <digest_id>
```

Enables SMTP debug logging to see full server communication.

---

### Step 9: Cleanup & Data Retention

**Objective:** Delete old articles and digests to prevent database bloat.

#### Implementation (`app/services/cleanup_repo.py`)

```python
def cleanup_older_than(hours: int = 18) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with SessionLocal() as s:
        # Delete digest_items via joining digests cutoff
        dig_ids = s.execute(
            delete(DigestItem).where(
                DigestItem.digest_id.in_(
                    select(Digest.id).where(Digest.created_at < cutoff)
                )
            )
        )
        d_items = dig_ids.rowcount or 0

        # Delete old digests
        d_dig = s.execute(
            delete(Digest).where(Digest.created_at < cutoff)
        ).rowcount or 0

        # Delete old articles
        d_art = s.execute(
            delete(Article).where(Article.scraped_at < cutoff)
        ).rowcount or 0

        s.commit()
        return {
            "cutoff": cutoff.isoformat(),
            "deleted_digest_items": d_items,
            "deleted_digests": d_dig,
            "deleted_articles": d_art
        }
```

**Why 18 Hours?**
- Digests are sent for "last 10 hours" of news
- Keeping 18 hours allows overlap for late-running jobs
- Prevents database from growing indefinitely
- Old news is no longer relevant

**Integration with Graph:**

Added as final node in the pipeline:
```python
def cleanup_node(state):
    result = cleanup_older_than(hours=18)
    return {"cleanup_stats": result}

# Graph flow: ... → persist_digest → cleanup → END
```

**Manual Cleanup:**
```bash
uv run python scripts/cleanup_once.py
```

**Test Cleanup:**
```bash
# Check counts before
docker compose -f docker/docker-compose.yml exec db psql -U news -d newsdb -c "SELECT COUNT(*) FROM articles;"

# Run cleanup
uv run python scripts/cleanup_once.py

# Check counts after
docker compose -f docker/docker-compose.yml exec db psql -U news -d newsdb -c "SELECT COUNT(*) FROM articles;"
```

---

## Technical Challenges & Solutions

### Challenge 1: Infinite Extraction Retry Loop

**Problem:** Articles failing extraction were retried infinitely, spamming logs:
```
✗ Failed: Trafilatura extraction failed for wol.fm
✗ Failed: Trafilatura extraction failed for wol.fm
✗ Failed: Trafilatura extraction failed for wol.fm
... (forever)
```

**Solution:** Implemented retry logic with exponential backoff

**Changes Made:**
- Added columns: `extraction_attempts`, `next_extract_at`
- Max 3 attempts per article
- Backoff delays: 5 min → 30 min
- After 3 failures: permanently mark as `failed`

**Code:**
```python
# app/services/extract_repo.py
if text:
    article.content_text = text
    article.extraction_status = "ok"
    article.next_extract_at = None
    succeeded += 1
else:
    article.extraction_attempts += 1
    if article.extraction_attempts < MAX_EXTRACTION_ATTEMPTS:
        # Exponential backoff: 5 * (6 ^ attempt) minutes
        backoff_minutes = 5 * (6 ** (article.extraction_attempts - 1))
        article.next_extract_at = now + timedelta(minutes=backoff_minutes)
    else:
        # Permanently mark as failed
        article.extraction_status = "failed"
        article.next_extract_at = None
    failed += 1
```

**Migration:**
```bash
uv run python scripts/migrate_add_retry_columns.py
```

---

### Challenge 2: SQLAlchemy NULL Filtering Bug

**Problem:** Articles with NULL `extraction_status` were not being selected for extraction.

**Root Cause:**
```python
.where(Article.extraction_status != "skipped")
```

In SQL, `NULL != 'skipped'` evaluates to `NULL` (not `TRUE`), so all NULL rows were filtered out.

**Solution:**
```python
.where(
    or_(
        Article.extraction_status.is_(None),
        Article.extraction_status != "skipped"
    )
)
```

This explicitly includes NULL values.

**Impact:**
- **Before fix:** 0 articles extracted
- **After fix:** 84 articles extracted (75 succeeded)

---

### Challenge 3: Some Domains Always Fail

**Problem:** Certain domains always fail extraction (radio sites, minimal blogs, 403 errors).

**Solution:** Created domain skiplist

```python
SKIP_DOMAINS = {
    "wol.fm",              # Radio/audio content
    "bostondynamics.com",  # JS-heavy
    "retool.com",          # 403 forbidden
    "twitter.com", "x.com", # Social media
    "youtube.com",         # Video content
}
```

Articles from these domains are marked as `skipped` immediately without attempting extraction.

---

### Challenge 4: Cloudscraper Not Used as Fallback

**Problem:** Logs showed `method: requests` even for sites that need Cloudscraper.

**Solution:** Always try Cloudscraper on final retry attempt

```python
should_try_cloudscraper = (
    (domain in CLOUDFLARE_PROTECTED_DOMAINS and attempt == 0) or
    (attempt == max_retries - 1)  # Last resort fallback
)
```

---

### Challenge 5: Email Deliverability Issues

**Problem:** Digest emails not arriving at recipient inbox (even though SMTP accepted them).

**Root Cause:** University email servers (ASU) have additional spam filtering after Gmail accepts the email.

**Solutions Implemented:**

1. **Added deliverability headers:**
   ```python
   msg["X-Mailer"] = "AI-News-Summarizer"
   msg["List-Unsubscribe"] = f"<mailto:{from_email}?subject=unsubscribe>"
   ```

2. **Proper multipart/alternative format:**
   - Plain text body (required)
   - HTML alternative (optional but recommended)

3. **Debug tooling:**
   ```bash
   uv run python scripts/debug_email_send.py <digest_id>
   ```

**SMTP Response Analysis:**
```
250 2.0.0 OK  1768013220 6a1803df08f44-890770e472csm87423476d6.23 - gsmtp
```
- `250` = Success
- `2.0.0` = Message accepted
- Email was successfully delivered to Gmail's servers

**Recommendation:**
- Test with pure Gmail addresses first
- Check spam/promotions folders
- For enterprise emails, contact IT support if issues persist

---

### Challenge 6: Times of India Technology Section 404

**Problem:** URL `/business/india-business/tech` returned 404.

**Solution:** Updated to correct URL
```python
'technology': '/technology/tech-news'  # Fixed
```

---

### Challenge 7: Missing State Fields in LangGraph

**Error:**
```
KeyError: 'summaries'
During task with name 'persist_digest' and id '...'
```

**Solution:** Added missing fields to `NewsState` TypedDict
```python
summaries: Dict[int, Dict[str, Any]]
digest_id: int
cleanup_stats: Dict[str, Any]
```

---

## References & Resources

### Docker & Database
- [Docker Compose Environment Variables](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
- [PostgreSQL Official Docker Image](https://hub.docker.com/_/postgres)
- [PostgreSQL Constraints Documentation](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [PostgreSQL INSERT with ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html)
- [SQLAlchemy Engines and Connections](https://docs.sqlalchemy.org/en/latest/core/connections.html)
- [SQLAlchemy ORM Quickstart](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)

### Web Scraping & Extraction
- [Trafilatura Documentation](https://trafilatura.readthedocs.io/)
- [Cloudscraper GitHub](https://github.com/VeNoMouS/cloudscraper)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [RSS Feed Parsing with feedparser](https://pythonhosted.org/feedparser/)

### LangChain & LangGraph
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Time-Travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel)
- [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [LangChain OpenAI Integration](https://docs.langchain.com/oss/python/integrations/chat/openai)

### Email & SMTP
- [Python EmailMessage Documentation](https://docs.python.org/3/library/email.message.html)
- [Python Email Examples](https://docs.python.org/3/library/email.examples.html)
- [smtplib — SMTP Protocol Client](https://docs.python.org/3/library/smtplib.html)
- [Gmail App Passwords](https://support.google.com/mail/answer/185833)

### Algorithms & Best Practices
- [Diversity-Aware Ranking (OHARS)](https://ceur-ws.org/Vol-2758/OHARS-paper5.pdf)
- [Relevance vs Diversity in Ranking](https://arxiv.org/pdf/2204.00539)
- [Exponential Backoff Best Practices](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)

### API Documentation
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

## Lessons Learned

1. **Always handle NULL values explicitly in SQL queries** - Don't assume `!= "value"` will include NULL rows

2. **Implement retry logic from the start** - Prevents infinite loops and improves reliability

3. **Use domain skiplists for known failures** - Saves time and reduces noise in logs

4. **Structured output is superior to text parsing** - LangChain's structured output with Pydantic is type-safe and reliable

5. **Email deliverability is complex** - SMTP acceptance doesn't guarantee inbox delivery; test with multiple providers

6. **LangGraph provides excellent observability** - State snapshots make debugging much easier than manual scripts

7. **Separation of concerns is key** - Keep rendering, message building, and sending as separate functions

8. **Always preview emails before sending** - Save as .eml file to catch formatting issues early

9. **Database migrations should be scripted** - Don't manually ALTER tables; write migration scripts

10. **Use environment variables for credentials** - Never hardcode passwords or API keys
