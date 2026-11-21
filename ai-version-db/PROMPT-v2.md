# Prompt v2 (rematch)

Prompt v1 plus the things v1 got wrong or decided for me. Sent with the same Week 2 in-memory `main.py`.

```text
Here is my to-do list API in Python/FastAPI (main.py attached). Right now it keeps the tasks in a
Python list in memory, so everything is lost when the server restarts.

Move the storage to a SQLite database so the data survives restarts.

Database
- Use Python's built-in sqlite3 module. No ORM, no extra packages.
- The database file is tasks.db, stored next to main.py (not in whatever folder the server was
  started from). If the environment variable TASKS_DB is set, use that path instead, so tests can
  use a throwaway file.
- One table, created with CREATE TABLE IF NOT EXISTS:
    id    INTEGER PRIMARY KEY AUTOINCREMENT  -- ids are never reused, even after the newest task is deleted
    title TEXT NOT NULL
    done  INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))  -- SQLite has no real boolean type
- On startup: create the table if it's missing, then insert the 3 example tasks only if the table
  is empty. Do the count and the inserts in one transaction so the seed is all-or-nothing.
- Open a connection per request and always close it (also on errors), so the file is never left
  locked on Windows.

API (must not change at all)
- Same URLs, request bodies, response bodies, error messages and status codes as the attached
  main.py: 200/201/204 on success, 400 for invalid input, 404 for an unknown id, every error as
  {"error": "..."}.
- The API returns done as a JSON true/false, never 0/1.
- Return what is actually in the database after a write (read the row back), not a dict built in
  Python.

Safety
- Every value from the client goes in as a ? parameter. Never build SQL with f-strings or +.

Keep everything in one file, main.py.
```

**What changed from v1:** I spelled out the schema (AUTOINCREMENT, `CHECK (done IN (0, 1))`, `NOT NULL`),
where the file lives plus a `TASKS_DB` override, the transaction around the seed, closing connections,
and reading rows back after writes.
