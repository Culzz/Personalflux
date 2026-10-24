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

Two Render services, one Neon database:

| piece | host | notes |
|---|---|---|
| storefront | **Render static site** | built from `frontend/` with `npm ci && npm run build`; SPA rewrite to `index.html` |
| API | **Render web service** | Docker, built from `backend/Dockerfile`; the free plan spins down after 15 minutes idle, which also lets the Neon compute sleep |
| database | **Neon** managed Postgres | provisioned with `neon deploy`; credentials live in `.env.local` |
| model artefact | **GitHub release asset** | `model-v0.1`; the container downloads it into `/artifacts` on boot |

`render.yaml` is the blueprint for both services. `DATABASE_URL` and
`JWT_SECRET_KEY` are marked `sync: false`, so they are set once in the dashboard
and never committed.

### Keeping sessions alive

The refresh token is an HttpOnly cookie, and the refresh endpoint refuses a request
whose `Origin` is not in `CORS_ORIGINS`.

Both Render hostnames sit under `onrender.com`:

```
https://personaflux-shop.onrender.com   ->  static site
https://personaflux-api.onrender.com    ->  web service
```

`onrender.com` is the registrable domain for both, so the cookie is same-site and
`SameSite=Strict` (the default) works unchanged. `CORS_ORIGINS` still has to name
the storefront origin exactly, because the API is a different origin.

If the storefront ever moves to a different registrable domain (a custom domain on
Vercel, say), set `REFRESH_COOKIE_SAMESITE=none` on the API. The cookie is then
marked `Secure` automatically, because browsers discard `SameSite=None` without it,
and the `Origin` check still applies.

### Deploying

1. Create the services from the blueprint: **New → Blueprint**, pick the
   repository, apply. Render reads `render.yaml`.
2. Set the two secret environment variables on `personaflux-api`:
   - `DATABASE_URL`: the direct Neon connection (`DATABASE_URL_UNPOOLED` in
     `.env.local`, without the surrounding quotes)
   - `JWT_SECRET_KEY`: 48 random characters
3. The first deploy runs `alembic upgrade head`, then Uvicorn on `$PORT`.

Why these values:

- **`plan: free`**, with a service that spins down after 15 minutes idle: an idle
  API stops querying Postgres, Neon suspends its compute in turn, and the
  deployment stays inside Neon's 191.9 free compute-hours instead of burning ~730.
- **`WEB_CONCURRENCY=1`** because the free instance has 512 MB and a shared CPU.
  Two workers would sit near the memory ceiling for no throughput gain at this size.
- **`MODEL_POLL_SECONDS=10`** adopts a promoted model on the next poll rather than
  requiring a restart.

**What this costs.** Render's free plan needs no card for a static site or a web
service. The API sleeps when idle, so the first request after a quiet spell waits
for a cold start (roughly a minute: container start, migrations, model download).
Neon's free plan covers the database.

### The model artefact

The trained version is a build output, so it is not in git. It is published as a
release asset, and the API downloads it into `/artifacts` on boot, then verifies the
checksums in `metadata.json` as usual:

```
https://github.com/Culzz/Personalflux/releases/download/model-v0.1/personaflux-v0.1.tar.gz
```

To publish a new version, upload a tarball whose top level is the version directory
(the registry scans for folders containing `metadata.json`):

```
personaflux-v0.1-20261013-222549/metadata.json
personaflux-v0.1-20261013-222549/items.npy
personaflux-v0.1-20261013-222549/item_meta.parquet
personaflux-v0.1-20261013-222549/popularity.json
personaflux-v0.1-20261013-222549/similarity.npz
```

Without the artefact the API still serves, from database popularity, and says so on
`/api/v1/ml/health`.

`items.npy` and the parquet are derived from the Retailrocket dataset, whose terms
are non-commercial. The release asset is public so the API can fetch it, which is
the same exposure a public bucket would have; take it down when the demo ends.

### The database (Neon)

Create the project in the same region as the service (Frankfurt → `eu-central-1`).
The CLI does the rest: `neon.ts` in the repository root is the service policy, and
`neon deploy` applies it and writes `.env.local` with the connection details.

```
neon init -y --org-id <org> --project-id <project> --branch production --services postgres
neon deploy
```

`.env.local` then holds three values, and the backend reads that file directly
(`app/core/config.py` resolves it by path, so it does not matter whether the
process was started from `backend/` or from `/code` in the container):

| variable | what it is |
|---|---|
| `DATABASE_URL` | the pooler endpoint |
| `DATABASE_URL_UNPOOLED` | the same database, direct |
| `NEON_BRANCH` | the branch that was deployed |

**Which one the app opens.** The direct endpoint, when it is published. Neon's
pooler is PgBouncer in transaction mode: it rejects the startup parameter that
carries the statement timeout (`unsupported startup parameter in options:
statement_timeout`), and a prepared statement cannot be reused across
transactions there. A long-running container with a small pool does not need the
pooler, so `Settings.connection_url` prefers `DATABASE_URL_UNPOOLED` and the
statement timeout survives. A host that publishes only one URL still works: the
engine then drops the startup parameter and disables psycopg's automatic
preparation instead (`app/db/session.py`).

The `+psycopg` driver marker is **not** something you need to add by hand. Neon
hands out `postgresql://`, which SQLAlchemy would read as "use psycopg2" (not
installed); the settings layer rewrites the scheme to `postgresql+psycopg://`.
`sslmode=require` must survive the copy — Neon refuses an unencrypted connection.

For the Render service, set `DATABASE_URL` to the **`DATABASE_URL_UNPOOLED`**
value from `.env.local`, without the surrounding quotes.

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

### Deploy the storefront (Render)

`render.yaml` already defines it: root directory `frontend`, build command
`npm ci && npm run build`, publish path `./dist`, and a rewrite of every path to
`index.html` so client-side routes survive a reload.

1. Applying the blueprint creates the static site together with the API.
2. `VITE_API_URL` is the API origin. Vite inlines it at build time, so changing it
   means a redeploy, not just a restart.
3. The API's `CORS_ORIGINS` must contain the storefront origin exactly
   (`https://personaflux-shop.onrender.com` in the blueprint).

### First run: the database is empty

A fresh Neon branch has no tables and no products. With `.env.local` in place the
scripts read the same connection the API does, so nothing has to be exported by
hand:

```
cd backend
python -m alembic upgrade head                        # normally the container does this
python ..\scripts\seed_showcase.py                    # described demo products, labelled as demo
python ..\scripts\import_affiliate_catalog.py "wireless headphones"   # optional: real listings, needs eBay keys
python ..\scripts\create_admin.py --email you@example.com   # prompts for the password, hidden
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
- *Bad deploy*: open the service in the Render dashboard → **Deploys**, pick the
  previous successful one and choose **Rollback**. The previous container keeps
  serving until the new one passes its health check. Migrations are additive in this
  project, so a rollback does not need a down migration.
- *Bad model promoted*: promote the previous version. No restart, no redeploy.
- *API unhealthy but database fine*: check `/health/model`; if the poller is
  behind, promote a model that is already on disk. If the artefact download failed,
  check `MODEL_ARTIFACT_URL` and that the release asset is still reachable. The
  storefront keeps working either way, because the catalogue endpoints do not
  depend on the model.
- *Database lost*: restore from Neon (point-in-time or a branch), then re-run the
  catalogue importers. Events are append-only and idempotent by key, so replays
  are safe.

## Deliberately deferred

No Redis, no queue, no object store, no CDN, no multi-region. Each has a trigger:
Redis when there is more than one instance and rate limits must be shared; a queue
when imports or training need to run in the background; an object store when the
artefact outgrows a disk; a CDN when static traffic justifies it.

