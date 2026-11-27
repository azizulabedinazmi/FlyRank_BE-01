# Task Triage API

A small FastAPI service with one endpoint, `POST /tasks/triage`. It sends a messy to-do note to an LLM through an OpenAI-compatible API (Ollama locally) and returns a structured task.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then set LLM_MODEL to a model you have pulled
ollama pull llama3.1
uvicorn main:app
```

## Example

```bash
curl -s -X POST http://127.0.0.1:8000/tasks/triage \
  -H "Content-Type: application/json" \
  -d '{"text": "call dentist tmrw, tooth still hurts"}'
```

Example response:

```json
{
  "title": "Call the dentist tomorrow about tooth pain",
  "category": "health",
  "priority": "high",
  "confidence": 0.9,
  "reason": "Ongoing tooth pain with a call planned for tomorrow.",
  "source": "model"
}
```

## Configuration (env vars, loaded from `.env`)

| Variable | Default | Purpose |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible base URL |
| `LLM_API_KEY` | `ollama` | API key (Ollama ignores it) |
| `LLM_MODEL` | `llama3.1` | Model name |
| `LLM_STUB` | `0` | `1` returns a fixed valid answer, `source: "stub"`, no model call |
| `LLM_ENABLED` | `true` | `false` is a kill switch: safe fallback, `source: "fallback"`, no model call |
| `LLM_TIMEOUT_SECONDS` | `20` | Timeout for each model call |
| `LLM_MAX_ATTEMPTS` | `3` | Attempts for transient errors (timeout, connection, 429, 5xx) |
| `LLM_BACKOFF_BASE_SECONDS` | `0.5` | Backoff 0.5s, 1s, 2s, ... |

If both are set, the kill switch wins over the stub.

## Behaviour

- Input `{"text": "..."}` must be 1-1000 characters (and not blank). Bad input gets a 422 before any model call.
- The prompt lives in `prompts/triage-v1.md` (with examples). Temperature is 0 and JSON mode is requested.
- The model's answer is validated with Pydantic (`TriageResult`). If it is invalid, the service retries once and tells the model what was wrong. If the second answer is also invalid, it returns 422.
- If the model can't be reached after all retries, it returns 503.
- Every model call attempt is logged to stdout as one JSON line, for example:
  `{"event": "llm_call", "purpose": "triage#1", "model": "llama3.1", "attempt": 1, "ok": true, "duration_ms": 812.4, "prompt_tokens": 612, "completion_tokens": 58, "total_tokens": 670, "ts": "..."}`
- `GET /health` shows the current mode.

## Files

- `main.py`: FastAPI app and endpoint
- `config.py`: env var settings
- `schemas.py`: Pydantic models
- `llm.py`: OpenAI client, timeout, backoff retries, JSON logging
- `triage.py`: stub, kill switch, validation and retry
- `prompts/triage-v1.md`: system prompt
