"""To-do list REST API. Run with: uvicorn main:app --port 8000"""
import itertools
import re
from typing import Any, List

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(title="Task API", version="1.0")


# ---------------------------------------------------------------- storage
tasks: List[dict] = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Write API docs", "done": True},
    {"id": 3, "title": "Walk the dog", "done": False},
]
_id_counter = itertools.count(4)  # ids are never reused after deletion


# ---------------------------------------------------------------- schemas (for docs and responses)
class Task(BaseModel):
    id: int
    title: str
    done: bool


class ErrorResponse(BaseModel):
    error: str


class Info(BaseModel):
    name: str
    version: str
    endpoints: List[str]


class Health(BaseModel):
    status: str


# ---------------------------------------------------------------- errors
class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


def error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return error_response(exc.status_code, exc.message)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        msg = "Resource not found"
    elif exc.status_code == 405:
        msg = "Method not allowed"
    else:
        msg = str(exc.detail) if exc.detail else "Request failed"
    return error_response(exc.status_code, msg)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return error_response(400, "Invalid request")


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    return error_response(500, "Internal server error")


# ---------------------------------------------------------------- helpers
def parse_id(raw: str) -> int:
    if not re.fullmatch(r"[0-9]+", raw):
        raise ApiError(400, "Task id must be a number")
    return int(raw)


def find_task(task_id: int) -> dict:
    for t in tasks:
        if t["id"] == task_id:
            return t
    raise ApiError(404, f"Task {task_id} not found")


async def read_json_object(request: Request) -> dict:
    try:
        body: Any = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise ApiError(400, "Request body must be valid JSON")
    if not isinstance(body, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return body


def clean_title(value: Any) -> str:
    if not isinstance(value, str):
        raise ApiError(400, "title must be a string")
    value = value.strip()
    if not value:
        raise ApiError(400, "title cannot be empty")
    return value


def clean_done(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ApiError(400, "done must be a boolean (true or false)")
    return value


# ---------------------------------------------------------------- docs helpers
ERR_400 = {"model": ErrorResponse, "description": "Invalid input"}
ERR_404 = {"model": ErrorResponse, "description": "Task not found"}

CREATE_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"title": {"type": "string", "minLength": 1}},
                    "required": ["title"],
                }
            }
        },
    }
}
UPDATE_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "description": "At least one of title or done is required.",
                    "properties": {
                        "title": {"type": "string", "minLength": 1},
                        "done": {"type": "boolean"},
                    },
                    "minProperties": 1,
                }
            }
        },
    }
}


# ---------------------------------------------------------------- endpoints
@app.get("/", summary="API info", response_model=Info)
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check", response_model=Health)
def health():
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks", response_model=List[Task])
def list_tasks():
    return [dict(t) for t in tasks]


@app.get(
    "/tasks/{task_id}",
    summary="Get one task",
    response_model=Task,
    responses={400: ERR_400, 404: ERR_404},
)
def get_task(task_id: str):
    return dict(find_task(parse_id(task_id)))


@app.post(
    "/tasks",
    summary="Create a task",
    status_code=201,
    response_model=Task,
    responses={400: ERR_400},
    openapi_extra=CREATE_BODY,
)
async def create_task(request: Request):
    body = await read_json_object(request)
    if "title" not in body:
        raise ApiError(400, "title is required")
    title = clean_title(body["title"])
    task = {"id": next(_id_counter), "title": title, "done": False}
    tasks.append(task)
    return dict(task)


@app.put(
    "/tasks/{task_id}",
    summary="Update a task",
    response_model=Task,
    responses={400: ERR_400, 404: ERR_404},
    openapi_extra=UPDATE_BODY,
)
async def update_task(task_id: str, request: Request):
    tid = parse_id(task_id)
    body = await read_json_object(request)
    if "title" not in body and "done" not in body:
        raise ApiError(400, "Body must contain title, done, or both")
    # validate everything before changing anything
    new_title = clean_title(body["title"]) if "title" in body else None
    new_done = clean_done(body["done"]) if "done" in body else None
    task = find_task(tid)
    if new_title is not None:
        task["title"] = new_title
    if new_done is not None:
        task["done"] = new_done
    return dict(task)


@app.delete(
    "/tasks/{task_id}",
    summary="Delete a task",
    status_code=204,
    response_class=Response,
    responses={400: ERR_400, 404: ERR_404},
)
def delete_task(task_id: str):
    task = find_task(parse_id(task_id))
    tasks.remove(task)
    return Response(status_code=204)


# ---------------------------------------------------------------- OpenAPI: never mention 422
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    for path_item in schema.get("paths", {}).values():
        for op in path_item.values():
            if isinstance(op, dict):
                op.get("responses", {}).pop("422", None)
    comps = schema.get("components", {}).get("schemas", {})
    comps.pop("HTTPValidationError", None)
    comps.pop("ValidationError", None)
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
