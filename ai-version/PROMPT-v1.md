Build me a to-do list REST API in Python using FastAPI.

- Keep the tasks in memory in a Python list (no database, no files). Start with 3 example tasks.
- Each task has an id (number), a title (text) and done (true/false).
- Endpoints:
  - GET / returns a short JSON description of the API
  - GET /health returns {"status": "ok"}
  - GET /tasks returns all tasks
  - GET /tasks/{id} returns one task
  - POST /tasks creates a task from {"title": "..."}; the server picks the next id and sets done to false
  - PUT /tasks/{id} updates the title and/or done
  - DELETE /tasks/{id} deletes a task
- Status codes: 200 for reads and updates, 201 for create, 204 for delete, 404 if the id doesn't exist, 400 if the title is missing or empty.
- Errors should be returned as JSON.
- I want Swagger UI at /docs.
- Put everything in one file called main.py.
