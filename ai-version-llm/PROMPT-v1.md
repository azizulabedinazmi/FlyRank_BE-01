# Prompt v1 (bonus: AI rematch)

Sent to a fresh AI session (Claude) with no access to this repo.

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
```
