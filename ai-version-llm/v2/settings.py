"""Configuration loaded from environment variables (and .env via python-dotenv)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

PROMPT_VERSION = "triage-v1"
PROMPT_PATH = BASE_DIR / "prompts" / f"{PROMPT_VERSION}.md"
LOG_DIR = BASE_DIR / "logs"
CALL_LOG_PATH = LOG_DIR / "llm-calls.jsonl"
QUARANTINE_PATH = LOG_DIR / "quarantine.jsonl"

# Per-call timeout and our own retry policy (the SDK's retries are disabled).
CALL_TIMEOUT_S = 30.0
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 0.5
BACKOFF_MAX_S = 8.0
# If a 429 asks us to wait longer than this, give up and return 503 instead.
MAX_RETRY_AFTER_S = 20.0


def _flag(name: str, default: str) -> str:
    return os.getenv(name, default).strip().lower()


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    stub: bool
    enabled: bool


def load_settings() -> Settings:
    return Settings(
        # 127.0.0.1, not localhost: on Windows localhost tries IPv6 first (~2 s per call).
        base_url=os.getenv("LLM_BASE_URL") or "http://127.0.0.1:11434/v1",
        # Ollama ignores the key, but the SDK requires a non-empty value.
        api_key=os.getenv("LLM_API_KEY") or "ollama",
        model=os.getenv("LLM_MODEL") or "llama3.2",
        stub=_flag("LLM_STUB", "0") in {"1", "true", "yes", "on"},
        enabled=_flag("LLM_ENABLED", "true") not in {"0", "false", "no", "off"},
    )
