# Prompt v1 (A3 AI rematch)

Sent to a fresh AI session (Claude, no access to the repo or my A3 code) together with my A2 SQLite `main.py`
(saved here as `start-main-sqlite.py`) and `requirements.txt` (fastapi, uvicorn).

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
```
