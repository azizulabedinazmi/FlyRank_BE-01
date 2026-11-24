"""A3 checkpoint for any compose project: static checks + a real `docker compose up` from a clean copy.

Usage:  python ai-version-compose/compose_checkpoint.py <project_dir> [port]
        python ai-version-compose/compose_checkpoint.py .                      # my own stack
        python ai-version-compose/compose_checkpoint.py ai-version-compose/v1

It copies the project to a temp folder (like a stranger's clone, no .env), runs `cp .env.example .env`,
`docker compose up -d --build` under its own project name, then tears everything down with `-v`.
Stop any other stack using the same ports first.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import types

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]).resolve()
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
BASE = f"http://127.0.0.1:{PORT}"
PROJECT = "a3check"

# Reuse the Week 2 suite unchanged: take call() and TESTS from ai-version/checkpoint.py without running its loop.
_src = (ROOT / "ai-version" / "checkpoint.py").read_text(encoding="utf-8").split("\npassed = 0")[0]
checkpoint = types.ModuleType("checkpoint")
checkpoint.__dict__["sys"] = types.SimpleNamespace(argv=["x", BASE])
exec(compile(_src.replace("import sys\n", ""), "checkpoint.py", "exec"), checkpoint.__dict__)
IGNORE = shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.db", ".env", "ai-version*", "docs")

results = []  # (check, ok, detail)


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def sh(*args, cwd, timeout=600):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def wait_ready(timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(BASE + "/tasks", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def get_json(path):
    status, text = checkpoint.call("GET", path)
    try:
        return status, json.loads(text) if text else None
    except json.JSONDecodeError:
        return status, text


# ---------------------------------------------------------------- static checks
compose_file = next((SRC / n for n in ("compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml")
                     if (SRC / n).exists()), None)
check("compose file exists", compose_file, compose_file.name if compose_file else "none")
compose = compose_file.read_text(encoding="utf-8") if compose_file else ""
check(".env.example exists", (SRC / ".env.example").exists())
check("Dockerfile exists", (SRC / "Dockerfile").exists())

pw_lines = [l.strip() for l in compose.splitlines() if re.search(r"POSTGRES_PASSWORD\s*[:=]", l)]
hard = [l for l in pw_lines if "${" not in l and "env_file" not in l]
py_creds = []
for f in SRC.rglob("*.py"):
    if {".venv", "ai-version", "ai-version-db", "ai-version-compose"} & set(f.relative_to(SRC).parts):
        continue  # third-party packages and other experiments are not this project's code
    for m in re.finditer(r"postgres(?:ql)?://[^\s\"'$/]+:[^\s\"'@$]+@", f.read_text(encoding="utf-8")):
        py_creds.append(f"{f.name}: {m.group(0)}")
check("no hardcoded password in compose", not hard, "; ".join(hard) or "uses ${...} / env_file")
check("no hardcoded credentials in .py", not py_creds, "; ".join(py_creds) or "none")

main_py = (SRC / "main.py").read_text(encoding="utf-8") if (SRC / "main.py").exists() else ""
sql_in_main = re.findall(r"\b(SELECT .+? FROM|INSERT INTO|UPDATE \w+ SET|DELETE FROM|CREATE TABLE)\b", main_py)
check("routes contain no SQL (one repository module)", not sql_in_main,
      f"{len(sql_in_main)} SQL statements in main.py" if sql_in_main else "SQL lives outside main.py")
check("connects with one DATABASE_URL connection string", "DATABASE_URL" in compose and (SRC / ".env.example").exists()
      and "DATABASE_URL" in (SRC / ".env.example").read_text(encoding="utf-8"), "")

dockerignore = (SRC / ".dockerignore").read_text(encoding="utf-8") if (SRC / ".dockerignore").exists() else ""
check(".env kept out of the image (.dockerignore)", re.search(r"^\.env\b", dockerignore, re.M),
      ".dockerignore lists .env" if dockerignore else "no .dockerignore: COPY . . bakes .env into the image")
gitignore = (SRC / ".gitignore").read_text(encoding="utf-8") if (SRC / ".gitignore").exists() else ""
check(".env git-ignored", re.search(r"^\.env\b", gitignore, re.M), "" if gitignore else "no .gitignore shipped")

image = re.search(r"image:\s*[\"']?(postgres[^\s\"']*)", compose)
image = image.group(1) if image else "?"
check("postgres image version pinned", ":" in image and not image.endswith(":latest"), image)
check("api uses service name, not localhost", not re.search(r"@localhost[:/]", compose), "")
check("named volume for the database", re.search(r"/var/lib/postgresql", compose), "")
check("waits for a healthy db", "service_healthy" in compose,
      "depends_on: condition: service_healthy" if "service_healthy" in compose else "plain depends_on (start order only)")

# ---------------------------------------------------------------- dynamic checks
work = Path(tempfile.mkdtemp(prefix="a3check-")) / "proj"
shutil.copytree(SRC, work, ignore=IGNORE)
shutil.copy(work / ".env.example", work / ".env")
sh("docker", "compose", "-p", PROJECT, "down", "-v", cwd=work)
t0 = time.time()
code, out = sh("docker", "compose", "-p", PROJECT, "up", "-d", "--build", cwd=work)
ready = code == 0 and wait_ready()
check("clean clone: cp .env.example .env && docker compose up works", ready,
      f"ready in {time.time() - t0:.0f}s" if ready else out[-600:])

try:
    if ready:
        passed = 0
        fails = []
        for name, method, path, body, raw, expected in checkpoint.TESTS:
            status, text = checkpoint.call(method, path, body, raw)
            if status == expected:
                passed += 1
            else:
                fails.append(f"{name}: expected {expected}, got {status} {text[:60]}")
        check(f"Week 2 suite {passed}/{len(checkpoint.TESTS)}", passed == len(checkpoint.TESTS), "; ".join(fails))

        _, tasks = get_json("/tasks")
        check("GET /tasks shape [{id,title,done}]",
              isinstance(tasks, list) and all(set(t) == {"id", "title", "done"} for t in tasks), "")
        s, body = get_json("/tasks?search=MILK")
        check("?search is case-insensitive (like SQLite LIKE)", s == 200 and len(body) == 1, f"{s} {body}")
        s, body = get_json("/tasks?search=100%25")
        check("?search=100% treats % literally", s == 200 and body == [], f"{s} {body}")
        s, body = get_json("/tasks?sort=title")
        titles = [t["title"] for t in body] if s == 200 else []
        check("?sort=title is case-insensitive", titles == sorted(titles, key=str.lower), f"{titles}")
        s, body = get_json("/stats")
        check("/stats same shape", s == 200 and set(body) == {"total", "done", "open"}, f"{s} {body}")
        s, body = get_json("/tasks/99999999999999999999")
        check("huge id -> 404 (not 500)", s == 404, f"{s} {str(body)[:80]}")

        # persistence across a full down/up
        checkpoint.call("POST", "/tasks", {"title": "Survive the restart"})
        _, before = get_json("/tasks")
        sh("docker", "compose", "-p", PROJECT, "down", cwd=work)
        sh("docker", "compose", "-p", PROJECT, "up", "-d", cwd=work)
        up_again = wait_ready()
        _, after = get_json("/tasks") if up_again else (None, None)
        check("data survives docker compose down + up", up_again and after == before,
              f"{len(before)} rows before, {len(after) if after else 0} after")

        # seed runs once
        sh("docker", "compose", "-p", PROJECT, "restart", cwd=work)
        wait_ready()
        _, again = get_json("/tasks")
        check("seed not repeated after restart", again == before, f"{len(again or [])} rows")

        # deleted ids are not reused
        _, created = get_json("/tasks")
        last = max(t["id"] for t in created)
        checkpoint.call("DELETE", f"/tasks/{last}")
        _, new_text = checkpoint.call("POST", "/tasks", {"title": "id reuse probe"})
        new_id = json.loads(new_text)["id"]
        check("deleted id never reused", new_id != last, f"deleted {last}, new task got {new_id}")

        # health reflects the database
        sh("docker", "compose", "-p", PROJECT, "stop", "db", cwd=work)
        time.sleep(2)
        try:
            s, body = get_json("/health")
        except Exception as e:  # noqa: BLE001
            s, body = "error", str(e)
        check("/health notices the database is down", s != 200, f"{s} {body}")
        sh("docker", "compose", "-p", PROJECT, "start", "db", cwd=work)

        code, size = sh("docker", "images", "--format", "{{.Repository}} {{.Size}}", cwd=work)
        results.append(("image size", True, " | ".join(l for l in size.splitlines() if PROJECT in l)))
finally:
    sh("docker", "compose", "-p", PROJECT, "down", "-v", "--rmi", "local", cwd=work)
    shutil.rmtree(work.parent, ignore_errors=True)

print(f"Testing {SRC.name} ({SRC})\n")
print("| Check | Result | Detail |\n|---|---|---|")
for name, ok, detail in results:
    print(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail.replace('|', '/')} |")
scored = [r for r in results if r[0] != "image size"]
print(f"\n{sum(ok for _, ok, _ in scored)}/{len(scored)} passed")
