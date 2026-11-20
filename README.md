# Task API

A small to-do list API built with **Python + FastAPI**. It supports the four CRUD operations
(create, read, update, delete) on tasks and has interactive documentation through Swagger UI.

Tasks are kept **in memory** (a Python list). There is no database, so all changes are lost
when the server stops.

FlyRank Internship · Backend Track · Week 2 · Assignment A1 (BE-01)

## Run it

You need Python 3.10 or newer.

```bash
git clone https://github.com/azizulabedinazmi/FlyRank_BE-01.git
cd FlyRank_BE-01
python -m venv .venv
```

Activate the virtual environment:

- Windows: `.venv\Scripts\activate`
- macOS / Linux: `source .venv/bin/activate`

Install dependencies and start the server:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at http://localhost:8000. Swagger UI is at http://localhost:8000/docs.

## Endpoints

| Method | Path | What it does | Success | Errors |
|--------|------|--------------|---------|--------|
| GET | `/` | Describes the API | 200 | – |
| GET | `/health` | Health check, returns `{"status": "ok"}` | 200 | – |
| GET | `/tasks` | Lists all tasks | 200 | – |
| GET | `/tasks/{id}` | Gets one task | 200 | 404 unknown id |
| POST | `/tasks` | Creates a task from `{"title": "..."}` | 201 | 400 missing/empty title |
| PUT | `/tasks/{id}` | Updates `title` and/or `done` | 200 | 400 empty/invalid body, 404 unknown id |
| DELETE | `/tasks/{id}` | Deletes a task (empty body) | 204 | 404 unknown id |

Every error returns JSON like `{"error": "Task 99 not found"}`.

A task looks like this:

```json
{ "id": 1, "title": "Learn HTTP methods", "done": true }
```

### Validation rules

- `POST /tasks`: `title` must be present, must be a string, and cannot be empty or only spaces.
- `PUT /tasks/{id}`: send `title`, `done`, or both. `{}` is rejected. `title` cannot be empty, and `done` must be `true` or `false`.
- Malformed JSON, or a non-number id like `/tasks/abc`, also returns 400.

FastAPI normally answers invalid input with **422**. This project replaces that with **400 + `{"error": ...}`** so it
matches the assignment.

## Example: `curl -i`

```text
$ curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Buy milk"}'
HTTP/1.1 201 Created
date: Fri, 20 Nov 2026 12:02:41 GMT
server: uvicorn
content-length: 40
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

```text
$ curl -i http://localhost:8000/tasks/99
HTTP/1.1 404 Not Found
date: Fri, 20 Nov 2026 12:02:41 GMT
server: uvicorn
content-length: 29
content-type: application/json

{"error":"Task 99 not found"}
```

> On Windows PowerShell, use `curl.exe` instead of `curl`. Pass the JSON body from a file
> (`--data-binary "@body.json"`) because PowerShell mangles the quotes in `-d '{"title":"Buy milk"}'`.

## Swagger UI

Open http://localhost:8000/docs. Every endpoint is listed, and **Try it out** sends real requests.

![Swagger UI showing all endpoints](docs/swagger-endpoints.png)

## The mortality experiment

I created a task (`id 4`, "Buy milk"), restarted the server, and called `GET /tasks` again. Only the 3 starting
tasks came back. The task list is a Python variable in the server's memory, so it is rebuilt from the source code
every time the program starts, and anything added while it ran is gone. A database keeps data outside the
process, which is the problem Week 3 solves.

## AI vs me (Stage 7)

I gave an AI assistant (Claude) a prompt asking for the same API, ran its code, and fired the same checkpoint
requests at it as at mine. The AI's code is kept apart in [`ai-version/`](ai-version/), and my own `main.py` was
not changed.

- `ai-version/PROMPT-v1.md` and `ai-version/v1/main.py`: first prompt and the code it produced
- `ai-version/PROMPT-v2.md` and `ai-version/v2/main.py`: the improved prompt (rematch)
- `ai-version/checkpoint.py`: the 19 test requests (`python ai-version/checkpoint.py http://127.0.0.1:8000`)
- `ai-version/results-*.md`: the full test output for each version

### My prompt (v1)

```text
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
```

### Results

v1 started on the first try with no extra packages.

| Test | Mine | AI v1 | AI v2 |
|---|---|---|---|
| Reads, create, delete, unknown id (11 tests) | all pass | all pass | all pass |
| `POST {}`, empty or blank title, number title, bad JSON | 400 | 400 | 400 |
| `PUT {}` (empty body) | **400** | **200**, silently changes nothing ❌ | 400 |
| `PUT {"done": "yes"}` | **400** | **200**, stores `done: true` ❌ | 400 |
| `PUT {"done": 1}` | 400 | 200, stores `done: true` ❌ | 400 |
| `GET /tasks/abc` | 400 | 400 | 400 |
| 422 listed in Swagger docs | no | **yes, 4 times** (never actually sent) ❌ | no |
| **Score** | **19/19** | **17/19** | **19/19** |

### 1. What the AI did better

- **Ids are never reused.** v1 uses a `next_id` counter. Mine uses `max(id) + 1`, so if I delete the newest task
  (id 4) and create another, the new one gets id 4 again. A client that still remembers the old task 4 would
  silently get a different task. The counter is the safer design, and I can explain why.
- **Errors use exceptions.** The AI raises `HTTPException(404, ...)` inside a helper and converts it to
  `{"error": ...}` once, in a global handler. In my code, every endpoint has to check `if task is None: return not_found(...)`.
  Its approach means less repeated code.
- **It tells "not sent" apart from "sent as null".** It uses `payload.model_fields_set`, so `{"title": null}` is
  rejected, not ignored.

### 2. What it got wrong or quietly ignored

- **`PUT {}` returns 200 and does nothing.** Accepting an empty update hides client bugs. My API returns 400.
- **`done` is coerced.** Pydantic's default "lax" mode turns `"yes"` and `1` into `true`. I used
  `StrictBool`/`StrictStr` so that only real JSON booleans and strings are accepted.
- **The docs don't match the API.** Swagger still lists a 422 "Validation Error" response on 4 endpoints, but the
  API returns 400 instead. Documentation that lies is worse than none.
- **The error shape is inconsistent.** Most errors are `{"error": "..."}`, but validation errors add an extra
  `details` list.

### 3. What my prompt forgot to specify (the AI decided for me)

- **The exact error body.** I only wrote "errors as JSON". The AI happened to choose `{"error": ...}`, but it could
  just as easily have used FastAPI's default `{"detail": ...}`.
- **What PUT does with an empty body**, and **whether types are strict**. I didn't say, so it picked the lenient option.
- **Malformed JSON and non-numeric ids.** I never mentioned them. The AI chose 400 on its own, which happens to match mine.
- **Id reuse, the exact `GET /` response, the port, and the sample tasks.** All were left to the AI.

### Rematch (v2)

[`PROMPT-v2.md`](ai-version/PROMPT-v2.md) spelled out the exact error shape, "`PUT {}` is a 400", "no type coercion",
"never use 422, and do not list it in the docs", and "ids are never reused". The new code passed 19/19. The cost
was size: v2 is 256 lines against my 139, because it reads the raw request and validates by hand instead of using
Pydantic models, so it also had to describe the request bodies in the OpenAPI docs by hand.

**Lesson:** the AI didn't guess wrong at random. Every failure in v1 traced back to something my prompt didn't say.
I could only spot those failures because I had built and tested the API myself first.

## Project structure

```
FlyRank_BE-01/
├── main.py            # the whole API (hand-built, Stages 0–6)
├── requirements.txt   # fastapi + uvicorn
├── docs/              # README screenshots
├── ai-version/        # Stage 7: AI-generated code, prompts and test results
└── README.md
```
