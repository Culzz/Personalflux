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
cd backend
python ..\scripts\seed_showcase.py                 # 30 curated products with photos
python ..\scripts\import_catalog_provider.py 100   # DummyJSON demo store
python ..\scripts\import_affiliate_catalog.py "wireless headphones" "running shoes"
```

The first two are labelled demo sources. The third imports a **live affiliate
feed** from the eBay Browse API and needs `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET`
(and optionally `AFFILIATE_CAMPAIGN_ID` for your Partner Network campaign). Every
row records its origin in `products.catalog_source`, so a demo row is never
presented as a real listing. All three are idempotent.

## Production

Two managed pieces, plus the database:

| piece | host | notes |
|---|---|---|
| storefront | **Vercel** | static SPA; set the project root to `personalflux/frontend`; `vercel.json` handles SPA rewrites and asset caching |
| API | **Render** (or any Docker host) | `render.yaml` at the repository root provisions the service and an artefacts disk; the database is *not* created there |
| database | **Neon** managed Postgres | set `DATABASE_URL` in the Render dashboard; back it up before anything else |

### Why the two hosts share a parent domain

The refresh token is an HttpOnly cookie with `SameSite=Strict`, and the refresh
endpoint additionally refuses a request whose `Origin` is not in `CORS_ORIGINS`.
`Strict` means the browser will not attach that cookie to a request that is
cross-site, and a bare `*.vercel.app` → `*.onrender.com` call is cross-site
(different registrable domains). Sessions would die on every reload.

So put the storefront and the API on two subdomains of one domain you control:

```
shop.example.com   ->  Vercel   (custom domain on the frontend project)
api.example.com    ->  Render   (custom domain on the web service)
```

Subdomains of the same registrable domain are same-site, so `Strict` keeps
working and no code change is needed. Both hosts issue TLS for a custom domain
themselves; nothing to configure here.

### Deploy the API (Render blueprint)

1. Render → **New → Blueprint** → pick this repository. It reads `render.yaml`.
2. Set `DATABASE_URL` to the Neon connection string (see below).
3. Set `CORS_ORIGINS` to the storefront origin, for example `https://shop.example.com`.
4. Set `JWT_SECRET_KEY` (the blueprint generates one; never reuse the dev value).
5. Optional but recommended: set `MODEL_ARTIFACT_URL` to a `.tar.gz` of the
   artefact directory. The container fetches and verifies it at boot, so the API
   serves the model instead of falling back to database popularity.
6. Add the custom domain (`api.example.com`) under Settings → Custom Domains.

The container runs `alembic upgrade head` and then two Uvicorn workers. Each
worker loads the model and **adopts a promotion on its own poll** (`MODEL_POLL_SECONDS`,
default 10), which is what makes a promotion reach every process without a restart.

### The database (Neon)

Create a project in the same region as the service (Frankfurt → `eu-central-1`),
then copy the connection string and **edit two things**:

```
postgresql://u:p@ep-cool-1.eu-central-1.aws.neon.tech/neondb?sslmode=require
            |
            v
postgresql+psycopg://u:p@ep-cool-1.eu-central-1.aws.neon.tech/neondb?sslmode=require
```

- the `+psycopg` driver marker, which SQLAlchemy needs in order to use psycopg 3
- `sslmode=require` must survive the copy; Neon refuses an unencrypted connection

Either host works: the direct one (`ep-cool-1…`) or the pooler (`ep-cool-1-pooler…`).
A URL containing `-pooler` goes through PgBouncer in transaction mode, where a
prepared statement cannot be reused across transactions, so the engine disables
psycopg's automatic preparation for those URLs (`app/db/session.py`). Use the
direct host unless you have a reason not to: two long-lived workers with a small
pool do not need a pooler.

**Usage billing.** Neon suspends an idle compute and wakes it on the next query.
Two things here touch the database while nobody is shopping: the readiness probe
(`/health/db`, polled by the host) and each worker's promotion poll. Between them
the compute stays awake, which is roughly 730 compute-hours a month against a
free plan allowance of 191.9. If that matters, pick one:

- a paid Neon plan, which is what keeps promotion and rollback instant;
- accept the free tier with `MODEL_POLL_SECONDS` raised (say 1800) and
  `healthCheckPath` changed to `/health`, which lets the compute sleep and costs
  a promotion a while to reach every worker;
- run one worker (`WEB_CONCURRENCY=1`).

`pool_pre_ping` is already on, so a connection that Neon closed while suspended is
discarded rather than served.

### Deploy the storefront (Vercel)

1. Vercel → **New Project** → same repository → **Root Directory** `personalflux/frontend`.
2. Environment variable `VITE_API_URL` = `https://api.example.com` (no trailing slash).
3. Deploy. `vercel.json` already rewrites client routes to `index.html`.
4. Add the custom domain (`shop.example.com`) under Settings → Domains, then put
   that same origin into the API's `CORS_ORIGINS`.

### First run: the database is empty

A fresh Neon branch has the schema (the container migrates it) and no products, so
the storefront would render an empty catalogue. From a machine with the backend
virtualenv, pointed at the **direct** Neon host:

```
cd personalflux/backend
$env:DATABASE_URL="postgresql+psycopg://…?sslmode=require"
python ..\scripts\seed_showcase.py                    # described demo products, labelled as demo
python ..\scripts\import_affiliate_catalog.py "wireless headphones"   # optional: real listings, needs eBay keys
python ..\scripts\create_admin.py                     # an admin/analyst account for /business and /ml
```

Then load the model:

```
POST /api/v1/ml/models/scan               # register artefacts on the disk (validated)
POST /api/v1/ml/models/{version}/promote  # serve one
```

`/health/model` returns 503 until every worker has adopted the promoted version;
`/api/v1/ml/health` names the serving version, the desired version and any poll error.

### After both are up

```
python scripts/smoke_test.py https://api.example.com
```

The smoke test registers a throwaway account and exercises the whole journey.
Run it after every deploy; it is the quickest way to catch a CORS or env mistake.

## Operating it

**Health.** `/health` is liveness (process up, no database). `/health/db` is
readiness (database reachable) and is what the host polls. `/health/model` is
503 while a worker has not yet adopted the promoted version, and `/api/v1/ml/health`
reports the serving version, the desired version and the poll error, if any.

**Promotion and rollback.**
```
POST /api/v1/ml/models/scan              # register artefacts found on disk (validated)
POST /api/v1/ml/models/{version}/promote # make one serve; promotes atomically
POST /api/v1/ml/models/{version}/promote # promoting an older version is the rollback
```
Promotion is serialised with a Postgres advisory lock and a partial unique index
allows exactly one serving row, so two operators cannot both win. The artefact is
immutable and checksum-verified, so a bad file is refused and the current model
keeps serving. If a worker never catches up, `/health/model` stays 503 and names it.

**Timeouts and pooling.** Each request runs with a Postgres statement timeout
(`DB_STATEMENT_TIMEOUT_MS`, default 15s) and the pool is bounded
(`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`, recycling idle connections). A stuck query
therefore fails one request instead of holding a worker and a connection forever.

**Recovery.**
- *Bad deploy*: Render keeps the previous image; redeploy it. Migrations are
  additive in this project, so a rollback does not need a down migration.
- *Bad model promoted*: promote the previous version. No restart, no redeploy.
- *API unhealthy but database fine*: check `/health/model`; if the poller is
  behind or the artefact disk is empty, restore `MODEL_ARTIFACT_URL` or the disk
  and restart the service. The storefront keeps working either way, because the
  catalogue endpoints do not depend on the model.
- *Database lost*: restore from Neon (point-in-time or a branch), then re-run the
  catalogue importers. Events are append-only and idempotent by key, so replays
  are safe.

## Deliberately deferred

No Redis, no queue, no object store, no CDN, no multi-region. Each has a trigger:
Redis when there is more than one instance and rate limits must be shared; a queue
when imports or training need to run in the background; an object store when the
artefact outgrows a disk; a CDN when static traffic justifies it.

