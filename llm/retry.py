"""Retry the right failures only.

Retried (maybe temporary): timeouts, connection errors, 429, 5xx (and 408). Exponential backoff 1 s, 2 s (+ up to
0.5 s jitter); a 429/503 Retry-After header is obeyed instead of guessing.
Never retried: 400, 401, 403, 404, 422... A bad key is still a bad key four seconds later, and on a metered free tier
every pointless retry burns real quota.

The SDK's own retries are switched off (max_retries=0 in provider.py) so this is the only retry logic: one log line
per real call, and nobody makes six calls while thinking they made one.
"""
import random
import time
from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, APITimeoutError

MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 1.0
MAX_RETRY_AFTER_S = 20.0


@dataclass
class ProviderFailure(Exception):
    kind: str            # "timeout" | "connection" | "rate_limited" | "server_error" | "auth" | "bad_request" | ...
    status: int | None
    attempts: int
    detail: str

    def __str__(self) -> str:
        return f"{self.kind} after {self.attempts} attempt(s): {self.detail}"


def classify(e: Exception) -> tuple[str, int | None, bool, str | None]:
    """-> (kind, http status, retryable?, Retry-After header)"""
    if isinstance(e, APITimeoutError):  # (a subclass of APIConnectionError, so check it first)
        return "timeout", None, True, None
    if isinstance(e, APIConnectionError):
        return "connection", None, True, None
    if isinstance(e, APIStatusError):
        s = e.status_code
        retry_after = e.response.headers.get("retry-after") if e.response is not None else None
        if s == 429:
            return "rate_limited", s, True, retry_after
        if s >= 500 or s == 408:
            return "server_error", s, True, retry_after
        if s in (401, 403):
            return "auth", s, False, None
        if s == 404:
            return "not_found", s, False, None
        return "bad_request", s, False, None
    raise e  # not a provider error: a bug, let it surface


def wait_for(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), MAX_RETRY_AFTER_S)
        except ValueError:
            pass
    return BACKOFF_BASE_S * 2 ** (attempt - 1) + random.uniform(0, 0.5)


def call_with_retries(fn, *, on_attempt=None, sleep=time.sleep, deadline_s: float = 60.0):
    """Call fn() until it succeeds, fails with a non-retryable error, runs out of attempts, or the next wait would
    blow the overall deadline. on_attempt(attempt, error_kind|None, status, duration_ms) is called for every try."""
    start = time.monotonic()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        t = time.monotonic()
        try:
            result = fn()
        except (APIConnectionError, APIStatusError) as e:
            kind, status, retryable, retry_after = classify(e)
            if on_attempt:
                on_attempt(attempt, kind, status, round((time.monotonic() - t) * 1000))
            wait = wait_for(attempt, retry_after)
            out_of_time = time.monotonic() - start + wait > deadline_s
            if not retryable or attempt == MAX_ATTEMPTS or out_of_time:
                raise ProviderFailure(kind, status, attempt, str(getattr(e, "message", e))[:200])
            sleep(wait)
        else:
            if on_attempt:
                on_attempt(attempt, None, 200, round((time.monotonic() - t) * 1000))
            return result
