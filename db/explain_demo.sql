-- Stretch: does an index help? Run with:
--   docker compose exec -T db psql -U postgres -d tasks < db/explain_demo.sql
-- Uses its own table (tasks_bench) so the real tasks table is never touched, and drops it at the end.

DROP TABLE IF EXISTS tasks_bench;
CREATE TABLE tasks_bench (
    id    BIGINT  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title TEXT    NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT FALSE
);

-- 200,000 tasks, 1% of them done (an index only pays off when the filter is selective).
INSERT INTO tasks_bench (title, done)
SELECT 'Task ' || i, (i % 100 = 0)
FROM generate_series(1, 200000) AS i;
ANALYZE tasks_bench;

\echo '=== BEFORE: no index on done ==='
EXPLAIN ANALYZE SELECT id, title FROM tasks_bench WHERE done;

CREATE INDEX idx_tasks_bench_done ON tasks_bench (done);
ANALYZE tasks_bench;

\echo '=== AFTER: CREATE INDEX idx_tasks_bench_done ON tasks_bench (done) ==='
EXPLAIN ANALYZE SELECT id, title FROM tasks_bench WHERE done;

DROP TABLE tasks_bench;
