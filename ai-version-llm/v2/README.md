# Task triage API

A small FastAPI service with one endpoint, `POST /tasks/triage`. It sends a messy to-do note to an LLM on an OpenAI-compatible server (Ollama by default) and returns a validated triage result.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (on macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # then edit it (on macOS/Linux: cp)
ollama pull llama3.2
uvicorn main:app --reload
```

| Variable | Default | Meaning |
|---|---|---|
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | OpenAI-compatible endpoint. It uses `127.0.0.1` because `localhost` on Windows tries IPv6 first, which adds about 2 s per call. |
| `LLM_API_KEY` | `ollama` | Ollama ignores it, but the SDK requires a value. |
| `LLM_MODEL` | `llama3.2` | Model name. |
| `LLM_STUB` | `0` | `1` returns a fixed valid answer (`source: "stub"`) without calling the model. |
| `LLM_ENABLED` | `true` | `false` is a kill switch. It returns a safe fallback (`category: "other"`, `confidence: 0`, `source: "fallback"`) and takes precedence over `LLM_STUB`. |

## Example

```bash
curl -s -X POST http://127.0.0.1:8000/tasks/triage \
  -H "Content-Type: application/json" \
  -d '{"text": "pay electricity bill!!! due tmrw"}'
```

```json
{"title":"Pay the electricity bill","category":"finance","priority":"high","confidence":0.95,"reason":"A bill payment that is due tomorrow.","source":"model"}
```

## Behaviour

- **Input:** `{"text": "..."}` with 1 to 1000 characters, not blank. Invalid input returns **400** with an error that names the field, for example `{"error": "text must be at most 1000 characters"}`.
- **Prompt:** the prompt is in `prompts/triage-v1.md`, which includes examples. Temperature is 0. The prompt version is written to every log line.
- **Parsing:** the service does not rely on `response_format`. It extracts the first complete JSON object from the reply, so code fences and "Sure! Here's the JSON:" are tolerated. A top-level array is invalid. The object is then validated by the strict Pydantic model `ModelTriage`.
- **Repair:** if the answer is invalid, the service makes one repair call that sends back the broken answer and the exact validation error. If that answer is also invalid, it appends a line to `logs/quarantine.jsonl` (input, prompt version, both raw answers, both errors) and returns **422**.
- **Timeouts and retries:**
  - Each call has a 30 s timeout. The SDK's own retries are turned off with `max_retries=0`.
  - The service retries timeouts, connection errors, 429 and 5xx responses, up to 3 attempts. It uses exponential backoff with jitter, and on a 429 it waits for the time given by `Retry-After`. If `Retry-After` asks for more than 20 s, it gives up straight away.
  - It never retries 400, 401, 403 or 404.
  - Worst case for one request: 2 calls × 3 attempts × 30 s.
- **Error mapping:**

  | Failure | Status |
  |---|---|
  | Timeout | 504 |
  | Auth error, model not found, other provider error, or 5xx after retries | 502 |
  | Rate limit or server unreachable | 503 |

- **Error bodies:** every error body is `{"error": "..."}`. It never contains raw model text, exception class names or stack traces. Unexpected errors return 500, and the details go only to the server log.
- **Call log:** `logs/llm-calls.jsonl` gets one line per real HTTP call. Each line has the prompt version, model, input and output tokens, duration in ms, attempt number, whether it was the repair call, and the outcome (`valid`, `invalid_output`, `timeout`, `connection_error`, `rate_limited`, `http_<status>`).
