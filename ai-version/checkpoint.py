"""Run the Stage 3/4 checkpoint requests against a running API and print a results table.

Usage:  python ai-version/checkpoint.py http://localhost:8001
"""
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"


def call(method, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# (name, method, path, body, raw_bytes, expected status)
TESTS = [
    ("GET /health", "GET", "/health", None, None, 200),
    ("GET /tasks", "GET", "/tasks", None, None, 200),
    ("GET /tasks/1", "GET", "/tasks/1", None, None, 200),
    ("GET /tasks/99 (unknown)", "GET", "/tasks/99", None, None, 404),
    ("POST valid title", "POST", "/tasks", {"title": "Buy milk"}, None, 201),
    ("POST {}", "POST", "/tasks", {}, None, 400),
    ('POST title ""', "POST", "/tasks", {"title": ""}, None, 400),
    ('POST title "   "', "POST", "/tasks", {"title": "   "}, None, 400),
    ("POST title 123 (number)", "POST", "/tasks", {"title": 123}, None, 400),
    ("POST invalid JSON", "POST", "/tasks", None, b"not json", 400),
    ("PUT title", "PUT", "/tasks/1", {"title": "Buy oat milk"}, None, 200),
    ("PUT done=true", "PUT", "/tasks/1", {"done": True}, None, 200),
    ("PUT {}", "PUT", "/tasks/1", {}, None, 400),
    ('PUT title ""', "PUT", "/tasks/1", {"title": ""}, None, 400),
    ('PUT done="yes"', "PUT", "/tasks/1", {"done": "yes"}, None, 400),
    ("PUT /tasks/99 (unknown)", "PUT", "/tasks/99", {"done": True}, None, 404),
    ("GET /tasks/abc (bad id)", "GET", "/tasks/abc", None, None, 400),
    ("DELETE /tasks/1", "DELETE", "/tasks/1", None, None, 204),
    ("DELETE /tasks/1 again", "DELETE", "/tasks/1", None, None, 404),
]

passed = 0
print(f"Testing {BASE}\n")
print(f"| Test | Expected | Got | Body |\n|---|---|---|---|")
for name, method, path, body, raw, expected in TESTS:
    status, text = call(method, path, body, raw)
    ok = status == expected
    passed += ok
    short = text.replace("\n", " ")[:70] or "(empty)"
    print(f"| {name} | {expected} | {status} {'PASS' if ok else 'FAIL'} | `{short}` |")
print(f"\n{passed}/{len(TESTS)} passed")
