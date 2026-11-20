from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, StrictBool, StrictStr

app = FastAPI(title="Task API", version="1.0")


class TaskCreate(BaseModel):
    title: StrictStr | None = None


class TaskUpdate(BaseModel):
    title: StrictStr | None = None
    done: StrictBool | None = None


# FastAPI normally answers bad input with 422; this assignment wants 400 + {"error": ...}.
@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if isinstance(p, str) and p not in ("body", "path", "query")) or "body"
    return JSONResponse(status_code=400, content={"error": f"Invalid {field}: {first['msg']}"})


def bad_request(message: str):
    return JSONResponse(status_code=400, content={"error": message})

# In-memory "database": lives only while the server runs.
tasks = [
    {"id": 1, "title": "Learn HTTP methods", "done": True},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Push to GitHub", "done": False},
]


def find_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


def not_found(task_id: int):
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        return not_found(task_id)
    return task


@app.post("/tasks", status_code=201)
def create_task(body: TaskCreate):
    if body.title is None or body.title.strip() == "":
        return bad_request("title is required and cannot be empty")
    next_id = max((t["id"] for t in tasks), default=0) + 1
    task = {"id": next_id, "title": body.title.strip(), "done": False}
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdate):
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


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        return not_found(task_id)
    tasks.remove(task)
    return Response(status_code=204)
