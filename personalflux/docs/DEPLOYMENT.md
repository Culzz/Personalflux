# Deployment

## Local (compose)

```
cp .env.example .env
# set JWT_SECRET_KEY in .env (32+ characters)
docker compose up --build
```

- API on :8000 (`/health`, `/health/db`). Docs at `/docs` unless `APP_ENV=production`.
- Storefront on :5173 (nginx proxies `/api`, `/health` to the backend).
- Postgres 16 with a `db-data` volume. The backend runs `alembic upgrade head` on start.

## Local (no compose)

Backend from `backend/` with the project virtualenv:

```
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend from `frontend/`:

```
npm ci
npm run dev
```

Needs `DATABASE_URL` and `JWT_SECRET_KEY` (see `backend/.env.example`).

## Demo data

```
python scripts/seed_showcase.py
```

Seeds 30 curated products and stable demo prices for sample rows. Idempotent.

## Production notes

- Set `APP_ENV=production` (disables `/docs`), a long `JWT_SECRET_KEY`, and a managed Postgres URL.
- The model artifact is mounted read-only at `/artifacts` in compose (`./ml/artifacts`).
  With no valid artifact the API serves database popularity and reports `degraded` on `/api/v1/ml/health`.
- No object storage or Redis yet. Back up the database; artifacts are versioned files.
