"""Pydantic models for the request, the model's answer, and the API response."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal["work", "errands", "health", "finance", "home", "learning", "other"]
Priority = Literal["low", "normal", "high"]
Source = Literal["model", "stub", "fallback"]


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=1000, description="The messy to-do note.")

    @field_validator("text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank")
        return v


class TriageResult(BaseModel):
    """What the model must return. Used to validate the raw LLM output."""

    # Ignore extra keys the model may add; enforce types and limits strictly.
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=80)
    category: Category
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=160)


class TriageResponse(TriageResult):
    source: Source


class ErrorResponse(BaseModel):
    detail: str
