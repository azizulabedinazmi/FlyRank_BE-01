"""Prompts are code: they live in prompts/<job>-vN.md with a version, get reviewed and diffed like code."""
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


@dataclass(frozen=True)
class Prompt:
    version: str
    temperature: float
    system: str

    def messages(self, note: str) -> list[dict]:
        """The user's text goes in its own user message, JSON-encoded, never glued into the system prompt:
        the model treats roles differently, and JSON-encoding stops the note from breaking out of its quotes."""
        return [{"role": "system", "content": self.system},
                {"role": "user", "content": json.dumps({"note": note}, ensure_ascii=False)}]


@lru_cache
def load(name: str) -> Prompt:
    """Load prompts/<name>.md: a small front-matter block (version, temperature), then the system prompt."""
    text = (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError(f"prompts/{name}.md has no front matter")
    meta = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    return Prompt(version=meta["version"], temperature=float(meta.get("temperature", 0)), system=m.group(2).strip())
