"""A2 storage: SQLite. Same SQL as before, moved out of main.py into one module."""
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from repository import SEED_TASKS, Sort, Task

# Column names can't be "?" parameters, so ORDER BY only ever uses one of these fixed strings.
ORDER_BY = {"id": "id", "title": "title COLLATE NOCASE, id"}


def escape_like(text: str) -> str:
    """Make % and _ in the user's search match literally instead of acting as wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def row_to_task(row: sqlite3.Row) -> Task:
    # SQLite stores booleans as 0/1; the API keeps sending real true/false.
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


class SqliteTaskRepository:
    def __init__(self, path: str | Path | None = None):
        # tasks.db sits next to this file. TASKS_DB lets tests point at a throwaway file.
        self.path = Path(path or os.environ.get("TASKS_DB", Path(__file__).parent / "tasks.db"))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row  # rows behave like dicts: row["title"]
        return conn

    def init(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT    NOT NULL,
                    done  INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks (done)")
            (count,) = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()
            if count == 0:
                conn.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)",
                                 [(t, int(d)) for t, d in SEED_TASKS])

    def ping(self) -> bool:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT 1").fetchone()[0] == 1

    def list(self, search: str | None = None, done: bool | None = None, sort: Sort = "id") -> list[Task]:
        sql = "SELECT id, title, done FROM tasks"
        where, params = [], []
        if search is not None:
            where.append("title LIKE ? ESCAPE '\\'")
            params.append(f"%{escape_like(search)}%")
        if done is not None:
            where.append("done = ?")
            params.append(int(done))
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY " + ORDER_BY[sort]
        with closing(self._connect()) as conn:
            return [row_to_task(r) for r in conn.execute(sql, params).fetchall()]

    def stats(self) -> dict:
        with closing(self._connect()) as conn:
            total, done = conn.execute("SELECT COUNT(*), COALESCE(SUM(done), 0) FROM tasks").fetchone()
        return {"total": total, "done": done, "open": total - done}

    def _get(self, conn: sqlite3.Connection, task_id: int) -> Task | None:
        row = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return row_to_task(row) if row else None

    def get(self, task_id: int) -> Task | None:
        with closing(self._connect()) as conn:
            return self._get(conn, task_id)

    def create(self, title: str) -> Task:
        with closing(self._connect()) as conn, conn:  # inner "conn" commits on success
            cur = conn.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title, 0))
            return self._get(conn, cur.lastrowid)  # the id comes from the database

    def update(self, task_id: int, title: str, done: bool) -> Task | None:
        with closing(self._connect()) as conn, conn:
            cur = conn.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (title, int(done), task_id))
            return self._get(conn, task_id) if cur.rowcount else None

    def delete(self, task_id: int) -> bool:
        with closing(self._connect()) as conn, conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cur.rowcount > 0

    def close(self) -> None:
        pass  # a connection is opened and closed per call
