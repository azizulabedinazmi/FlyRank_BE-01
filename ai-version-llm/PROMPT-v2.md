# Prompt v2 (rematch)

v1 passed 16/18 behaviour checks and scored 19/25 on the real eval, but it answered bad input with FastAPI's 422
(the same code it uses for "the model failed"), couldn't parse an answer with text around the JSON because it relied
on `json_object` mode, returned `{"detail": ...}` with exception class names in it, and logged only to stdout.
v2 = v1 + the NEW block. Sent to a fresh AI session.

```text
Build a small FastAPI service (Python) with one endpoint, POST /tasks/triage, that uses an LLM to triage a messy
to-do note. Use the `openai` Python package pointed at an OpenAI-compatible server (Ollama locally), configured by
three env vars: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL (load them from .env with python-dotenv).

- Input: {"text": "..."}, 1-1000 characters. Validate it with Pydantic before calling the model.
- Output: {"title": short task title (max 80 chars), "category": one of work|errands|health|finance|home|learning|other,
  "priority": one of low|normal|high, "confidence": 0-1, "reason": one short sentence (max 160 chars),
  "source": "model" | "stub" | "fallback"}.
- If the note is vague, use category "other" with confidence below 0.5.
- Put the prompt in a file prompts/triage-v1.md, not in the code. Include a couple of examples. Temperature 0.
- Validate the model's answer with a Pydantic model. If it's invalid, retry once; if it's still invalid, return 422.
- Use a timeout on the model call and retry failed calls with exponential backoff.
- Log every model call (model, tokens, duration) as a JSON line.
- LLM_STUB=1 returns a fixed valid answer without calling the model. LLM_ENABLED=false is a kill switch that
  returns a safe fallback.
- Give me requirements.txt and a short README with a curl example. Entry point: uvicorn main:app

NEW:
- Invalid input returns 400 (not FastAPI's default 422) with {"error": "..."} naming the field. 422 is reserved for
  "the model's answer failed the schema twice". Every error body is {"error": "..."}, and never contains raw model
  text, exception class names or stack traces.
- Don't rely on response_format: models wrap JSON in ```json fences or add "Sure! Here's the JSON:". Extract the
  first complete JSON object from the text, then validate it. A top-level array is invalid.
- The repair call sends the broken answer back plus the exact validation error. If the second answer is also invalid,
  append a line to logs/quarantine.jsonl (input, prompt version, both raw answers, errors) before returning 422.
- Timeout 30 s per call; set the SDK's max_retries=0 explicitly so only your retry logic runs. Retry only timeouts,
  connection errors, 429 (obey Retry-After) and 5xx, max 3 attempts. Never retry 400/401/403/404.
  Map failures: timeout -> 504, auth/model-not-found/other provider errors -> 502, rate limit/unreachable -> 503.
- Write the call log to logs/llm-calls.jsonl, one line per real call: prompt version, model, input and output tokens,
  duration ms, attempt number, whether it was the repair call, outcome.
- Default LLM_BASE_URL to http://127.0.0.1:11434/v1, not localhost (on Windows localhost tries IPv6 first and adds
  ~2 s per call).
```
