import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, StrictBool, StrictStr

# The database file lives next to this file, not in the folder the server was started from.
# Set TASKS_DB to use a different file (e.g. a throwaway one for tests).
DB_PATH = os.environ.get("TASKS_DB") or str(Path(__file__).resolve().parent / "tasks.db")

SEED_TASKS = [
    ("Learn HTTP methods", 1),
    ("Build a CRUD API", 0),
    ("Push to GitHub", 0),
]


@contextmanager
def get_db():
    """Open a connection for one request and always close it, even on errors."""
    # isolation_level=None: autocommit, so we control transactions explicitly with BEGIN/COMMIT.
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done  INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
            )
            """
        )
        # Count + seed in one transaction so the seed is all-or-nothing.
        # IMMEDIATE takes the write lock up front, so two starting servers can't both seed.
        conn.execute("BEGIN IMMEDIATE")
        try:
            count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            if count == 0:
                conn.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", SEED_TASKS)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A tiny to-do list API with full CRUD. Data is stored in a SQLite database.",
    lifespan=lifespan,
)


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    title: StrictStr | None = Field(default=None, examples=["Buy milk"])


class TaskUpdate(BaseModel):
    title: StrictStr | None = Field(default=None, examples=["Buy oat milk"])
    done: StrictBool | None = Field(default=None, examples=[True])


class Error(BaseModel):
    error: str


ERR_400 = {400: {"model": Error, "description": "Invalid or empty body"}}
ERR_404 = {404: {"model": Error, "description": "Task not found"}}


def bad_request(message: str):
    return JSONResponse(status_code=400, content={"error": message})


def not_found(task_id: int):
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


def row_to_task(row: sqlite3.Row) -> dict:
    # SQLite stores done as 0/1; the API always returns a JSON true/false.
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def fetch_task(conn: sqlite3.Connection, task_id: int):
    row = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return None if row is None else row_to_task(row)


# FastAPI normally answers bad input with 422; this assignment wants 400 + {"error": ...}.
@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if isinstance(p, str) and p not in ("body", "path", "query"))
    return bad_request(f"Invalid {field or 'body'}: {first['msg']}")


@app.get("/", summary="Describe the API")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Check the server is alive")
def health():
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks", response_model=list[Task])
def list_tasks():
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return [row_to_task(r) for r in rows]


@app.get("/tasks/{task_id}", summary="Get one task by id", response_model=Task, responses=ERR_404)
def get_task(task_id: int):
    with get_db() as conn:
        task = fetch_task(conn, task_id)
    if task is None:
        return not_found(task_id)
    return task


@app.post("/tasks", summary="Create a new task", status_code=201, response_model=Task, responses=ERR_400)
def create_task(body: TaskCreate):
    """Send `{"title": "..."}`. The server assigns the id and sets `done` to false."""
    if body.title is None or body.title.strip() == "":
        return bad_request("title is required and cannot be empty")
    with get_db() as conn:
        cur = conn.execute("INSERT INTO tasks (title, done) VALUES (?, 0)", (body.title.strip(),))
        # Read the row back so the response reflects what is really stored.
        task = fetch_task(conn, cur.lastrowid)
    return task


@app.put("/tasks/{task_id}", summary="Update a task's title and/or done", response_model=Task,
         responses={**ERR_400, **ERR_404})
def update_task(task_id: int, body: TaskUpdate):
    """Send `title`, `done`, or both. At least one is required."""
    with get_db() as conn:
        if fetch_task(conn, task_id) is None:
            return not_found(task_id)
        if body.title is None and body.done is None:
            return bad_request("send at least one of: title, done")
        if body.title is not None and body.title.strip() == "":
            return bad_request("title cannot be empty")

        # Fixed SQL text; only the values come from the client, always as ? parameters.
        # COALESCE keeps the current value for any field that wasn't sent.
        title = body.title.strip() if body.title is not None else None
        done = int(body.done) if body.done is not None else None
        cur = conn.execute(
            "UPDATE tasks SET title = COALESCE(?, title), done = COALESCE(?, done) WHERE id = ?",
            (title, done, task_id),
        )
        if cur.rowcount == 0:  # deleted by another request in the meantime
            return not_found(task_id)
        task = fetch_task(conn, task_id)
    if task is None:
        return not_found(task_id)
    return task


@app.delete("/tasks/{task_id}", summary="Delete a task", status_code=204, responses=ERR_404)
def delete_task(task_id: int):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    if cur.rowcount == 0:
        return not_found(task_id)
    return Response(status_code=204)


# FastAPI's docs list a 422 response on every route, but our handler above returns 400 instead.
# Remove the 422 entries so Swagger UI shows only what the API really sends.
def custom_openapi():
    if app.openapi_schema is None:
        schema = FastAPI.openapi(app)
        for path in schema["paths"].values():
            for operation in path.values():
                operation.get("responses", {}).pop("422", None)
        app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
