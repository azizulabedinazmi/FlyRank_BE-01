"""A3 storage: PostgreSQL (psycopg 3). Same methods and return shapes as sqlite_repository.py.

Every query is parameterized: values go in as %s placeholders and are sent separately from the SQL text.
"""
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from repository import SEED_TASKS

SCHEMA = Path(__file__).parent / "db" / "schema.sql"

# Any fixed number works; it just has to be the same for every app instance (see init()).
INIT_LOCK_ID = 4_2026_03


class PostgresTaskRepository:
    def __init__(self, database_url: str):
        # A small pool: connections are reused across requests instead of reconnecting every time.
        # open=False so importing main.py never touches the network; init() opens it.
        self.pool = ConnectionPool(database_url, min_size=1, max_size=5, open=False,
                                   kwargs={"row_factory": dict_row})

    def init(self) -> None:
        """Create the table if it's missing (db/schema.sql), then seed it only if it's empty."""
        self.pool.open(wait=True, timeout=30)
        with self.pool.connection() as conn:  # one transaction: commits on success, rolls back on error
            # Two app containers starting at once could both see an empty table and seed twice.
            # This lock makes the second one wait until the first has committed.
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (INIT_LOCK_ID,))
            conn.execute(SCHEMA.read_text(encoding="utf-8"))
            count = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
            if count == 0:
                with conn.cursor() as cur:
                    cur.executemany("INSERT INTO tasks (title, done) VALUES (%s, %s)", SEED_TASKS)

    def ping(self) -> bool:
        try:
            with self.pool.connection(timeout=2) as conn:
                return conn.execute("SELECT 1 AS ok").fetchone()["ok"] == 1
        except Exception:
            return False

    def close(self) -> None:
        self.pool.close()
