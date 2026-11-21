"""Week 3 checkpoints, run against any version of the SQLite Task API.

Starts the server itself (so it can restart it), from a fresh tasks.db, and checks the
Stage 0-3 checkpoints plus the Week 2 test suite.

Usage:  python ai-version-db/db_checkpoint.py <folder containing main.py> [port]
        python ai-version-db/db_checkpoint.py .              # my version
        python ai-version-db/db_checkpoint.py ai-version-db/v1
"""
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path

APP_DIR = Path(sys.argv[1]).resolve()
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8010
BASE = f"http://127.0.0.1:{PORT}"
DB = APP_DIR / "tasks.db"
CHECKPOINT = Path(__file__).resolve().parent.parent / "ai-version" / "checkpoint.py"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            text = r.read().decode()
            return r.status, json.loads(text) if text else None
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        return e.code, json.loads(text) if text else None


class Server:
    proc = None

    def start(self):
        env = {k: v for k, v in os.environ.items() if k != "TASKS_DB"}
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--port", str(PORT)],
            cwd=APP_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        for _ in range(80):
            try:
                urllib.request.urlopen(BASE + "/health", timeout=1)
                return True
            except Exception:
                if self.proc.poll() is not None:
                    print("Server failed to start:\n" + self.proc.stderr.read().decode()[-1500:])
                    return False
                time.sleep(0.25)
        return False

    def stop(self):
        self.proc.terminate()
        self.proc.wait()

    def restart(self):
        self.stop()
        return self.start()


results = []


def wipe_db():
    for f in APP_DIR.glob("tasks.db*"):
        for _ in range(20):
            try:
                f.unlink()
                break
            except PermissionError:  # Windows: the stopped server may still hold the file a moment
                time.sleep(0.25)


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


wipe_db()

srv = Server()
if not srv.start():
    sys.exit(1)

# Stage 0: database, table and seed
check("tasks.db created on first start", DB.exists())
status, tasks = call("GET", "/tasks")
check("3 seeded tasks on first start", status == 200 and len(tasks) == 3, f"{len(tasks)} tasks")
srv.restart()
srv.restart()
status, tasks = call("GET", "/tasks")
check("still 3 tasks after 2 restarts (seed runs once)", len(tasks) == 3, f"{len(tasks)} tasks")

# Stage 1: reads come from the database (change the file directly, the API sees it)
with closing(sqlite3.connect(DB)) as conn, conn:
    conn.execute("UPDATE tasks SET title = 'edited in SQL' WHERE id = 1")
status, task = call("GET", "/tasks/1")
check("API reflects a direct SQL edit with no restart", task and task.get("title") == "edited in SQL")
status, body = call("GET", "/tasks/999")
check("unknown id -> 404 + {\"error\": ...}", status == 404 and isinstance(body, dict) and "error" in body, json.dumps(body))

# Stage 2: create persists across a restart
status, created = call("POST", "/tasks", {"title": "Buy milk"})
check("POST -> 201", status == 201, json.dumps(created))
srv.restart()
status, task = call("GET", f"/tasks/{created['id']}")
check("created task survives a restart", status == 200 and task["title"] == "Buy milk")

# Stage 3: update persists, delete works, booleans stay booleans
status, task = call("PUT", f"/tasks/{created['id']}", {"done": True})
srv.restart()
status, task = call("GET", f"/tasks/{created['id']}")
check("PUT done=true survives a restart", status == 200 and task["done"] is True, json.dumps(task))
check("done comes back as JSON true, not 1", type(task["done"]) is bool, repr(task["done"]))
with closing(sqlite3.connect(DB)) as conn, conn:
    stored = conn.execute("SELECT done FROM tasks WHERE id = ?", (created["id"],)).fetchone()[0]
check("done is stored as 0/1 in the table", stored in (0, 1), repr(stored))
status, _ = call("DELETE", f"/tasks/{created['id']}")
check("DELETE -> 204", status == 204)
status, _ = call("DELETE", f"/tasks/{created['id']}")
check("DELETE again -> 404", status == 404)

# Ids: a deleted newest id must not be handed to a new task
status, a = call("POST", "/tasks", {"title": "newest"})
call("DELETE", f"/tasks/{a['id']}")
status, b = call("POST", "/tasks", {"title": "after delete"})
check("deleted id is never reused", b["id"] != a["id"], f"deleted {a['id']}, new task got {b['id']}")

# Parameterized queries: SQL in a title is stored as plain text
evil = "x'); DROP TABLE tasks; --"
status, t = call("POST", "/tasks", {"title": evil})
status, tasks = call("GET", "/tasks")
check("SQL in a title is stored literally", status == 200 and any(x["title"] == evil for x in tasks))

srv.stop()

# Week 2 suite, unchanged, on a fresh database
wipe_db()
srv.start()
out = subprocess.run([sys.executable, str(CHECKPOINT), BASE], capture_output=True, text=True).stdout
srv.stop()
summary = out.strip().splitlines()[-1]
check("Week 2 checkpoint suite", summary.startswith("19/19"), summary)
failed = [line for line in out.splitlines() if "FAIL" in line]

wipe_db()

print(f"Testing {APP_DIR.name or APP_DIR}\n")
print("| Check | Result | Detail |\n|---|---|---|")
for name, ok, detail in results:
    print(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
if failed:
    print("\nWeek 2 suite failures:\n" + "\n".join(failed))
print(f"\n{sum(ok for _, ok, _ in results)}/{len(results)} passed")
