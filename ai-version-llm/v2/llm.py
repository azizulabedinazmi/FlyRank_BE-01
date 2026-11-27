"""Thin wrapper around the OpenAI-compatible chat API with our own retry policy.

- 30 s timeout per call; the SDK's built-in retries are disabled (max_retries=0).
- Retries (max 3 attempts): timeouts, connection errors, 429 (honouring Retry-After), 5xx.
- Never retries 400/401/403/404 or any other 4xx.
- Every real HTTP call is written to logs/llm-calls.jsonl.
"""

from __future__ import annotations

import asyncio
import email.utils
import random
import time
from dataclasses import dataclass
from typing import Any

import openai
from openai import AsyncOpenAI

import settings as cfg
from jsonl import append_jsonl


class LLMError(Exception):
    """A model call failed in a way the API maps to a 5xx. Message is safe to show."""

    def __init__(self, status_code: int, public_message: str) -> None:
        super().__init__(public_message)
        self.status_code = status_code
        self.public_message = public_message


@dataclass
class LLMResult:
    text: str | None
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: int
    attempt: int


def make_client(settings: cfg.Settings) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout=cfg.CALL_TIMEOUT_S,
        max_retries=0,  # only our retry logic runs
    )


def log_call(
    *,
    model: str,
    attempt: int,
    repair: bool,
    outcome: str,
    duration_ms: int,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    append_jsonl(
        cfg.CALL_LOG_PATH,
        {
            "event": "llm_call",
            "prompt_version": cfg.PROMPT_VERSION,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "attempt": attempt,
            "repair": repair,
            "outcome": outcome,
        },
    )


def _retry_after_seconds(exc: openai.APIStatusError) -> float | None:
    headers = exc.response.headers
    ms = headers.get("retry-after-ms")
    if ms:
        try:
            return max(0.0, float(ms) / 1000.0)
        except ValueError:
            pass
    value = headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
        return max(0.0, when.timestamp() - time.time())
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def _backoff(attempt: int) -> float:
    # attempt 1 -> ~0.5 s, attempt 2 -> ~1 s, ... with jitter
    delay = min(cfg.BACKOFF_MAX_S, cfg.BACKOFF_BASE_S * (2 ** (attempt - 1)))
    return delay * (0.5 + random.random() / 2)


def _classify(exc: Exception) -> tuple[str, bool, LLMError, float | None]:
    """Return (log outcome, retryable, error to raise if we give up, forced wait)."""
    if isinstance(exc, openai.APITimeoutError):  # must come before APIConnectionError
        return "timeout", True, LLMError(504, "the language model timed out"), None
    if isinstance(exc, openai.APIConnectionError):
        return "connection_error", True, LLMError(503, "the language model is unreachable"), None
    if isinstance(exc, openai.RateLimitError):
        return "rate_limited", True, LLMError(503, "the language model is rate limited; try again later"), _retry_after_seconds(exc)
    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return f"http_{exc.status_code}", False, LLMError(502, "the language model rejected our credentials"), None
    if isinstance(exc, openai.NotFoundError):
        return "http_404", False, LLMError(502, "the configured language model was not found"), None
    if isinstance(exc, openai.APIStatusError):
        status = exc.status_code
        retryable = status >= 500
        return f"http_{status}", retryable, LLMError(502, "the language model provider returned an error"), None
    if isinstance(exc, openai.OpenAIError):
        return "provider_error", False, LLMError(502, "the language model provider returned an error"), None
    return "unexpected_error", False, LLMError(502, "the language model call failed"), None


async def chat(
    client: AsyncOpenAI,
    *,
    model: str,
    messages: list[dict[str, Any]],
    repair: bool,
) -> LLMResult:
    """One logical model call, with up to MAX_ATTEMPTS real HTTP calls.

    Successful calls are NOT logged here: the caller logs them once it knows
    whether the answer validated (so each real call gets exactly one log line).
    """
    for attempt in range(1, cfg.MAX_ATTEMPTS + 1):
        started = time.perf_counter()
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                max_tokens=400,
            )
        except Exception as exc:  # noqa: BLE001 - classified below, never leaked
            duration_ms = int((time.perf_counter() - started) * 1000)
            outcome, retryable, error, forced_wait = _classify(exc)
            log_call(model=model, attempt=attempt, repair=repair, outcome=outcome, duration_ms=duration_ms)

            if not retryable or attempt >= cfg.MAX_ATTEMPTS:
                raise error from None
            if forced_wait is not None:
                if forced_wait > cfg.MAX_RETRY_AFTER_S:
                    raise error from None
                wait = forced_wait
            else:
                wait = _backoff(attempt)
            await asyncio.sleep(wait)
            continue

        duration_ms = int((time.perf_counter() - started) * 1000)
        usage = getattr(resp, "usage", None)
        text = None
        if resp.choices:
            text = resp.choices[0].message.content
        return LLMResult(
            text=text,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            duration_ms=duration_ms,
            attempt=attempt,
        )

    raise LLMError(502, "the language model call failed")  # unreachable
