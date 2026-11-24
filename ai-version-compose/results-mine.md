Testing task-api (D:\FlyRank AI\Assignments\Backend AI Engineering\task-api)

| Check | Result | Detail |
|---|---|---|
| compose file exists | PASS | compose.yaml |
| .env.example exists | PASS |  |
| Dockerfile exists | PASS |  |
| no hardcoded password in compose | PASS | uses ${...} / env_file |
| no hardcoded credentials in .py | PASS | none |
| routes contain no SQL (one repository module) | PASS | SQL lives outside main.py |
| connects with one DATABASE_URL connection string | PASS |  |
| .env kept out of the image (.dockerignore) | PASS | .dockerignore lists .env |
| .env git-ignored | PASS |  |
| postgres image version pinned | PASS | postgres:17 |
| api uses service name, not localhost | PASS |  |
| named volume for the database | PASS |  |
| waits for a healthy db | PASS | depends_on: condition: service_healthy |
| clean clone: cp .env.example .env && docker compose up works | PASS | ready in 6s |
| Week 2 suite 19/19 | PASS |  |
| GET /tasks shape [{id,title,done}] | PASS |  |
| ?search is case-insensitive (like SQLite LIKE) | PASS | 200 [{'id': 4, 'title': 'Buy milk', 'done': False}] |
| ?search=100% treats % literally | PASS | 200 [] |
| ?sort=title is case-insensitive | PASS | ['Build a CRUD API', 'Buy milk', 'Push to GitHub'] |
| /stats same shape | PASS | 200 {'total': 3, 'done': 0, 'open': 3} |
| huge id -> 404 (not 500) | PASS | 404 {'error': 'Task 99999999999999999999 not found'} |
| data survives docker compose down + up | PASS | 4 rows before, 4 after |
| seed not repeated after restart | PASS | 4 rows |
| deleted id never reused | PASS | deleted 5, new task got 6 |
| /health notices the database is down | PASS | 503 {'status': 'degraded', 'db': 'down', 'redis': 'ok'} |
| image size | PASS | a3check-api 243MB |

25/25 passed
