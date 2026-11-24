-- Schema for the Task API. Safe to run on every startup: everything is IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS tasks (
    id    SERIAL  PRIMARY KEY,
    title TEXT    NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT FALSE
);

-- Index on done so GET /tasks?done=... and /stats don't scan every row.
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks (done);
