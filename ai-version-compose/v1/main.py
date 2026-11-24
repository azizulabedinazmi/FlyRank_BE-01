import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field, StrictBool, StrictStr

# ---------------------------------------------------------------------------
# Storage layer: PostgreSQL (psycopg 3 + a small connection pool)
# ---------------------------------------------------------------------------
# Connection settings come from the environment (docker-compose passes them in
# from .env). The password has no default on purpose: it must be provided.
CONNINFO = make_conninfo(
    host=os.environ.get("POSTGRES_HOST", "db"),
    port=os.environ.get("POSTGRES_PORT", "5432"),
    dbname=os.environ.get("POSTGRES_DB", "tasks"),
    user=os.environ.get("POSTGRES_USER", "tasks"),
    password=os.environ["POSTGRES_PASSWORD"],
)

SEED_TASKS = [
    ("Learn HTTP methods", True),
    ("Build a CRUD API", False),
    ("Push to GitHub", False),
]

# open=False: the pool is opened in lifespan, so importing this module never touches the DB.
pool = ConnectionPool(
    CONNINFO,
    min_size=1,
    max_size=10,
    open=False,
    kwargs={"row_factory": dict_row},  # rows come back as dicts: row["title"]
)


def init_db():
    """Create the tasks table if it's missing, then seed it only if it's empty."""
    with pool.connection() as conn:  # commits on success, rolls back on error
        # Serialize startup across several app processes so the seed can't run twice.
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (727001,))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id    SERIAL  PRIMARY KEY,
                title TEXT    NOT NULL,
                done  BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        # Index on done so GET /tasks?done=... and /stats don't scan every row.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks (done)")
        count = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
        if count == 0:
            # Same transaction as the COUNT: all three seed rows land, or none do.
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO tasks (title, done) VALUES (%s, %s)", SEED_TASKS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # wait=True blocks until a connection succeeds (or 60 s pass), which covers
    # the few seconds Postgres may still need after its container starts.
    pool.open(wait=True, timeout=60)
    init_db()
    yield
    pool.close()


app = FastAPI(
    title="Task API",
    version="2.0",
    description="A tiny to-do list API with full CRUD, stored in a PostgreSQL database.",
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


class Stats(BaseModel):
    total: int
    done: int
    open: int


class Error(BaseModel):
    error: str


ERR_400 = {400: {"model": Error, "description": "Invalid or empty body"}}
ERR_404 = {404: {"model": Error, "description": "Task not found"}}


def bad_request(message: str):
    return JSONResponse(status_code=400, content={"error": message})


def not_found(task_id: int):
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


def row_to_task(row: dict) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


# Postgres SERIAL is a 32-bit integer. Ids outside that range can't exist, so we
# answer 404 for them directly instead of letting the driver raise an error.
INT4_MIN, INT4_MAX = -(2**31), 2**31 - 1


def valid_id(task_id: int) -> bool:
    return INT4_MIN <= task_id <= INT4_MAX


def db_get_task(conn, task_id: int, for_update: bool = False):
    if not valid_id(task_id):
        return None
    sql = "SELECT id, title, done FROM tasks WHERE id = %s"
    if for_update:
        sql += " FOR UPDATE"  # lock the row until this transaction ends
    row = conn.execute(sql, (task_id,)).fetchone()
    return row_to_task(row) if row else None


# FastAPI normally answers bad input with 422; this assignment wants 400 + {"error": ...}.
@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if isinstance(p, str) and p not in ("body", "path", "query"))
    return bad_request(f"Invalid {field or 'body'}: {first['msg']}")


@app.get("/", summary="Describe the API")
def root():
    return {"name": "Task API", "version": "2.0", "endpoints": ["/tasks", "/stats"]}


@app.get("/health", summary="Check the server is alive")
def health():
    return {"status": "ok"}


# Column names can't be %s parameters, so ORDER BY only ever uses one of these fixed strings.
# LOWER(title) mirrors SQLite's COLLATE NOCASE (case-insensitive sort, ties broken by id).
ORDER_BY = {"id": "id", "title": "LOWER(title), id"}


def escape_like(text: str) -> str:
    """Make % and _ in the user's search match literally instead of acting as wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@app.get("/tasks", summary="List all tasks", response_model=list[Task], responses=ERR_400)
def list_tasks(search: str | None = None, done: bool | None = None, sort: Literal["id", "title"] = "id"):
    """Optional filters: `?search=milk` (title contains, case-insensitive), `?done=true|false`,
    `?sort=title`. With no query string this returns every task, ordered by id, as before."""
    sql = "SELECT id, title, done FROM tasks"
    where, params = [], []
    if search is not None:
        # ILIKE = case-insensitive LIKE (SQLite's LIKE was case-insensitive too).
        where.append("title ILIKE %s ESCAPE '\\'")
        params.append(f"%{escape_like(search)}%")
    if done is not None:
        where.append("done = %s")
        params.append(done)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + ORDER_BY[sort]
    with pool.connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_task(r) for r in rows]


@app.get("/stats", summary="Count tasks in SQL", response_model=Stats)
def stats():
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE done) AS done FROM tasks"
        ).fetchone()
    total, done = row["total"], row["done"]
    return {"total": total, "done": done, "open": total - done}


@app.get("/tasks/{task_id}", summary="Get one task by id", response_model=Task, responses=ERR_404)
def get_task(task_id: int):
    with pool.connection() as conn:
        task = db_get_task(conn, task_id)
    if task is None:
        return not_found(task_id)
    return task


@app.post("/tasks", summary="Create a new task", status_code=201, response_model=Task, responses=ERR_400)
def create_task(body: TaskCreate):
    """Send `{"title": "..."}`. The server assigns the id and sets `done` to false."""
    if body.title is None or body.title.strip() == "":
        return bad_request("title is required and cannot be empty")
    with pool.connection() as conn:  # commits on success
        row = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
            (body.title.strip(), False),
        ).fetchone()  # the id comes from the database
    return row_to_task(row)


@app.put("/tasks/{task_id}", summary="Update a task's title and/or done", response_model=Task,
         responses={**ERR_400, **ERR_404})
def update_task(task_id: int, body: TaskUpdate):
    """Send `title`, `done`, or both. At least one is required."""
    with pool.connection() as conn:
        task = db_get_task(conn, task_id, for_update=True)
        if task is None:
            return not_found(task_id)
        if body.title is None and body.done is None:
            return bad_request("send at least one of: title, done")
        if body.title is not None and body.title.strip() == "":
            return bad_request("title cannot be empty")
        # Keep the current value for any field the client didn't send.
        title = body.title.strip() if body.title is not None else task["title"]
        done = body.done if body.done is not None else task["done"]
        row = conn.execute(
            "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
            (title, done, task_id),
        ).fetchone()
    return row_to_task(row)


@app.delete("/tasks/{task_id}", summary="Delete a task", status_code=204, responses=ERR_404)
def delete_task(task_id: int):
    if not valid_id(task_id):
        return not_found(task_id)
    with pool.connection() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    if cur.rowcount == 0:  # no row had that id
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
