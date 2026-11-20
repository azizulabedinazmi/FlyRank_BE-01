Testing http://127.0.0.1:8002

| Test | Expected | Got | Body |
|---|---|---|---|
| GET /health | 200 | 200 PASS | `{"status":"ok"}` |
| GET /tasks | 200 | 200 PASS | `[{"id":1,"title":"Buy groceries","done":false},{"id":2,"title":"Write ` |
| GET /tasks/1 | 200 | 200 PASS | `{"id":1,"title":"Buy groceries","done":false}` |
| GET /tasks/99 (unknown) | 404 | 404 PASS | `{"error":"Task 99 not found"}` |
| POST valid title | 201 | 201 PASS | `{"id":4,"title":"Buy milk","done":false}` |
| POST {} | 400 | 400 PASS | `{"error":"title is required"}` |
| POST title "" | 400 | 400 PASS | `{"error":"title cannot be empty"}` |
| POST title "   " | 400 | 400 PASS | `{"error":"title cannot be empty"}` |
| POST title 123 (number) | 400 | 400 PASS | `{"error":"title must be a string"}` |
| POST invalid JSON | 400 | 400 PASS | `{"error":"Request body must be valid JSON"}` |
| PUT title | 200 | 200 PASS | `{"id":1,"title":"Buy oat milk","done":false}` |
| PUT done=true | 200 | 200 PASS | `{"id":1,"title":"Buy oat milk","done":true}` |
| PUT {} | 400 | 400 PASS | `{"error":"Body must contain title, done, or both"}` |
| PUT title "" | 400 | 400 PASS | `{"error":"title cannot be empty"}` |
| PUT done="yes" | 400 | 400 PASS | `{"error":"done must be a boolean (true or false)"}` |
| PUT /tasks/99 (unknown) | 404 | 404 PASS | `{"error":"Task 99 not found"}` |
| GET /tasks/abc (bad id) | 400 | 400 PASS | `{"error":"Task id must be a number"}` |
| DELETE /tasks/1 | 204 | 204 PASS | `(empty)` |
| DELETE /tasks/1 again | 404 | 404 PASS | `{"error":"Task 1 not found"}` |

19/19 passed
