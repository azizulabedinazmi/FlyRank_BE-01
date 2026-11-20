Testing http://127.0.0.1:8000

| Test | Expected | Got | Body |
|---|---|---|---|
| GET /health | 200 | 200 PASS | `{"status":"ok"}` |
| GET /tasks | 200 | 200 PASS | `[{"id":1,"title":"Learn HTTP methods","done":true},{"id":2,"title":"Bu` |
| GET /tasks/1 | 200 | 200 PASS | `{"id":1,"title":"Learn HTTP methods","done":true}` |
| GET /tasks/99 (unknown) | 404 | 404 PASS | `{"error":"Task 99 not found"}` |
| POST valid title | 201 | 201 PASS | `{"id":4,"title":"Buy milk","done":false}` |
| POST {} | 400 | 400 PASS | `{"error":"title is required and cannot be empty"}` |
| POST title "" | 400 | 400 PASS | `{"error":"title is required and cannot be empty"}` |
| POST title "   " | 400 | 400 PASS | `{"error":"title is required and cannot be empty"}` |
| POST title 123 (number) | 400 | 400 PASS | `{"error":"Invalid title: Input should be a valid string"}` |
| POST invalid JSON | 400 | 400 PASS | `{"error":"Invalid body: JSON decode error"}` |
| PUT title | 200 | 200 PASS | `{"id":1,"title":"Buy oat milk","done":true}` |
| PUT done=true | 200 | 200 PASS | `{"id":1,"title":"Buy oat milk","done":true}` |
| PUT {} | 400 | 400 PASS | `{"error":"send at least one of: title, done"}` |
| PUT title "" | 400 | 400 PASS | `{"error":"title cannot be empty"}` |
| PUT done="yes" | 400 | 400 PASS | `{"error":"Invalid done: Input should be a valid boolean"}` |
| PUT /tasks/99 (unknown) | 404 | 404 PASS | `{"error":"Task 99 not found"}` |
| GET /tasks/abc (bad id) | 400 | 400 PASS | `{"error":"Invalid task_id: Input should be a valid integer, unable to ` |
| DELETE /tasks/1 | 204 | 204 PASS | `(empty)` |
| DELETE /tasks/1 again | 404 | 404 PASS | `{"error":"Task 1 not found"}` |

19/19 passed
