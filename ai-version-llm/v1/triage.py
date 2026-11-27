"""Triage logic: stub / kill switch / model call with one validation retry."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import ValidationError

from config import Settings
from llm import LLMClient, log_json
from schemas import TriageResponse, TriageResult

STUB_RESULT = TriageResult(
    title="Review the to-do note",
    category="work",
    priority="normal",
    confidence=0.9,
    reason="Stub mode is on; this is a fixed answer and no model was called.",
)

FALLBACK_RESULT = TriageResult(
    title="Review this note manually",
    category="other",
    priority="normal",
    confidence=0.0,
    reason="Automatic triage is turned off, so this note needs manual review.",
)


class InvalidModelOutputError(Exception):
    """The model answered twice, and neither answer passed validation."""


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_result(raw: str) -> TriageResult:
    """Parse and validate the model's raw text. Raises ValueError/ValidationError."""
    cleaned = _FENCE_RE.sub("", raw.strip())
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")
    return TriageResult.model_validate(data)


def _note_message(text: str) -> str:
    # Neutralise any closing tag the user may have typed so the note stays delimited.
    safe = text.replace("</note>", "<\\/note>")
    return f"<note>{safe}</note>"


class TriageService:
    def __init__(self, settings: Settings, client: LLMClient | None) -> None:
        self.settings = settings
        self.client = client
        self.system_prompt = load_prompt(settings.prompt_path)

    async def triage(self, text: str) -> TriageResponse:
        s = self.settings

        # Kill switch first: if disabled, never call the model.
        if not s.llm_enabled:
            log_json(event="triage", source="fallback", reason="LLM_ENABLED=false")
            return TriageResponse(**FALLBACK_RESULT.model_dump(), source="fallback")

        if s.llm_stub:
            log_json(event="triage", source="stub")
            return TriageResponse(**STUB_RESULT.model_dump(), source="stub")

        assert self.client is not None
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": _note_message(text)},
        ]

        # Attempt 1, then one corrective retry if the answer is invalid.
        last_error = ""
        for validation_attempt in (1, 2):
            reply = await self.client.chat(messages, purpose=f"triage#{validation_attempt}")
            try:
                result = parse_result(reply.content)
            except (ValueError, ValidationError) as exc:
                last_error = _short_error(exc)
                log_json(
                    event="triage_invalid_output",
                    validation_attempt=validation_attempt,
                    error=last_error,
                )
                messages = messages + [
                    {"role": "assistant", "content": reply.content},
                    {
                        "role": "user",
                        "content": (
                            "Your previous answer was invalid: "
                            f"{last_error}. Reply again with only the JSON object, "
                            "following every rule in the instructions."
                        ),
                    },
                ]
                continue
            return TriageResponse(**result.model_dump(), source="model")

        raise InvalidModelOutputError(last_error)


def _short_error(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        parts = [
            f"{'.'.join(str(p) for p in e['loc']) or 'root'}: {e['msg']}" for e in exc.errors()
        ]
        return "; ".join(parts)[:500]
    return str(exc)[:500]
