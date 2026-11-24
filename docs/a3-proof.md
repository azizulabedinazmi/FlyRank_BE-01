# A3 proof log (Postgres in Docker)

Raw output from the runs described in the README, 24 Nov 2026. Docker 29.9.3, Compose v5.7.1, `postgres:17`, `redis:7-alpine`.

## 1. Week 2 checkpoint suite, unchanged, against the Postgres stack

`docker compose up -d --build` on a fresh volume, then `python ai-version/checkpoint.py http://127.0.0.1:8000`:

| Test | Expected | Got | Body |
|---|---|---|---|
| GET /health | 200 | 200 PASS | `{"status":"ok","db":"ok","redis":"ok"}` |
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

**19/19 passed.** Extra checks on the same stack:

```text
GET /tasks?search=MILK            -> [{"id":4,"title":"Buy milk","done":false}]      (ILIKE: case-insensitive)
GET /tasks?search=100%            -> []                                               (% escaped, not a wildcard)
GET /tasks?done=false&sort=title  -> Build a CRUD API, Buy milk, Push to GitHub
GET /stats                        -> {"total":3,"done":0,"open":3}
GET /tasks/99999999999999999999   -> 404   (bigger than BIGINT: a 404, not a 500)
GET /tasks?sort=bad               -> 400
```

## 2. Persistence across `docker compose down` / `up`

```text
### 1. create two tasks
$ curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Survive the restart"}'
HTTP/1.1 201 Created
date: Tue, 24 Nov 2026 03:38:09 GMT
server: uvicorn
content-length: 51
content-type: application/json

{"id":5,"title":"Survive the restart","done":false}
{"id":6,"title":"Water the plants","done":false}

### 2. before
[{"id":2,...},{"id":3,...},{"id":4,"title":"Buy milk",...},{"id":5,"title":"Survive the restart",...},{"id":6,"title":"Water the plants",...}]

### 3. docker compose down        (api, db and redis containers + network removed)
$ docker ps -a --filter name=task-api
(no containers left)
$ docker volume ls --filter name=taskdata
task-api_taskdata                  <- the volume is still there

### 4. docker compose up -d
api Up 2 seconds
db Up 4 seconds (healthy)
redis Up 5 seconds (healthy)

### 5. after
[{"id":2,...},{"id":3,...},{"id":4,"title":"Buy milk",...},{"id":5,"title":"Survive the restart",...},{"id":6,"title":"Water the plants",...}]

### 6. app-only restart: docker compose restart api
GET /stats -> {"total":5,"done":0,"open":5}     <- still 5: the seed did not run again
```

## 3. The rows inside Postgres

```text
$ docker compose exec db psql -U postgres -d tasks -c "\dt" -c "SELECT * FROM tasks ORDER BY id;"
         List of relations
 Schema | Name  | Type  |  Owner
--------+-------+-------+----------
 public | tasks | table | postgres
(1 row)

 id |        title        | done
----+---------------------+------
  2 | Build a CRUD API    | f
  3 | Push to GitHub      | f
  4 | Buy milk            | f
  5 | Survive the restart | f
  6 | Water the plants    | f
(5 rows)
```

## 4. Clean clone, no manual database setup

```text
git clone <repo> && cd <repo>
Test-Path .env                     -> False   (.env is not in git)
cp .env.example .env
docker compose up -d --build
GET /tasks after 20 s              -> the 3 seeded tasks
```

## 5. EXPLAIN ANALYZE before/after an index (`db/explain_demo.sql`, 200,000 rows, 1% done)

```text
=== BEFORE: no index on done ===
 Seq Scan on tasks_bench  (cost=0.00..3274.00 rows=2100 width=19) (actual time=0.049..9.650 rows=2000 loops=1)
   Filter: done
   Rows Removed by Filter: 198000
 Execution Time: 9.926 ms

=== AFTER: CREATE INDEX idx_tasks_bench_done ON tasks_bench (done) ===
 Index Scan using idx_tasks_bench_done on tasks_bench  (cost=0.29..235.40 rows=2080 width=19) (actual time=0.026..1.112 rows=2000 loops=1)
   Index Cond: (done = true)
 Execution Time: 1.220 ms
```

## 6. Mortality experiment: Postgres without a volume

```text
$ docker run -d --name mortality -e POSTGRES_PASSWORD=... -p 5433:5432 postgres:17      (no -v)
$ psql: CREATE TABLE tasks ...; INSERT ... 'I will not survive'; SELECT * FROM tasks;
  1 | I will not survive
$ docker rm -f mortality
$ docker run -d --name mortality ... postgres:17                                        (fresh container)
$ psql: \dt
Did not find any relations.
```
