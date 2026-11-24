# Task API (FastAPI + PostgreSQL)

## Run

```sh
cp .env.example .env        # then edit .env and set POSTGRES_PASSWORD
docker compose up --build   # starts Postgres and the API together
```

API: http://localhost:8000 (docs at http://localhost:8000/docs)

On first start the app creates the `tasks` table and inserts the 3 example tasks.
Data lives in the `pgdata` volume, so it survives `docker compose down` / `up`.

- Stop: `docker compose down`
- Wipe all data and start fresh: `docker compose down -v`

Note: Postgres only reads `POSTGRES_PASSWORD` the first time it creates the volume.
If you change the password later, either change it inside Postgres (`ALTER USER`)
or reset the volume with `docker compose down -v`.
