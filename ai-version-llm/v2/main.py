"""FastAPI entry point: uvicorn main:app"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import settings as cfg
from llm import LLMError, make_client
from schemas import TriageRequest, TriageResponse
from triage import STUB_ANSWER, ModelOutputInvalid, fallback_answer, load_prompt, triage_with_model

logger = logging.getLogger("triage")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = cfg.load_settings()
    app.state.system_prompt = load_prompt()  # fail fast if the prompt file is missing
    app.state.client = make_client(app.state.settings)
    cfg.LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        yield
    finally:
        await app.state.client.close()


app = FastAPI(title="Task triage", version="2.0.0", lifespan=lifespan)


def error(status_code: int, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message}, headers=headers)


# ---------- error handlers: every error body is {"error": "..."} ----------

_FRIENDLY = {
    "missing": "is required",
    "string_type": "must be a string",
    "string_too_short": "must be at least 1 character",
    "string_too_long": "must be at most 1000 characters",
}


def _describe_validation_error(err: dict[str, Any]) -> str:
    loc = [str(p) for p in err.get("loc", ()) if p != "body"]
    etype = err.get("type", "")
    if etype == "json_invalid":
        return "request body is not valid JSON"
    if not loc:
        return "request body must be a JSON object with a 'text' field"
    field = ".".join(loc)
    if etype in _FRIENDLY:
        return f"{field} {_FRIENDLY[etype]}"
    if etype == "value_error":
        return f"{field} must not be blank"
    return f"{field} is invalid"


@app.exception_handler(RequestValidationError)
async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    message = _describe_validation_error(errors[0]) if errors else "invalid request"
    return error(400, message)


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "request failed"
    return error(exc.status_code, message, getattr(exc, "headers", None))


@app.exception_handler(Exception)
async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error")  # stack trace goes to server logs only
    return error(500, "internal server error")


# ---------- endpoint ----------

@app.post("/tasks/triage", response_model=TriageResponse)
async def triage_endpoint(body: TriageRequest, request: Request):
    settings: cfg.Settings = request.app.state.settings

    if not settings.enabled:  # kill switch wins over everything
        return fallback_answer(body.text)
    if settings.stub:
        return STUB_ANSWER

    try:
        return await triage_with_model(
            request.app.state.client, settings.model, request.app.state.system_prompt, body.text
        )
    except LLMError as exc:
        return error(exc.status_code, exc.public_message)
    except ModelOutputInvalid:
        return error(422, "the model's answer failed schema validation twice")
