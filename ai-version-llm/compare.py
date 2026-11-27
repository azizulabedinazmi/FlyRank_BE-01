"""Run the same behaviour checks against any implementation of POST /tasks/triage.

    python ai-version-llm/compare.py <project_dir> --label "Mine"

The implementation is started with uvicorn (main:app) and pointed at mock_llm.py, a fake OpenAI-compatible server that
plays back one failure per check and COUNTS the calls it receives. So retries, timeouts and leaks are measured from
outside, not read from the code, and no real provider is touched.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = HERE.parent / ".venv" / "Scripts" / "python.exe"
SRC = Path(sys.argv[1]).resolve()
LABEL = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else SRC.name
MOCK, APP = 8099, 8098
MARKER = "MOCK-RAW-7Q2"
results = []


def http(method, url, body=None, timeout=200):
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                                 {"Content-Type": "application/json"}, method=method)
    t = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode(), time.monotonic() - t
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), time.monotonic() - t


def scenario(name):
    http("POST", f"http://127.0.0.1:{MOCK}/_scenario", {"name": name})


def calls():
    return json.loads(http("GET", f"http://127.0.0.1:{MOCK}/_calls")[1])


def start_app(extra_env):
    env = {**os.environ, "LLM_BASE_URL": f"http://127.0.0.1:{MOCK}/v1", "LLM_API_KEY": "mock-key",
           "LLM_MODEL": "mock-model", "LLM_STUB": "0", "LLM_ENABLED": "true", "LLM_CACHE": "0",
           "LLM_TIMEOUT_S": "30", "PYTHONIOENCODING": "utf-8", **extra_env}
    log = open(HERE / f"_app-{LABEL.replace(' ', '_')}.log", "a", encoding="utf-8")
    p = subprocess.Popen([str(PY), "-m", "uvicorn", "main:app", "--port", str(APP)], cwd=SRC, env=env,
                         stdout=log, stderr=subprocess.STDOUT)
    for _ in range(80):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{APP}/docs", timeout=1)
            return p
        except Exception:  # noqa: BLE001
            if p.poll() is not None:
                break
            time.sleep(0.5)
    p.kill()
    raise SystemExit(f"{LABEL}: app didn't start, see {log.name}")


def check(name, ok, detail):
    results.append((name, bool(ok), str(detail)))


def triage(text="electricity bill overdue, pay it today pls"):
    return http("POST", f"http://127.0.0.1:{APP}/tasks/triage", {"text": text})


def jsonl_files():
    return [p for p in SRC.rglob("*.jsonl") if "ai-version-llm" not in p.relative_to(SRC).parts]


sizes_before = {p: p.stat().st_size for p in jsonl_files()}  # only judge log lines written during THIS run
(HERE / f"_app-{LABEL.replace(' ', '_')}.log").unlink(missing_ok=True)
mock = subprocess.Popen([str(PY), str(HERE / "mock_llm.py"), str(MOCK)])
time.sleep(1)
app = start_app({})
try:
    scenario("good")
    s, b, _ = triage()
    body = json.loads(b) if b.startswith("{") else {}
    check("valid note -> 200 with the six fields", s == 200 and set(body) == {"title", "category", "priority",
          "confidence", "reason", "source"} and body.get("source") == "model", f"{s} {b[:90]}")

    scenario("good")
    bad_inputs = [{}, {"text": ""}, {"text": "x" * 1001}, {"txt": "hi"}, {"text": 7}]
    got = [triage_status for triage_status, *_ in [http("POST", f"http://127.0.0.1:{APP}/tasks/triage", bi) for bi in bad_inputs]]
    check("bad input -> 400 (the assignment's code)", all(c == 400 for c in got), got)
    check("bad input -> zero model calls", calls()["count"] == 0, f"{calls()['count']} calls")
    s, b, _ = http("POST", f"http://127.0.0.1:{APP}/tasks/triage", {"txt": "hi"})
    check("bad input error names the field", "text" in b, b[:100])

    scenario("fenced")
    s, b, _ = triage()
    check("fenced / chatty JSON is parsed", s == 200, f"{s} {b[:60]}")

    scenario("bad_then_good")
    s, b, _ = triage()
    c = calls()
    last_user = json.dumps(c["last_messages"][-1][-1]) if c["count"] >= 2 else ""
    check("invalid answer -> one repair -> 200", s == 200 and c["count"] == 2, f"{s}, {c['count']} calls")
    check("repair hands the model its error", "categor" in last_user.lower(), last_user[:120])

    scenario("bad_always")
    s, b, _ = triage()
    check("invalid twice -> 422 after exactly 2 calls", s == 422 and calls()["count"] == 2, f"{s}, {calls()['count']} calls")
    check("raw model text never returned (bad answer)", MARKER not in b, b[:120])

    scenario("refusal")
    s, b, _ = triage()
    check("refusal -> clean error, no raw text", s in (422, 502) and MARKER not in b, f"{s} {b[:100]}")

    scenario("auth")
    s, b, _ = triage()
    check("401 is never retried (1 call)", calls()["count"] == 1, f"{calls()['count']} calls, HTTP {s}")
    check("401 -> clean error, process alive", s in (500, 502, 503) and b.startswith("{"), f"{s} {b[:80]}")

    scenario("server_error")
    s, b, secs = triage()
    n = calls()["count"]
    check("500 retried, but bounded (2-4 calls)", 2 <= n <= 4, f"{n} calls in {secs:.1f}s, HTTP {s}")

    scenario("rate_limited")
    s, b, _ = triage()
    check("429 + Retry-After -> retried -> 200", s == 200 and calls()["count"] == 2, f"{s}, {calls()['count']} calls")

    scenario("slow")  # the mock stalls 70 s: a real timeout (<= 60 s) must fire first
    s, b, secs = triage()
    # Passing = the caller never sat through the 70 s stall: a timeout fired (then maybe a retry answered fast).
    check("timeout <= 60 s fires (mock stalls 70 s)", secs < 65, f"HTTP {s} after {secs:.0f}s, {calls()['count']} calls")
finally:
    app.terminate()
    app.wait()

for name, env in [("stub", {"LLM_STUB": "1"}), ("kill switch", {"LLM_ENABLED": "false"})]:
    app = start_app(env)
    try:
        scenario("good")
        s, b, _ = triage()
        body = json.loads(b) if b.startswith("{") else {}
        check(f"{name} -> 200, schema-shaped, zero model calls", s == 200 and calls()["count"] == 0 and
              body.get("category") in {"work", "errands", "health", "finance", "home", "learning", "other"},
              f"{s} source={body.get('source')} calls={calls()['count']}")
    finally:
        app.terminate()
        app.wait()

mock.terminate()
new_text = {p: p.read_bytes()[sizes_before.get(p, 0):].decode("utf-8", "ignore") for p in jsonl_files()}
app_log = HERE / f"_app-{LABEL.replace(' ', '_')}.log"  # JSON lines on stdout count too: that's a valid choice
if app_log.exists():
    new_text[app_log] = app_log.read_text(encoding="utf-8", errors="ignore")
logged = [p for p, t in new_text.items() if '"111"' in t or ": 111" in t]  # the mock always reports 111 input tokens
check("every call logged with token counts", logged, ", ".join(p.name for p in logged) or
      "no new token counts in any .jsonl")

print(f"## {LABEL}\n\n| Check | Result | Detail |\n|---|---|---|")
for name, ok, detail in results:
    print(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail.replace('|', '/')[:110]} |")
print(f"\n**{sum(ok for _, ok, _ in results)}/{len(results)} passed**")
