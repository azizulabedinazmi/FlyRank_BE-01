"""The storage contract. Routes in main.py only ever talk to an object with these methods.

Every storage engine (SQLite in A2, Postgres in A3) implements the same methods and returns the same
plain dicts, so the API on top can't tell which one it is using.
"""
from typing import Literal, Protocol

Task = dict  # {"id": int, "title": str, "done": bool}
Sort = Literal["id", "title"]

# Inserted only when the table is empty (first run).
SEED_TASKS = [
    ("Learn HTTP methods", True),
    ("Build a CRUD API", False),
    ("Push to GitHub", False),
]


class TaskRepository(Protocol):
    def init(self) -> None:
        """Create the table if it's missing, then seed it only if it's empty."""

    def ping(self) -> bool:
        """True if the database answers a trivial query."""

    def list(self, search: str | None = None, done: bool | None = None, sort: Sort = "id") -> list[Task]: ...

    def stats(self) -> dict: ...

    def get(self, task_id: int) -> Task | None: ...

    def create(self, title: str) -> Task: ...

    def update(self, task_id: int, title: str, done: bool) -> Task | None:
        """Overwrite both fields. None if the id doesn't exist."""

    def delete(self, task_id: int) -> bool:
        """True if a row was deleted, False if the id didn't exist."""

    def close(self) -> None: ...
