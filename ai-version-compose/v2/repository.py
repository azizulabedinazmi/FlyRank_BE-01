"""Storage layer: every line that talks to the database lives in this module.

main.py only calls TaskRepository methods and never sees SQL, so moving to another
storage engine means rewriting this file and nothing else.
"""
from __future__ import annotations  # lets the "list" method coexist with list[...] annotations

import time
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

SCHEMA_PATH = Path(__file__).parent / "db" / "schema.sql"

SEED_TASKS = [
    ("Learn HTTP methods", True),
    ("Build a CRUD API", False),
    ("Push to GitHub", False),
]

# Column names can't be %s parameters, so ORDER BY only ever uses one of these fixed strings.
# lower(...) COLLATE "C" mirrors SQLite's "COLLATE NOCASE": case-insensitive, otherwise plain
# code-point order (not the locale-aware order Postgres would use by default).
ORDER_BY = {"id": "id", "title": 'lower(title) COLLATE "C", id'}

# Any fixed number works; it just has to be the same for every app process.
INIT_LOCK_ID = 727_001


def escape_like(text: str) -> str:
    """Make % and _ in the user's search match literally instead of acting as wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class TaskRepository:
    def __init__(self, database_url: str, connect_timeout: int = 5):
        self.database_url = database_url
        self.connect_timeout = connect_timeout

    def _connect(self, timeout: int | None = None) -> psycopg.Connection:
        # Used as "with self._connect() as conn:" -> commits on success, rolls back on error,
        # and closes the connection either way.
        return psycopg.connect(
            self.database_url,
            row_factory=dict_row,
            connect_timeout=timeout or self.connect_timeout,
        )

    # ------------------------------------------------------------------ setup

    def initialize(self, retries: int = 15, delay: float = 1.0) -> None:
        """Create the schema from db/schema.sql and seed the 3 example tasks if the table is empty.

        Retries for a short while so the app can start while the database is still booting.
        """
        for attempt in range(1, retries + 1):
            try:
                self._initialize_once()
                return
            except psycopg.OperationalError:
                if attempt == retries:
                    raise
                time.sleep(delay)

    def _initialize_once(self) -> None:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        with self._connect() as conn:
            # One transaction: lock, create, count, seed. The advisory lock stops two app
            # processes starting at once from both seeding the table.
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (INIT_LOCK_ID,))
            conn.execute(schema_sql)  # no parameters -> multiple statements are allowed
            count = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
            if count == 0:
                with conn.cursor() as cur:
                    cur.executemany("INSERT INTO tasks (title, done) VALUES (%s, %s)", SEED_TASKS)

    def ping(self) -> bool:
        """True if the database answers SELECT 1."""
        try:
            with self._connect(timeout=2) as conn:
                return conn.execute("SELECT 1 AS ok").fetchone()["ok"] == 1
        except psycopg.Error:
            return False

    # ------------------------------------------------------------------ queries

    def list(self, search: str | None = None, done: bool | None = None, sort: str = "id") -> list[dict]:
        sql = "SELECT id, title, done FROM tasks"
        where, params = [], []
        if search is not None:
            where.append("title ILIKE %s ESCAPE '\\'")
            params.append(f"%{escape_like(search)}%")
        if done is not None:
            where.append("done = %s")
            params.append(done)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY " + ORDER_BY[sort]  # KeyError on anything not whitelisted
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()

    def get(self, task_id: int) -> dict | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s", (task_id,)
            ).fetchone()

    def create(self, title: str) -> dict:
        with self._connect() as conn:
            return conn.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
                (title, False),
            ).fetchone()

    def update(self, task_id: int, title: str, done: bool) -> dict | None:
        """Returns the updated task, or None if no task has that id."""
        with self._connect() as conn:
            return conn.execute(
                "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
                (title, done, task_id),
            ).fetchone()

    def delete(self, task_id: int) -> bool:
        """Returns True if a task was deleted, False if no task had that id."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            return cur.rowcount > 0

    def stats(self) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE done) AS done FROM tasks"
            ).fetchone()
        total, done = row["total"], row["done"]
        return {"total": total, "done": done, "open": total - done}
