<!-- 
# Save results to JSON file
uv run python app/scrapers/test_scrapers.py all --save -->


### For the Docker Phase 1 Step 1
Created a `.env` file inside the `docker/` folder to store the Postgres DB name, user, password, and port, since Docker Compose reads variables from the project directory by default.

Because the default port was already in use,  changed the host port mapping to a free port.
Then I started the Postgres container with Docker Compose, making sure required variables like `POSTGRES_PASSWORD` were set so the database could initialize properly. 

Finally, verified the setup by running a simple `SELECT now();` query using `psql` inside the container to confirm the DB is reachable and responding.

[1]: https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/?utm_source=chatgpt.com "Interpolation"
[2]: https://hub.docker.com/_/postgres?utm_source=chatgpt.com "postgres - Official Image"
[3]: https://www.datacamp.com/tutorial/postgresql-docker?utm_source=chatgpt.com "PostgreSQL in Docker: A Step-by-Step Guide for Beginners"


“Before we can send you a daily news email, we need a small storage box to keep the articles and summaries for a short time. We’re turning on that storage box (a database) on my laptop using Docker, which is like running a pre-built appliance. The healthcheck is just a ‘ready light’ that tells us the database is fully turned on before the app tries to use it.”

Simple analogy

Postgres = a filing cabinet for news items
Docker = a sealed appliance that contains the filing cabinet
Healthcheck = the green “ready” LED
select now() test = pressing the “self-test” button

### Phase 1 Step 2

In Step 2, I created three tables—`articles` to store every scraped link plus its extracted text later, `digests` to store each “run” (like the last 10 hours), and `digest_items` to connect a digest to the 10 chosen articles with their per-article summaries.
I added “dedupe” by making `articles.url` unique so I never store the same link twice, which prevents repeated stories in the email. 
I created `database.py` so I have one shared place to build the SQLAlchemy Engine (meant to be created once per DB URL), create sessions, and run `create_all()` to create the tables from my models.
This file structure keeps “what my data looks like” (`models.py`) separate from “how I connect to the DB” (`database.py`), so extraction/ranking/summarization nodes can reuse the same DB layer cleanly. 
Example: if Google News returns `https://example.com/story` at 9:30 and again at 10:00, the unique URL rule blocks the duplicate, and I can safely fetch text once, summarize it, attach it to a digest, email it, and later delete anything older than 18 hours. 

[1]: https://www.postgresql.org/docs/current/ddl-constraints.html?utm_source=chatgpt.com "Documentation: 18: 5.5. Constraints"
[2]: https://docs.sqlalchemy.org/en/latest/core/connections.html?utm_source=chatgpt.com "Working with Engines and Connections"


### phase 1 Step 3
Step 3 takes the articles scrapers return and saves them into the `articles` table so later phases can extract text, rank, summarize, and email reliably.
We created the `articles` table to store one row per news story (title, source, URL, scraped time), and we made `url` UNIQUE so the database enforces “no duplicates.” ([PostgreSQL][1])
“Dedup” means if the same URL appears again (from another source or another run), we don’t create a second row; we update the existing row using Postgres UPSERT (`ON CONFLICT DO UPDATE`). ([PostgreSQL][1])
We also dedupe the batch *before* inserting because the same URL can appear twice in one scrape run, and a single INSERT can’t update the same target row twice.
`database.py` exists so every part of the app uses one consistent DB connection/session setup (scrapers, LangGraph nodes, cleanup). ([Database Administrators Stack Exchange][2])
Example: Google News returns URL=A, TechBlogs also returns URL=A; batch-dedupe keeps one, and UPSERT ensures only one DB row exists for A. ([PostgreSQL][1])
Non-tech explanation: “We save all news links in a small database and keep only one copy of each link so you don’t get repeated stories in your email.”
This step is the “foundation” because everything next reads from the DB: extraction fills `content_text`, ranking picks top items, LLM writes summaries, and retention deletes old rows.

[1]: https://www.postgresql.org/docs/current/sql-insert.html?utm_source=chatgpt.com "Documentation: 18: INSERT"
[2]: https://dba.stackexchange.com/questions/315039/insert-on-conflict-do-update-set-an-upsert-statement-with-a-unique-constraint?utm_source=chatgpt.com "INSERT ON CONFLICT DO UPDATE SET (an UPSERT) ..."
