Testing http://127.0.0.1:8001

| Test | Expected | Got | Body |
|---|---|---|---|
| GET /health | 200 | 200 PASS | `{"status":"ok"}` |
| GET /tasks | 200 | 200 PASS | `[{"id":1,"title":"Learn FastAPI","done":true},{"id":2,"title":"Build a` |
| GET /tasks/1 | 200 | 200 PASS | `{"id":1,"title":"Learn FastAPI","done":true}` |
| GET /tasks/99 (unknown) | 404 | 404 PASS | `{"error":"Task 99 not found"}` |
| POST valid title | 201 | 201 PASS | `{"id":4,"title":"Buy milk","done":false}` |
| POST {} | 400 | 400 PASS | `{"error":"Title is required and cannot be empty"}` |
| POST title "" | 400 | 400 PASS | `{"error":"Title is required and cannot be empty"}` |
| POST title "   " | 400 | 400 PASS | `{"error":"Title is required and cannot be empty"}` |
| POST title 123 (number) | 400 | 400 PASS | `{"error":"Invalid request","details":[{"field":"title","message":"Inpu` |
| POST invalid JSON | 400 | 400 PASS | `{"error":"Invalid request","details":[{"field":"0","message":"JSON dec` |
| PUT title | 200 | 200 PASS | `{"id":1,"title":"Buy oat milk","done":true}` |
| PUT done=true | 200 | 200 PASS | `{"id":1,"title":"Buy oat milk","done":true}` |
| PUT {} | 400 | 200 FAIL | `{"id":1,"title":"Buy oat milk","done":true}` |
| PUT title "" | 400 | 400 PASS | `{"error":"Title is required and cannot be empty"}` |
| PUT done="yes" | 400 | 200 FAIL | `{"id":1,"title":"Buy oat milk","done":true}` |
| PUT /tasks/99 (unknown) | 404 | 404 PASS | `{"error":"Task 99 not found"}` |
| GET /tasks/abc (bad id) | 400 | 400 PASS | `{"error":"Invalid request","details":[{"field":"path.task_id","message` |
| DELETE /tasks/1 | 204 | 204 PASS | `(empty)` |
| DELETE /tasks/1 again | 404 | 404 PASS | `{"error":"Task 1 not found"}` |

17/19 passed
