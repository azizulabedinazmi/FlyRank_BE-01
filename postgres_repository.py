"""A3 storage: PostgreSQL (psycopg 3). Same methods and return shapes as sqlite_repository.py.

Every query is parameterized: values go in as %s placeholders and are sent separately from the SQL text.
"""
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from repository import SEED_TASKS, Sort, Task

SCHEMA = Path(__file__).parent / "db" / "schema.sql"

# Column names can't be placeholders, so ORDER BY only ever uses one of these fixed strings.
ORDER_BY = {"id": "id", "title": "lower(title), id"}

BIGINT_MIN, BIGINT_MAX = -(2**63), 2**63 - 1


def fits_bigint(task_id: int) -> bool:
    """Python ints are unbounded; Postgres BIGINT isn't. An id outside the range can't exist, so it's a 404,
    not a 500 from the driver."""
    return BIGINT_MIN <= task_id <= BIGINT_MAX


def escape_like(text: str) -> str:
    """Make % and _ in the user's search match literally instead of acting as wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

# Any fixed number works; it just has to be the same for every app instance (see init()).
INIT_LOCK_ID = 4_2026_03


class PostgresTaskRepository:
    def __init__(self, database_url: str):
        # A small pool: connections are reused across requests instead of reconnecting every time.
        # open=False so importing main.py never touches the network; init() opens it.
        self.pool = ConnectionPool(database_url, min_size=1, max_size=5, open=False,
                                   kwargs={"row_factory": dict_row, "connect_timeout": 10})  # fail fast, never hang

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

    def list(self, search: str | None = None, done: bool | None = None, sort: Sort = "id") -> list[Task]:
        sql = "SELECT id, title, done FROM tasks"
        where, params = [], []
        if search is not None:
            where.append("title ILIKE %s ESCAPE '\\'")  # ILIKE = case-insensitive, like SQLite's LIKE
            params.append(f"%{escape_like(search)}%")
        if done is not None:
            where.append("done = %s")
            params.append(done)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY " + ORDER_BY[sort]  # fixed strings only, never from the request
        with self.pool.connection() as conn:
            return conn.execute(sql, params).fetchall()

    def stats(self) -> dict:
        with self.pool.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE done) AS done FROM tasks"
            ).fetchone()
        return {"total": row["total"], "done": row["done"], "open": row["total"] - row["done"]}

    def get(self, task_id: int) -> Task | None:
        if not fits_bigint(task_id):
            return None
        with self.pool.connection() as conn:
            return conn.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,)).fetchone()

    def create(self, title: str) -> Task:
        with self.pool.connection() as conn:
            # RETURNING hands back the row Postgres actually stored, id included.
            return conn.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done", (title, False)
            ).fetchone()

    def update(self, task_id: int, title: str, done: bool) -> Task | None:
        if not fits_bigint(task_id):
            return None
        with self.pool.connection() as conn:
            return conn.execute(
                "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
                (title, done, task_id),
            ).fetchone()  # None when no row had that id

    def delete(self, task_id: int) -> bool:
        if not fits_bigint(task_id):
            return False
        with self.pool.connection() as conn:
            return conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,)).rowcount > 0

    def ping(self) -> bool:
        try:
            with self.pool.connection(timeout=2) as conn:
                return conn.execute("SELECT 1 AS ok").fetchone()["ok"] == 1
        except Exception:
            return False

    def close(self) -> None:
        self.pool.close()
