"""To-do list REST API built with FastAPI.

Run with:  uvicorn main:app --reload
Swagger UI is served at /docs.
"""
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(
    title="To-Do List API",
    description="A simple in-memory to-do list REST API.",
    version="1.0.0",
)

# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    title: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


# --------------------------------------------------------------------------
# In-memory storage
# --------------------------------------------------------------------------

tasks: List[dict] = [
    {"id": 1, "title": "Learn FastAPI", "done": True},
    {"id": 2, "title": "Build a to-do API", "done": False},
    {"id": 3, "title": "Write some tests", "done": False},
]
next_id = 4  # ids are never reused, even after deletes


def find_task(task_id: int) -> dict:
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


def clean_title(title: Optional[str]) -> str:
    if title is None or not title.strip():
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")
    return title.strip()


# --------------------------------------------------------------------------
# Error handlers: always return JSON in the form {"error": "..."}
# --------------------------------------------------------------------------


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Malformed input (bad JSON, wrong types, non-numeric id) is a 400.
    errors: List[Any] = [
        {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request", "details": errors},
    )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@app.get("/")
def root():
    return {
        "name": "To-Do List API",
        "version": "1.0.0",
        "description": "A simple in-memory to-do list REST API.",
        "docs": "/docs",
        "endpoints": [
            "GET /health",
            "GET /tasks",
            "GET /tasks/{id}",
            "POST /tasks",
            "PUT /tasks/{id}",
            "DELETE /tasks/{id}",
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks", response_model=List[Task])
def list_tasks():
    return tasks


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    return find_task(task_id)


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate):
    global next_id
    task = {"id": next_id, "title": clean_title(payload.title), "done": False}
    next_id += 1
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    task = find_task(task_id)
    if "title" in payload.model_fields_set:
        task["title"] = clean_title(payload.title)
    if payload.done is not None:
        task["done"] = payload.done
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    task = find_task(task_id)
    tasks.remove(task)
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
