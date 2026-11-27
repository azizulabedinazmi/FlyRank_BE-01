"""POST /tasks/triage: the one place the route talks to. Stage 1: stub mode only, no model yet."""
from llm.config import settings
from llm.schema import Triage


class TriageError(Exception):
    """A failure the route turns into a clean HTTP error: never raw model text, never a crash."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


STUB = {"title": "Call mum about Sunday lunch", "category": "home", "priority": "normal", "confidence": 0.9,
        "reason": "Stub answer: LLM_STUB=1, no model was called."}


def run(text: str) -> Triage:
    if settings().stub:
        return Triage(**STUB, source="stub")
    raise TriageError(503, "The model isn't wired up yet (Stage 1). Set LLM_STUB=1.")
