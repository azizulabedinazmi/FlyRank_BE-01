Testing v1

| Check | Result | Detail |
|---|---|---|
| tasks.db created on first start | PASS |  |
| 3 seeded tasks on first start | PASS | 3 tasks |
| still 3 tasks after 2 restarts (seed runs once) | PASS | 3 tasks |
| API reflects a direct SQL edit with no restart | PASS |  |
| unknown id -> 404 + {"error": ...} | PASS | {"error": "Task 999 not found"} |
| POST -> 201 | PASS | {"id": 4, "title": "Buy milk", "done": false} |
| created task survives a restart | PASS |  |
| PUT done=true survives a restart | PASS | {"id": 4, "title": "Buy milk", "done": true} |
| done comes back as JSON true, not 1 | PASS | True |
| done is stored as 0/1 in the table | PASS | 1 |
| DELETE -> 204 | PASS |  |
| DELETE again -> 404 | PASS |  |
| deleted id is never reused | FAIL | deleted 4, new task got 4 |
| SQL in a title is stored literally | PASS |  |
| Week 2 checkpoint suite | PASS | 19/19 passed |

14/15 passed
