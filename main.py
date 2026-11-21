import os
import sqlite3
from contextlib import asynccontextmanager, closing
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, StrictBool, StrictStr

# ---------------------------------------------------------------------------
# Storage layer: SQLite
# ---------------------------------------------------------------------------
# tasks.db sits next to this file. TASKS_DB lets tests point at a throwaway file.
DB_PATH = Path(os.environ.get("TASKS_DB", Path(__file__).parent / "tasks.db"))

SEED_TASKS = [
    ("Learn HTTP methods", 1),
    ("Build a CRUD API", 0),
    ("Push to GitHub", 0),
]


def get_db() -> sqlite3.Connection:
    """Open a connection. Connecting to a file that doesn't exist creates it."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["title"]
    return conn


def init_db():
    """Create the tasks table if it's missing, then seed it only if it's empty."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT    NOT NULL,
                done  INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
            )
            """
        )
        (count,) = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()
        if count == 0:
            conn.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", SEED_TASKS)
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Task API",
    version="2.0",
    description="A tiny to-do list API with full CRUD, stored in a SQLite database (tasks.db).",
    lifespan=lifespan,
)

# In-memory list: still serving the endpoints until Stage 1 moves reads to SQLite.
tasks = [
    {"id": 1, "title": "Learn HTTP methods", "done": True},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Push to GitHub", "done": False},
]


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
    # SQLite stores booleans as 0/1; the API keeps sending real true/false.
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def db_get_task(conn: sqlite3.Connection, task_id: int):
    row = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_task(row) if row else None


def find_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


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
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return [row_to_task(r) for r in rows]


@app.get("/tasks/{task_id}", summary="Get one task by id", response_model=Task, responses=ERR_404)
def get_task(task_id: int):
    with closing(get_db()) as conn:
        task = db_get_task(conn, task_id)
    if task is None:
        return not_found(task_id)
    return task


@app.post("/tasks", summary="Create a new task", status_code=201, response_model=Task, responses=ERR_400)
def create_task(body: TaskCreate):
    """Send `{"title": "..."}`. The server assigns the id and sets `done` to false."""
    if body.title is None or body.title.strip() == "":
        return bad_request("title is required and cannot be empty")
    next_id = max((t["id"] for t in tasks), default=0) + 1
    task = {"id": next_id, "title": body.title.strip(), "done": False}
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}", summary="Update a task's title and/or done", response_model=Task,
         responses={**ERR_400, **ERR_404})
def update_task(task_id: int, body: TaskUpdate):
    """Send `title`, `done`, or both. At least one is required."""
    task = find_task(task_id)
    if task is None:
        return not_found(task_id)
    if body.title is None and body.done is None:
        return bad_request("send at least one of: title, done")
    if body.title is not None and body.title.strip() == "":
        return bad_request("title cannot be empty")
    if body.title is not None:
        task["title"] = body.title.strip()
    if body.done is not None:
        task["done"] = body.done
    return task


@app.delete("/tasks/{task_id}", summary="Delete a task", status_code=204, responses=ERR_404)
def delete_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        return not_found(task_id)
    tasks.remove(task)
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
