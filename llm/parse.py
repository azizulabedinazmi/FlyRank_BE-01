"""The model's answer is untrusted input: find the JSON, then validate it. Never trust, never echo."""
import json
import re

from pydantic import ValidationError

from llm.schema import ModelTriage


class BadAnswer(Exception):
    """The answer couldn't be turned into a valid ModelTriage. `reason` is short and safe to show the model again."""

    def __init__(self, reason: str, fields: list[str] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.fields = fields or []  # which fields were wrong: safe to show the caller


def extract_json(text: str) -> object:
    """Models like to wrap JSON in ```json fences or say "Sure! Here's the JSON:" first. Take the first complete
    {...} object in the text (string-aware, so braces inside strings don't confuse it) and parse that.
    If the whole answer already IS valid JSON, that exact value is used, so an array like [{...}] is rejected rather
    than quietly unwrapped."""
    stripped = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text.strip())
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break  # not valid JSON from this brace; try the next "{"
        start = text.find("{", start + 1)
    raise BadAnswer("the answer contained no JSON object")


def parse_answer(text: str) -> ModelTriage:
    data = extract_json(text)
    if not isinstance(data, dict):
        raise BadAnswer("the answer was not a JSON object")
    try:
        return ModelTriage.model_validate(data)
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(map(str, err['loc'])) or 'object'}: {err['msg']}" for err in e.errors())
        fields = sorted({".".join(map(str, err["loc"])) or "object" for err in e.errors()})
        raise BadAnswer(problems[:500], fields)
