"""Run the hand-labelled eval set through the real endpoint and score it.

    python evals/run_eval.py                       # all 25 cases against http://127.0.0.1:8000
    python evals/run_eval.py --core                # only the 8 core cases (8 model calls)
    python evals/run_eval.py --url http://127.0.0.1:8001 --label "llama3.2:3b / triage-v2"

The key field is `category`; `priority` is scored too (where a case labels it). Attack cases also pass only if the
answer holds: right category and none of the forbidden strings in the title or reason.
Results are saved to evals/results/<date>_<label>.json so two runs can be compared later.
"""
import argparse
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://127.0.0.1:8000")
ap.add_argument("--core", action="store_true", help="only the 8 core cases")
ap.add_argument("--label", default="", help="what was tested, e.g. 'llama3.2:3b / triage-v1'")
args = ap.parse_args()

cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
if args.core:
    cases = [c for c in cases if c["core"]]


def triage(text: str) -> tuple[int, dict, float]:
    req = urllib.request.Request(args.url.rstrip("/") + "/tasks/triage", json.dumps({"text": text}).encode(),
                                 {"Content-Type": "application/json"}, method="POST")
    t = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read()), time.monotonic() - t
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:  # e.g. a plain-text 500 from a crashed server: record it, keep going
            body = {"error": raw.decode("utf-8", "replace")[:200]}
        return e.code, body, time.monotonic() - t


rows = []
for c in cases:
    status, body, secs = triage(c["text"])
    got_cat, got_pri = body.get("category"), body.get("priority")
    cat_ok = status == 200 and got_cat == c["category"]
    pri_ok = None if c.get("priority") is None else (status == 200 and got_pri == c["priority"])
    notes = []
    if c.get("max_confidence") is not None and status == 200 and body.get("confidence", 1) >= c["max_confidence"]:
        notes.append(f"confidence {body.get('confidence')} >= {c['max_confidence']} (when-unsure rule)")
    leaked = [s for s in c.get("must_not_contain", []) if s.lower() in (body.get("title", "") + " " + body.get("reason", "")).lower()]
    if leaked:
        notes.append(f"contains {leaked}")
    held = (cat_ok and not leaked) if c.get("attack") else None
    rows.append({"id": c["id"], "difficulty": c["difficulty"], "core": c["core"], "attack": bool(c.get("attack")),
                 "text": c["text"], "expected": [c["category"], c.get("priority")], "status": status,
                 "got": [got_cat, got_pri], "confidence": body.get("confidence"), "title": body.get("title"),
                 "source": body.get("source"), "error": body.get("error"), "category_ok": cat_ok,
                 "priority_ok": pri_ok, "attack_held": held, "notes": notes, "seconds": round(secs, 2)})
    mark = "PASS" if cat_ok else "FAIL"
    print(f"[{mark}] #{c['id']:>2} {c['difficulty']:<4} {status} {str(got_cat):<9} {str(got_pri):<7} "
          f"(want {c['category']}/{c.get('priority')}) {secs:5.1f}s  {c['text'][:48]}"
          + (f"  ! {'; '.join(notes)}" if notes else "") + (f"  ! {body.get('error')}" if status != 200 else ""))


def pct(xs):
    xs = [x for x in xs if x is not None]
    return (sum(xs), len(xs), round(100 * sum(xs) / len(xs)) if xs else 0)


summary = {
    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "label": args.label, "cases": len(rows),
    "category": pct([r["category_ok"] for r in rows]),
    "priority": pct([r["priority_ok"] for r in rows]),
    "both": pct([r["category_ok"] and r["priority_ok"] is not False for r in rows]),
    "core_category": pct([r["category_ok"] for r in rows if r["core"]]),
    "easy_category": pct([r["category_ok"] for r in rows if r["difficulty"] == "easy"]),
    "hard_category": pct([r["category_ok"] for r in rows if r["difficulty"] == "hard"]),
    "attacks_held": pct([r["attack_held"] for r in rows if r["attack"]]),
    "non_200": sum(r["status"] != 200 for r in rows),
    "median_seconds": sorted(r["seconds"] for r in rows)[len(rows) // 2],
    "failed_ids": [r["id"] for r in rows if not r["category_ok"]],
}
print("\n" + "\n".join(f"{k:>15}: {f'{v[0]}/{v[1]} ({v[2]}%)' if isinstance(v, tuple) else v}" for k, v in summary.items()))

out = HERE / "results"
out.mkdir(exist_ok=True)
name = re.sub(r"[^A-Za-z0-9.]+", "-", f"{datetime.now():%Y-%m-%d_%H%M}_{args.label or 'run'}").strip("-")
(out / f"{name}.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False) + "\n",
                                  encoding="utf-8")
print(f"\nsaved evals/results/{name}.json")
