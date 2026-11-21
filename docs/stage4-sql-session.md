# Stage 4: SQL by hand

Each query was run straight against `tasks.db` while the API server kept running (no restart).

## `SELECT * FROM tasks;`

```text
1 | Learn HTTP methods | 1
2 | Build a CRUD API | 0
3 | Push to GitHub | 0
4 | Buy milk | 1
5 | Water the plants | 0
```

## `SELECT * FROM tasks WHERE done = 1;`

```text
1 | Learn HTTP methods | 1
4 | Buy milk | 1
```

## `SELECT COUNT(*) FROM tasks;`

```text
5
```

## `UPDATE tasks SET done = 1;`

```text
5 row(s) changed
```

`GET /tasks` right afterwards:

```json
[{"id": 1, "title": "Learn HTTP methods", "done": true}, {"id": 2, "title": "Build a CRUD API", "done": true}, {"id": 3, "title": "Push to GitHub", "done": true}, {"id": 4, "title": "Buy milk", "done": true}, {"id": 5, "title": "Water the plants", "done": true}]
```

## `DELETE FROM tasks WHERE done = 1;`

```text
5 row(s) changed
```

`GET /tasks` right afterwards:

```json
[]
```

