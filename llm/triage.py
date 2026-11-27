"""POST /tasks/triage: the one place the route talks to.

    validate the input        -> done by TriageIn before we get here (400)
    build the prompt          -> prompts/triage-vN.md, the note as a separate user message
    call the model            -> provider.complete()
    parse + validate output   -> llm/parse.py against ModelTriage
    repair once if it failed  -> hand the model its own error message, one more call
    return clean JSON         -> or a 422 + a line in logs/quarantine.jsonl; never raw model text
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from llm import prompts
from llm.config import settings
from llm.parse import BadAnswer, parse_answer
from llm.provider import OpenAICompatible, Provider
from llm.schema import Triage

PROMPT_NAME = "triage-v1"
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


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def append_jsonl(name: str, record: dict) -> None:
    LOGS.mkdir(exist_ok=True)
    with (LOGS / name).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def make_provider() -> Provider:
    return OpenAICompatible(settings())


def run(text: str, provider: Provider | None = None) -> Triage:
    if settings().stub:
        return Triage(**STUB, source="stub")
    prompt = prompts.load(PROMPT_NAME)
    provider = provider or make_provider()
    messages = prompt.messages(text)
    attempts = []
    for attempt in (1, 2):  # the first answer, then exactly one repair
        out = provider.complete(messages, prompt.temperature)
        try:
            return Triage(**parse_answer(out.text).model_dump(), source="model")
        except BadAnswer as e:
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
