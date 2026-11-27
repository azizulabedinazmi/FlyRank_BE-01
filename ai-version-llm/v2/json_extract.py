"""Pull the first complete JSON object out of free-form model text.

Models often wrap JSON in ```json fences or add chatter such as
"Sure! Here's the JSON:". We do not rely on response_format; instead we scan the
text for the first position where a complete JSON value can be decoded.
"""

from __future__ import annotations

import json
from typing import Any


class ExtractionError(ValueError):
    """Raised when no usable JSON object can be found in the text."""


_decoder = json.JSONDecoder()


def extract_first_json_object(text: str | None) -> dict[str, Any]:
    if text is None or not text.strip():
        raise ExtractionError("the answer was empty; expected a single JSON object")

    for i, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            value, _end = _decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            continue  # not a complete JSON value starting here; keep scanning
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            raise ExtractionError("the answer is a JSON array; expected a single JSON object")

    raise ExtractionError("no complete JSON object found in the answer")
