"""FastAPI app. Run with: uvicorn main:app"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from config import settings
from llm import LLMClient, LLMUnavailableError
from schemas import ErrorResponse, TriageRequest, TriageResponse
from triage import InvalidModelOutputError, TriageService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only build a client when the model may actually be called.
    client = LLMClient(settings) if settings.llm_enabled and not settings.llm_stub else None
    app.state.triage = TriageService(settings, client)
    try:
        yield
    finally:
        if client is not None:
            await client.aclose()


app = FastAPI(title="Task Triage API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "llm_enabled": settings.llm_enabled,
        "llm_stub": settings.llm_stub,
        "model": settings.llm_model,
    }


@app.post(
    "/tasks/triage",
    response_model=TriageResponse,
    responses={
        422: {"description": "Invalid input, or the model's answer was invalid twice"},
        503: {"model": ErrorResponse, "description": "Model unreachable after retries"},
    },
)
async def triage_task(body: TriageRequest) -> TriageResponse:
    # `body` is already validated by Pydantic (1-1000 chars) before any model call.
    service: TriageService = app.state.triage
    try:
        return await service.triage(body.text)
    except InvalidModelOutputError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Model returned an invalid answer twice: {exc}",
        ) from exc
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
