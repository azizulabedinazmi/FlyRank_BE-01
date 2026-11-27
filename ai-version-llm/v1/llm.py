"""Thin wrapper around the OpenAI-compatible chat API (Ollama locally).

- Per-call timeout.
- Retries transient failures (timeouts, connection errors, 429, 5xx) with
  exponential backoff plus a little jitter.
- Logs every model call attempt as one JSON line: model, tokens, duration.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import sys
import time
from dataclasses import dataclass

import openai
from openai import AsyncOpenAI

from config import Settings

# --- JSON-lines logger -------------------------------------------------------

logger = logging.getLogger("llm")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_json(**fields: object) -> None:
    fields.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    logger.info(json.dumps(fields, ensure_ascii=False, default=str))


# --- Errors ------------------------------------------------------------------


class LLMUnavailableError(Exception):
    """The model could not be reached after all retries (or a non-retryable API error)."""


@dataclass
class LLMReply:
    content: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


def _is_retryable(exc: Exception) -> bool:
    # APITimeoutError is a subclass of APIConnectionError.
    if isinstance(exc, (openai.APIConnectionError, openai.RateLimitError)):
        return True
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code >= 500
    return False


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # max_retries=0: we do our own retries so every attempt is logged and the
        # backoff policy is explicit.
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.timeout_s,
            max_retries=0,
        )

    async def chat(self, messages: list[dict[str, str]], purpose: str) -> LLMReply:
        s = self.settings
        last_exc: Exception | None = None

        for attempt in range(1, s.max_attempts + 1):
            started = time.perf_counter()
            try:
                resp = await self._client.chat.completions.create(
                    model=s.llm_model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=0,
                    response_format={"type": "json_object"},
                    timeout=s.timeout_s,
                )
            except Exception as exc:  # noqa: BLE001 - classified below
                duration_ms = round((time.perf_counter() - started) * 1000, 1)
                retryable = _is_retryable(exc)
                log_json(
                    event="llm_call",
                    purpose=purpose,
                    model=s.llm_model,
                    attempt=attempt,
                    ok=False,
                    error=type(exc).__name__,
                    retryable=retryable,
                    duration_ms=duration_ms,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                )
                last_exc = exc
                if not retryable or attempt == s.max_attempts:
                    break
                delay = s.backoff_base_s * (2 ** (attempt - 1))
                delay += random.uniform(0, delay * 0.1)  # small jitter
                await asyncio.sleep(delay)
                continue

            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            usage = resp.usage
            reply = LLMReply(
                content=(resp.choices[0].message.content or "") if resp.choices else "",
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            )
            log_json(
                event="llm_call",
                purpose=purpose,
                model=s.llm_model,
                attempt=attempt,
                ok=True,
                duration_ms=duration_ms,
                prompt_tokens=reply.prompt_tokens,
                completion_tokens=reply.completion_tokens,
                total_tokens=reply.total_tokens,
            )
            return reply

        raise LLMUnavailableError(
            f"model call failed after {attempt} attempt(s): {type(last_exc).__name__}"
        ) from last_exc

    async def aclose(self) -> None:
        await self._client.close()
