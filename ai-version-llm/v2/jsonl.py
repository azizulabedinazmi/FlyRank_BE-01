"""Append-only JSON-lines writer for the call log and the quarantine file."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_lock = threading.Lock()


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    line = json.dumps(
        {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), **record},
        ensure_ascii=False,
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _lock, path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        # Logging must never break a request.
        pass
