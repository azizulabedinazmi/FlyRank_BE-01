"""Settings loaded from environment variables (and .env via python-dotenv)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load .env from the project root. Real environment variables win over .env.
load_dotenv(BASE_DIR / ".env", override=False)


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_enabled: bool  # kill switch: false -> safe fallback, no model call
    llm_stub: bool  # true -> fixed valid answer, no model call
    timeout_s: float  # per-request timeout for one model call
    max_attempts: int  # attempts per call for transient errors (timeouts, 429, 5xx)
    backoff_base_s: float  # first backoff delay; doubles each retry
    prompt_path: Path


def load_settings() -> Settings:
    return Settings(
        llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        # Ollama ignores the key, but the openai client requires a non-empty one.
        llm_api_key=os.getenv("LLM_API_KEY", "ollama"),
        llm_model=os.getenv("LLM_MODEL", "llama3.1"),
        llm_enabled=_bool("LLM_ENABLED", True),
        llm_stub=_bool("LLM_STUB", False),
        timeout_s=_float("LLM_TIMEOUT_SECONDS", 20.0),
        max_attempts=max(1, _int("LLM_MAX_ATTEMPTS", 3)),
        backoff_base_s=_float("LLM_BACKOFF_BASE_SECONDS", 0.5),
        prompt_path=BASE_DIR / "prompts" / "triage-v1.md",
    )


settings = load_settings()
