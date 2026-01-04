<!-- 
# Save results to JSON file
uv run python app/scrapers/test_scrapers.py all --save -->


# For the Docker Step 1
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