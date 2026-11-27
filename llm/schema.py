"""The contract, written before the model exists. Copied from JOB-CARD.md."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

Category = Literal["work", "errands", "health", "finance", "home", "learning", "other"]
Priority = Literal["low", "normal", "high"]
Source = Literal["model", "stub", "fallback", "cache"]
CATEGORIES: tuple[str, ...] = Category.__args__
PRIORITIES: tuple[str, ...] = Priority.__args__
MAX_INPUT = 1000


class TriageIn(BaseModel):
    """What a caller may send. Checked before any model call: every rejected request is a call we didn't pay for."""
    model_config = ConfigDict(extra="forbid")

    text: StrictStr = Field(min_length=1, max_length=MAX_INPUT, pattern=r"^[^\x00]*$",
                            examples=["ring mum re sunday lunch + pick up her meds!!"])

    @field_validator("text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must contain some text, not only spaces")
        return v


class ModelTriage(BaseModel):
    """What the MODEL must return: exactly these five fields. extra="forbid" means an added field is a failure."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    category: Category
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=160)


class Triage(ModelTriage):
    """What the ENDPOINT returns: the model's five fields plus where the answer came from (set by our code)."""
    source: Source


def output_shape_for_prompt() -> str:
    """The shape the prompt shows the model, generated from the same lists so the two can't drift apart."""
    return ("{\n"
            '  "title": "<the note as a short task, max 80 characters>",\n'
            f'  "category": "<one of: {" | ".join(CATEGORIES)}>",\n'
            f'  "priority": "<one of: {" | ".join(PRIORITIES)}>",\n'
            '  "confidence": <number between 0.0 and 1.0>,\n'
            '  "reason": "<one short sentence, max 160 characters>"\n'
            "}")
