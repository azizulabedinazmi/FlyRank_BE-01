-- The tasks table. Run by the app on every startup (postgres_repository.py), so it must be safe to re-run.
-- You can also run it by hand:
--   docker compose exec -T db psql -U postgres -d tasks < db/schema.sql

CREATE TABLE IF NOT EXISTS tasks (
    id    BIGINT  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- Postgres hands out ids; a sequence never reuses them
    title TEXT    NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT FALSE                     -- a real boolean, unlike SQLite's 0/1
);

-- GET /tasks?done=... and /stats filter on done.
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks (done);
