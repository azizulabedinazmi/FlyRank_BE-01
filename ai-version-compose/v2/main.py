import os
from contextlib import asynccontextmanager
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, StrictBool, StrictStr

from repository import TaskRepository

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Reads .env when running "uvicorn main:app" on your machine. Variables already set in the
# environment (e.g. by docker compose) win over .env, because load_dotenv doesn't override.
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")

repo = TaskRepository(DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo.initialize()
    yield


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


class Health(BaseModel):
    status: str
    db: str


class Error(BaseModel):
    error: str


ERR_400 = {400: {"model": Error, "description": "Invalid or empty body"}}
ERR_404 = {404: {"model": Error, "description": "Task not found"}}
ERR_503 = {503: {"model": Health, "description": "Database unreachable"}}


def bad_request(message: str):
    return JSONResponse(status_code=400, content={"error": message})


def not_found(task_id: int):
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


# FastAPI normally answers bad input with 422; this assignment wants 400 + {"error": ...}.
@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if isinstance(p, str) and p not in ("body", "path", "query"))
    return bad_request(f"Invalid {field or 'body'}: {first['msg']}")


@app.get("/", summary="Describe the API")
def root():
    return {"name": "Task API", "version": "2.0", "endpoints": ["/tasks", "/stats"]}


@app.get("/health", summary="Check the server and the database are alive", response_model=Health,
         responses=ERR_503)
def health():
    if repo.ping():
        return {"status": "ok", "db": "ok"}
    return JSONResponse(status_code=503, content={"status": "error", "db": "down"})


@app.get("/tasks", summary="List all tasks", response_model=list[Task], responses=ERR_400)
def list_tasks(search: str | None = None, done: bool | None = None, sort: Literal["id", "title"] = "id"):
    """Optional filters: `?search=milk` (title contains, case-insensitive), `?done=true|false`,
    `?sort=title`. With no query string this returns every task, ordered by id, as before."""
    return repo.list(search=search, done=done, sort=sort)


@app.get("/stats", summary="Count tasks in SQL", response_model=Stats)
def stats():
    return repo.stats()


@app.get("/tasks/{task_id}", summary="Get one task by id", response_model=Task, responses=ERR_404)
def get_task(task_id: int):
    task = repo.get(task_id)
    if task is None:
        return not_found(task_id)
    return task


@app.post("/tasks", summary="Create a new task", status_code=201, response_model=Task, responses=ERR_400)
def create_task(body: TaskCreate):
    """Send `{"title": "..."}`. The server assigns the id and sets `done` to false."""
    if body.title is None or body.title.strip() == "":
        return bad_request("title is required and cannot be empty")
    return repo.create(body.title.strip())  # the id comes from the database


@app.put("/tasks/{task_id}", summary="Update a task's title and/or done", response_model=Task,
         responses={**ERR_400, **ERR_404})
def update_task(task_id: int, body: TaskUpdate):
    """Send `title`, `done`, or both. At least one is required."""
    task = repo.get(task_id)
    if task is None:
        return not_found(task_id)
    if body.title is None and body.done is None:
        return bad_request("send at least one of: title, done")
    if body.title is not None and body.title.strip() == "":
        return bad_request("title cannot be empty")
    # Keep the current value for any field the client didn't send.
    title = body.title.strip() if body.title is not None else task["title"]
    done = body.done if body.done is not None else task["done"]
    updated = repo.update(task_id, title, done)
    if updated is None:  # deleted by someone else between the read and the write
        return not_found(task_id)
    return updated


@app.delete("/tasks/{task_id}", summary="Delete a task", status_code=204, responses=ERR_404)
def delete_task(task_id: int):
    if not repo.delete(task_id):  # no row had that id
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
