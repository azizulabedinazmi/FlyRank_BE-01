Build me a to-do list REST API in Python using FastAPI, all in one file called main.py, run with `uvicorn main:app` on port 8000.

Storage
- Keep the tasks in memory in a Python list (no database, no files). Start with 3 example tasks.
- Each task is {"id": int, "title": str, "done": bool}.
- New ids come from a counter, so a deleted task's id is never reused.

Endpoints
- GET / -> {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}
- GET /health -> {"status": "ok"}
- GET /tasks -> 200, list of all tasks
- GET /tasks/{id} -> 200, one task
- POST /tasks with body {"title": "..."} -> 201 and the created task (server sets id, done = false; any other fields in the body are ignored)
- PUT /tasks/{id} with body containing title, done, or both -> 200 and the updated task
- DELETE /tasks/{id} -> 204 with an empty body

Validation (the server never trusts the client)
- POST: title must be present, must be a JSON string (not a number), and cannot be empty or only spaces. Trim spaces.
- PUT: the body must contain at least one of title or done. An empty body {} is a 400, not a silent no-op. If title is sent it follows the POST rules. done must be a real JSON boolean: "yes", "true", 1 or 0 must be rejected (no type coercion).
- Malformed JSON and a non-numeric id like /tasks/abc are also 400.

Errors
- 400 for any invalid input, 404 for an unknown id. Never use 422.
- Every error body has exactly this shape: {"error": "<one human-readable sentence>"}, for example {"error": "Task 99 not found"}. No extra keys.

Docs
- Swagger UI at /docs. Give each endpoint a short summary.
- The OpenAPI docs must match the real behaviour: document the 400 and 404 responses with the {"error": ...} schema, and do not list a 422 response anywhere.
