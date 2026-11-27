"""Replays the Stage 3 and Stage 4 checkpoints against a real server, each with its own settings.

    python evals/checkpoints.py

Each scenario starts uvicorn on port 8011 with extra environment variables, sends one note, prints the response and
the new lines in logs/llm-calls.jsonl / logs/quarantine.jsonl, then stops the server. Needs Postgres running (the
API's startup checks it) and Ollama for the scenarios that reach a model.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
PORT = 8011
NOTE = "electricity bill overdue, pay it today pls"

BROKEN = ROOT / "prompts" / "triage-broken.md"  # temporary, deleted at the end


def start(env_extra: dict) -> subprocess.Popen:
    env = {**os.environ, "LLM_CACHE": "0", **env_extra}
    server_log = (LOGS / "checkpoint-server.log").open("w", encoding="utf-8")
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(PORT)], cwd=ROOT, env=env,
                         stdout=server_log, stderr=subprocess.STDOUT)
    last = None
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
            return p
        except Exception as e:  # noqa: BLE001
            last = e
            if p.poll() is not None:
                break
            time.sleep(0.5)
    p.kill()
    raise SystemExit(f"server didn't start ({last!r}); see logs/checkpoint-server.log")


def post(text: str) -> tuple[int, str, float]:
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/tasks/triage", json.dumps({"text": text}).encode(),
                                 {"Content-Type": "application/json"}, method="POST")
    t = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, r.read().decode(), time.monotonic() - t
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), time.monotonic() - t


def lines(name: str) -> list[str]:
    p = LOGS / name
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def scenario(title: str, env_extra: dict, text: str = NOTE) -> None:
    before_calls, before_q = len(lines("llm-calls.jsonl")), len(lines("quarantine.jsonl"))
    p = start(env_extra)
    try:
        status, body, secs = post(text)
    finally:
        p.terminate()
        p.wait()
    new_calls = lines("llm-calls.jsonl")[before_calls:]
    new_q = lines("quarantine.jsonl")[before_q:]
    real_calls = [c for c in new_calls if json.loads(c).get("attempt")]
    print(f"\n### {title}\nsettings: {env_extra}\nHTTP {status} in {secs:.1f}s: {body}")
    print(f"model calls made: {len(real_calls)}")
    for c in new_calls:
        print("  llm-calls.jsonl:", c)
    for q in new_q:
        print("  quarantine.jsonl:", q[:400] + ("..." if len(q) > 400 else ""))


try:
    original = (ROOT / "prompts" / "triage-v1.md").read_text(encoding="utf-8")
    # A realistic bad edit: someone renames the categories in the prompt but not in the schema.
    broken = original.replace("version: triage-v1", "version: triage-broken")
    broken = broken.replace("work | errands | health | finance | home | learning | other", "chores | admin")
    for cat in ("finance", "other"):
        broken = broken.replace(f'"category": "{cat}"', '"category": "chores"')
    broken = broken.replace("## Rules", "## Rules\n\n- The ONLY valid categories are chores and admin. "
                                        "Every bill or payment is \"chores\".", 1)
    BROKEN.write_text(broken, encoding="utf-8")
    scenario("Stage 3: prompt demands a category that is not in the enum -> repair once -> 422 + quarantine",
             {"LLM_PROMPT": "triage-broken"})
finally:
    BROKEN.unlink(missing_ok=True)

scenario("Stage 4: kill switch -> fallback, zero model calls", {"LLM_ENABLED": "false"})
scenario("Stage 4: wrong API key -> fails fast, a 401 is never retried",
         {"LLM_BASE_URL": "https://openrouter.ai/api/v1", "LLM_API_KEY": "sk-or-v1-this-is-not-a-real-key",
          "LLM_MODEL": "openrouter/free"})
scenario("Stage 4: model slower than the timeout -> retried with backoff -> 504",
         {"LLM_TIMEOUT_S": "0.5"})
scenario("Happy path again (real key/model, cache off)", {})
shutil.rmtree(ROOT / "__pycache__", ignore_errors=True)
