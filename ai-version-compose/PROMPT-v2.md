# Prompt v2 (A3 rematch)

v1 passed 22/23 but put the SQL straight into the routes, read five separate `POSTGRES_*` variables instead of one
connection string, couldn't run outside Docker, and its `/health` said "ok" with the database stopped. v2 adds those
requirements (marked NEW). Sent to a fresh AI session with the same two files.

```text
Here is my to-do list API (Python, FastAPI). It stores tasks in SQLite (main.py and requirements.txt attached).
I want to move it to PostgreSQL running in Docker, and start the app and the database together with one command.

- Use Postgres in Docker with the official postgres image, and psycopg 3 as the driver.
- Keep the same tasks table: id (serial primary key), title (text), done (boolean).
- On startup, create the table if it doesn't exist and insert the 3 example tasks only if the table is empty.
- All the endpoints (GET /tasks, GET /tasks/{id}, POST /tasks, PUT /tasks/{id}, DELETE /tasks/{id}, plus /, /health
  and /stats) must behave exactly the same as now: same URLs, bodies, responses and status codes.
- Use parameterized queries everywhere.
- The database password must come from a .env file, never hardcoded. Give me a .env.example too.
- Use a volume so the data survives restarts.
- Write a Dockerfile for the app and a docker-compose.yml so that `docker compose up` starts everything.

NEW:
- Put every line that talks to the database in ONE module (a repository class with methods like list, get, create,
  update, delete, stats). The routes in main.py call that class and contain no SQL, so switching storage engines
  later means changing only that module.
- The app connects with a single connection string, DATABASE_URL=postgresql://user:password@host:5432/dbname, read
  from the environment. Load .env with python-dotenv so I can also run `uvicorn main:app` on my machine against the
  database container. That means the database port 5432 must be published, and inside compose the app must reach
  the database by its service name, not localhost.
- The table and index must be created from a separate db/schema.sql file.
- /health must actually check the database (SELECT 1): 200 with {"status": "ok", "db": "ok"} when it works,
  503 with "db": "down" when it doesn't.
- Pin the postgres image to a major version that matches the volume path you mount.
```
