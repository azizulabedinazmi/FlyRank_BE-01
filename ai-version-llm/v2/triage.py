"""Triage orchestration: prompt -> model -> extract JSON -> validate -> (repair once) -> result."""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

import settings as cfg
from json_extract import ExtractionError, extract_first_json_object
from jsonl import append_jsonl
from llm import chat, log_call
from schemas import ModelTriage, TriageResponse

STUB_ANSWER = TriageResponse(
    title="Review the to-do note",
    category="work",
    priority="normal",
    confidence=0.9,
    reason="Fixed stub answer (LLM_STUB=1); no model was called.",
    source="stub",
)


class ModelOutputInvalid(Exception):
    """The model's answer failed validation twice (initial + repair)."""


def load_prompt() -> str:
    return cfg.PROMPT_PATH.read_text(encoding="utf-8")


def fallback_answer(text: str) -> TriageResponse:
    """Safe answer used when the kill switch (LLM_ENABLED=false) is on."""
    first_line = " ".join(text.split())[:80].strip() or "Untitled note"
    return TriageResponse(
        title=first_line,
        category="other",
        priority="normal",
        confidence=0.0,
        reason="Automatic triage is disabled; this note needs manual review.",
        source="fallback",
    )


def _format_validation_error(exc: Exception) -> str:
    """A precise, compact description of why an answer was rejected."""
    if isinstance(exc, ExtractionError):
        return str(exc)
    if isinstance(exc, ValidationError):
        parts = []
        for err in exc.errors(include_url=False, include_input=False):
            loc = ".".join(str(p) for p in err.get("loc", ())) or "(root)"
            parts.append(f"{loc}: {err.get('msg')}")
        return "; ".join(parts)
    return "answer could not be validated"


def _validate(raw: str | None) -> tuple[ModelTriage | None, str | None]:
    try:
        data = extract_first_json_object(raw)
        return ModelTriage.model_validate(data), None
    except (ExtractionError, ValidationError) as exc:
        return None, _format_validation_error(exc)


def _repair_message(error: str) -> str:
    return (
        "Your previous answer was rejected by the validator with this error:\n"
        f"{error}\n\n"
        "Reply again with ONLY one corrected JSON object that has exactly the keys "
        "title, category, priority, confidence, reason and follows every rule in the "
        "instructions. No code fences, no extra text."
    )


async def triage_with_model(client: AsyncOpenAI, model: str, system_prompt: str, text: str) -> TriageResponse:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"<note>\n{text}\n</note>"},
    ]

    # First call.
    first = await chat(client, model=model, messages=messages, repair=False)
    result, error1 = _validate(first.text)
    log_call(
        model=model, attempt=first.attempt, repair=False,
        outcome="valid" if result else "invalid_output",
        duration_ms=first.duration_ms,
        input_tokens=first.input_tokens, output_tokens=first.output_tokens,
    )
    if result is not None:
        return TriageResponse(**result.model_dump(), source="model")

    # Repair call: send the broken answer back with the exact validation error.
    repair_messages = messages + [
        {"role": "assistant", "content": first.text or ""},
        {"role": "user", "content": _repair_message(error1 or "")},
    ]
    second = await chat(client, model=model, messages=repair_messages, repair=True)
    result, error2 = _validate(second.text)
    log_call(
        model=model, attempt=second.attempt, repair=True,
        outcome="valid" if result else "invalid_output",
        duration_ms=second.duration_ms,
        input_tokens=second.input_tokens, output_tokens=second.output_tokens,
    )
    if result is not None:
        return TriageResponse(**result.model_dump(), source="model")

    append_jsonl(
        cfg.QUARANTINE_PATH,
        {
            "prompt_version": cfg.PROMPT_VERSION,
            "model": model,
            "input": text,
            "raw_answers": [first.text, second.text],
            "errors": [error1, error2],
        },
    )
    raise ModelOutputInvalid()
