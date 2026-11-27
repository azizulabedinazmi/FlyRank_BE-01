"""POST /tasks/triage: the one place the route talks to.

    kill switch / stub        -> LLM_ENABLED=false: safe fallback, zero calls · LLM_STUB=1: fixed answer, zero calls
    validate the input        -> done by TriageIn before we get here (400)
    build the prompt          -> prompts/triage-vN.md, the note as a separate user message
    call the model            -> provider.complete() with a real timeout, retries only on the right errors
    parse + validate output   -> llm/parse.py against ModelTriage
    repair once if it failed  -> hand the model its own error message, one more call
    return clean JSON         -> or 422 + logs/quarantine.jsonl / 502 / 503 / 504; never raw model text
Every model call writes one line to logs/llm-calls.jsonl (prompt version, model, tokens, duration, repair, outcome).
"""
import hashlib
import json
import os
import re
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from llm import prompts
from llm.config import settings
from llm.parse import BadAnswer, parse_answer
from llm.provider import Completion, OpenAICompatible, Provider
from llm.retry import ProviderFailure, call_with_retries
from llm.schema import ModelTriage, Triage

PROMPT_NAME = os.environ.get("LLM_PROMPT", "triage-v1")
LOGS = Path(__file__).resolve().parent.parent / "logs"


class TriageError(Exception):
    """A failure the route turns into a clean HTTP error: never raw model text, never a crash."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


STUB = {"title": "Call mum about Sunday lunch", "category": "home", "priority": "normal", "confidence": 0.9,
        "reason": "Stub answer: LLM_STUB=1, no model was called."}

REPAIR = ("Your previous answer was rejected for this reason: {reason}\n"
          "Return only corrected JSON matching the schema in the instructions: exactly the five fields, "
          "allowed values only, no code fences, no other text.")

# What the caller sees when the provider fails. The provider's own message goes to the log, not to the caller.
PROVIDER_ERRORS = {
    "timeout": (504, "The model didn't answer within {timeout:g} s ({attempts} attempt(s)). Try again later."),
    "connection": (503, "The model provider can't be reached right now ({attempts} attempt(s))."),
    "rate_limited": (503, "The model provider is rate-limiting us. Try again in a minute."),
    "server_error": (502, "The model provider returned a server error ({attempts} attempt(s))."),
    "auth": (502, "The model provider rejected this server's credentials. An operator needs to fix the key."),
    "not_found": (502, "The model provider doesn't know the configured model. An operator needs to fix LLM_MODEL."),
    "bad_request": (502, "The model provider rejected the request."),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def append_jsonl(name: str, record: dict) -> None:
    LOGS.mkdir(exist_ok=True)
    with (LOGS / name).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def make_provider() -> Provider:
    return OpenAICompatible(settings())


# Extra: a small in-memory cache. The key includes the prompt version AND the model, so changing either one
# can never serve yesterday's answers. Only valid answers are cached.
_CACHE: "OrderedDict[str, dict]" = OrderedDict()
CACHE_SIZE = 256


def cache_key(prompt_version: str, model: str, text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(f"{prompt_version}|{model}|{normalized}".encode()).hexdigest()


def structured_format() -> dict | None:
    """Extra: ask the provider to constrain decoding to our JSON schema (LLM_STRUCTURED=1). Not every model supports
    it; our own parse + validate still runs either way, because "supported" is not the same as "guaranteed"."""
    if os.environ.get("LLM_STRUCTURED", "0") != "1":
        return None
    return {"type": "json_schema",
            "json_schema": {"name": "triage", "strict": True, "schema": ModelTriage.model_json_schema()}}


def fallback(text: str) -> Triage:
    """Kill switch answer: deterministic, schema-valid, honest about being a default."""
    title = re.sub(r"\s+", " ", text).strip()[:80] or "Untitled task"
    return Triage(title=title, category="other", priority="normal", confidence=0.0,
                  reason="AI triage is switched off (LLM_ENABLED=false); this is a safe default.", source="fallback")


def run(text: str, provider: Provider | None = None, sleep=time.sleep) -> Triage:
    s = settings()
    if not s.enabled:
        append_jsonl("llm-calls.jsonl", {"ts": now(), "outcome": "disabled", "model_calls": 0})
        return fallback(text)
    if s.stub:
        return Triage(**STUB, source="stub")

    prompt = prompts.load(PROMPT_NAME)
    provider = provider or make_provider()
    use_cache = os.environ.get("LLM_CACHE", "1") == "1"
    key = cache_key(prompt.version, provider.model, text)
    if use_cache and key in _CACHE:
        _CACHE.move_to_end(key)
        append_jsonl("llm-calls.jsonl", {"ts": now(), "prompt_version": prompt.version, "model": provider.model,
                                         "outcome": "cache_hit", "model_calls": 0})
        return Triage(**_CACHE[key], source="cache")
    messages = prompt.messages(text)
    attempts = []
    for purpose in ("answer", "repair"):  # the first answer, then exactly one repair
        out, record = _call(provider, prompt, messages, purpose, s.timeout_s, sleep)
        try:
            answer = parse_answer(out.text).model_dump()
            append_jsonl("llm-calls.jsonl", {**record, "outcome": "ok"})
            if use_cache:
                _CACHE[key] = answer
                while len(_CACHE) > CACHE_SIZE:
                    _CACHE.popitem(last=False)
            return Triage(**answer, source="model")
        except BadAnswer as e:
            append_jsonl("llm-calls.jsonl", {**record, "outcome": f"bad_answer: {', '.join(e.fields) or e.reason}"})
            attempts.append({"raw": out.text[:4000], "error": e.reason, "fields": e.fields})
            # Same conversation + the broken answer + the exact error: the model fixes its own mistake.
            messages = messages + [{"role": "assistant", "content": out.text},
                                   {"role": "user", "content": REPAIR.format(reason=e.reason)}]
    append_jsonl("quarantine.jsonl", {"ts": now(), "prompt_version": prompt.version, "model": provider.model,
                                      "input": text, "attempts": attempts})
    last = attempts[-1]
    what = f"invalid fields: {', '.join(last['fields'])}" if last["fields"] else last["error"]
    raise TriageError(422, f"The model's answer failed the schema twice ({what}). "
                           "It was quarantined; nothing was returned.")


def _call(provider: Provider, prompt, messages: list[dict], purpose: str, timeout_s: float,
          sleep) -> tuple[Completion, dict]:
    """One logical model call (with retries). Every real HTTP attempt gets exactly one cost-log line: failed
    attempts are written here; the successful one is returned so its line can carry the parse outcome too."""
    holder: dict = {}

    def attempt_log(n: int, error: str | None, status: int | None, ms: int) -> None:
        out = holder.get("out") if not error else None
        record = {"ts": now(), "prompt_version": prompt.version, "model": provider.model, "purpose": purpose,
                  "repair": purpose == "repair", "attempt": n, "status": status, "duration_ms": ms,
                  "input_tokens": out.input_tokens if out else None,
                  "output_tokens": out.output_tokens if out else None}
        if error:
            append_jsonl("llm-calls.jsonl", {**record, "outcome": f"error: {error}"})
        else:
            holder["record"] = record

    def once() -> Completion:
        holder["out"] = provider.complete(messages, prompt.temperature, structured_format())
        return holder["out"]

    try:
        out = call_with_retries(once, on_attempt=attempt_log, sleep=sleep, deadline_s=timeout_s * 2)
        return out, holder["record"]
    except ProviderFailure as f:
        status, message = PROVIDER_ERRORS.get(f.kind, (502, "The model provider failed."))
        raise TriageError(status, message.format(timeout=timeout_s, attempts=f.attempts))

