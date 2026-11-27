"""LLM settings, read from the environment on every call (so the kill switch works without a restart in tests)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    stub: bool
    enabled: bool
    timeout_s: float


def settings() -> Settings:
    return Settings(
        base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.environ.get("LLM_API_KEY", "ollama"),
        model=os.environ.get("LLM_MODEL", "llama3.2:3b"),
        stub=_flag("LLM_STUB", "0"),
        enabled=_flag("LLM_ENABLED", "true"),
        timeout_s=float(os.environ.get("LLM_TIMEOUT_S", "30")),
    )
