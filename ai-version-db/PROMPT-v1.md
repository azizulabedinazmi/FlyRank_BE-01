# Prompt v1 (Week 3 AI rematch)

Written from memory, before looking at my own SQLite code again. Sent together with my Week 2
in-memory `main.py` (saved here as `start-main-inmemory.py`).

```text
Here is my to-do list API in Python/FastAPI (main.py attached). Right now it keeps the tasks in a
Python list in memory, so everything is lost when the server restarts.

Move the storage to a SQLite database so the data survives restarts.

- Use Python's built-in sqlite3 module. The database file is tasks.db.
- One table called tasks with columns id (integer primary key), title (text) and done (boolean).
- When the app starts, create the table if it doesn't exist, and insert the 3 example tasks
  only if the table is empty (so they don't get added again on every restart).
- Every endpoint must keep behaving exactly the same as now: same URLs, same request bodies,
  same responses, same status codes (200/201/204, 400 for invalid input, 404 for an unknown id).
- Use parameterized queries (?) everywhere, never build SQL strings from user input.
- Keep everything in one file, main.py.
```
