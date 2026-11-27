"""A tiny fake OpenAI-compatible server for testing LLM integrations from the outside.

POST /v1/chat/completions   plays the current scenario and counts the call
POST /_scenario {"name": ...} switches scenario and resets the counters
GET  /_calls                -> {"count": n, "last_messages": [...]} (the messages of every call)
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GOOD = {"title": "Pay the electricity bill", "category": "finance", "priority": "high", "confidence": 0.9,
        "reason": "A bill that is overdue."}
MARKER = "MOCK-RAW-7Q2"  # appears only in deliberately bad answers: if a caller ever sees it, raw model text leaked
BAD = json.dumps({**GOOD, "category": f"bills-{MARKER}"})
REFUSAL = f"I'm sorry, but I can't help with that request. ({MARKER})"

# Each scenario is a list of steps; the last step repeats forever.
SCENARIOS = {
    "good": [("json", json.dumps(GOOD))],
    "fenced": [("json", "Sure! Here is the JSON:\n```json\n" + json.dumps(GOOD) + "\n```")],
    "bad_then_good": [("json", BAD), ("json", json.dumps(GOOD))],
    "bad_always": [("json", BAD)],
    "refusal": [("json", REFUSAL)],
    "auth": [("status", 401)],
    "server_error": [("status", 500)],
    "rate_limited": [("status", 429), ("json", json.dumps(GOOD))],
    "slow": [("sleep", 70), ("json", json.dumps(GOOD))],
}
state = {"name": "good", "count": 0, "messages": []}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, status: int, body: dict, headers: dict | None = None) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/_calls":
            self._send(200, {"scenario": state["name"], "count": state["count"], "last_messages": state["messages"]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/_scenario":
            state.update(name=body["name"], count=0, messages=[])
            self._send(200, {"ok": True})
            return
        if not self.path.endswith("/chat/completions"):
            self._send(404, {"error": {"message": "not found"}})
            return
        state["count"] += 1
        state["messages"].append(body.get("messages"))
        steps = SCENARIOS[state["name"]]
        kind, arg = steps[min(state["count"] - 1, len(steps) - 1)]
        if kind == "sleep":
            time.sleep(arg)
            kind, arg = "json", json.dumps(GOOD)
        if kind == "status":
            headers = {"Retry-After": "1"} if arg == 429 else {}
            self._send(arg, {"error": {"message": f"mock HTTP {arg}", "type": "mock"}}, headers)
            return
        self._send(200, {"id": "mock-1", "object": "chat.completion", "created": int(time.time()), "model": "mock-model",
                         "choices": [{"index": 0, "message": {"role": "assistant", "content": arg},
                                      "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 111, "completion_tokens": 22, "total_tokens": 133}})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
