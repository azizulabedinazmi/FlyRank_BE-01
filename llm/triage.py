"""POST /tasks/triage: the one place the route talks to.

Stage 2: load the versioned prompt, send the note as a separate user message, validate the answer once.
"""
import json

from pydantic import ValidationError

from llm import prompts
from llm.config import settings
from llm.provider import OpenAICompatible, Provider
from llm.schema import ModelTriage, Triage

PROMPT_NAME = "triage-v1"


class TriageError(Exception):
    """A failure the route turns into a clean HTTP error: never raw model text, never a crash."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


STUB = {"title": "Call mum about Sunday lunch", "category": "home", "priority": "normal", "confidence": 0.9,
        "reason": "Stub answer: LLM_STUB=1, no model was called."}


def make_provider() -> Provider:
    return OpenAICompatible(settings())


def run(text: str, provider: Provider | None = None) -> Triage:
    if settings().stub:
        return Triage(**STUB, source="stub")
    prompt = prompts.load(PROMPT_NAME)
    provider = provider or make_provider()
    out = provider.complete(prompt.messages(text), prompt.temperature)
    try:
        return Triage(**ModelTriage.model_validate(json.loads(out.text)).model_dump(), source="model")
    except (json.JSONDecodeError, ValidationError, TypeError) as e:
        raise TriageError(422, f"The model's answer didn't match the schema: {e.__class__.__name__}")
