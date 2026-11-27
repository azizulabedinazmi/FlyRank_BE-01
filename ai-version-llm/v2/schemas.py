"""Pydantic models for the request, the model's answer and the API response."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal["work", "errands", "health", "finance", "home", "learning", "other"]
Priority = Literal["low", "normal", "high"]
Source = Literal["model", "stub", "fallback"]


class TriageRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    text: str = Field(min_length=1, max_length=1000)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ModelTriage(BaseModel):
    """What the LLM must return. Strict: no string->number coercion, no unknown enum values."""

    model_config = ConfigDict(strict=True, extra="ignore")

    title: str = Field(min_length=1, max_length=80)
    category: Category
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=160)

    @field_validator("title", "reason")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class TriageResponse(ModelTriage):
    source: Source
