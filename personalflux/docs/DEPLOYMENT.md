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

Four moving parts:

| piece | host | notes |
|---|---|---|
| storefront | **Vercel** | static SPA; set the project root to `personalflux/frontend`; `vercel.json` handles SPA rewrites and asset caching |
| API | **Cloud Run** | `gcloud run deploy --source` builds the existing Dockerfile; the service scales to zero, which is also what lets the Neon compute sleep |
| database | **Neon** managed Postgres | provisioned with `neon deploy`; credentials live in `.env.local`, secrets are set on the service |
| model artefact | **Cloudflare R2** (or any static URL) | a `.tar.gz` the container downloads on each cold start |

### Why the two hosts share a parent domain

The refresh token is an HttpOnly cookie with `SameSite=Strict`, and the refresh
endpoint additionally refuses a request whose `Origin` is not in `CORS_ORIGINS`.
`Strict` means the browser will not attach that cookie to a request that is
cross-site, and a bare `*.vercel.app` to `*.run.app` call is cross-site
(different registrable domains). Sessions would die on every reload.

So put the storefront and the API on two subdomains of one domain you control:

```
shop.example.com   ->  Vercel       (custom domain on the frontend project)
api.example.com    ->  Cloud Run    (domain mapping, CNAME to ghs.googlehosted.com)
```

Subdomains of the same registrable domain are same-site, so `Strict` keeps
working and no code change is needed. Both hosts issue TLS for a custom domain
themselves; nothing to configure here.

### Deploy the API (Cloud Run)

One-time project setup, then a single deploy command. From `personalflux/backend`,
which is where the Dockerfile lives:

```
gcloud auth login
gcloud config set project <project-id>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
```

Put the two credentials in Secret Manager rather than in plain environment
variables (free at this scale, and the database password stays out of the
revision listing):

```
printf '%s' "<DATABASE_URL_UNPOOLED from .env.local>" | gcloud secrets create personaflux-database-url --data-file=-
printf '%s' "<48 random characters>"                  | gcloud secrets create personaflux-jwt-secret --data-file=-
```

```
gcloud run deploy personaflux-api \
  --source . \
  --region europe-west3 \
  --allow-unauthenticated \
  --cpu 1 --memory 1Gi --concurrency 80 \
  --min-instances 0 --max-instances 2 \
  --cpu-boost --timeout 300 \
  --set-env-vars APP_ENV=production,MODEL_ARTIFACT_DIR=/tmp/artifacts,WEB_CONCURRENCY=1,MODEL_POLL_SECONDS=10,LOG_LEVEL=INFO,CORS_ORIGINS=https://shop.example.com,MODEL_ARTIFACT_URL=<r2 url> \
  --set-secrets DATABASE_URL=personaflux-database-url:latest,JWT_SECRET_KEY=personaflux-jwt-secret:latest \
  --startup-probe-http-path /health --startup-probe-initial-delay 5 \
  --startup-probe-period 10 --startup-probe-timeout 5 --startup-probe-failure-threshold 30
```

`--source .` builds the existing `Dockerfile` with Cloud Build and pushes it to
Artifact Registry, so no image has to be built by hand. The container command is
unchanged: `alembic upgrade head`, then Uvicorn on `$PORT`, which Cloud Run sets.

Why these values:

- **`--min-instances 0`** is the whole reason for choosing Cloud Run: an idle
  service stops querying Postgres, Neon suspends its compute in turn, and a hobby
  deployment stays inside Neon's 191.9 free compute-hours instead of burning ~730.
- **`--max-instances 2`** bounds how many connections the database can see. Each
  instance holds a pool of 5 (+10 overflow), which is well inside Neon's limit.
- **`WEB_CONCURRENCY=1`** because the instance has one vCPU and one gigabyte; two
  workers would sit near the memory ceiling for no throughput gain at this size.
  Concurrency 80 is handled by the async event loop and the DB threadpool.
- **`--cpu-boost`** and the **startup probe** cover the first boot, which loads
  numpy and the model before it answers anything.
- Under Cloud Run's default CPU throttling the in-process promotion poll only runs
  while requests are being served, so a promotion is adopted on the next request
  rather than while the service sleeps. `--no-cpu-throttling` keeps a poller
  running, at the cost of always-allocated CPU.

Custom domain, and the CNAME record it asks for:

```
gcloud beta run domain-mappings create --service personaflux-api --domain api.example.com --region europe-west3
```

**What this costs.** Cloud Run's always-free tier (2M requests, 360k GB-seconds,
180k vCPU-seconds a month) covers a portfolio deployment, but Google requires a
billing account with a card attached before the service can be created. The free
tier is North-America-centric for egress, so `europe-west3` can add pennies; the
image in Artifact Registry exceeds the 0.5 GB free storage by a little. Expect a
few cents a month rather than zero, and set a budget alert.

### Hosting the model artefact

The container downloads `MODEL_ARTIFACT_URL` into `/tmp/artifacts` when it starts
and the directory is empty. Cloud Run's filesystem is memory, so this happens on
every cold start — 13 MB, once per scale-up, not per request. Any URL that answers
an unauthenticated GET works; Cloudflare R2 is free at this size and charges no
egress:

```
npx wrangler r2 bucket create personaflux-artifacts
npx wrangler r2 object put personaflux-artifacts/model/personaflux-v0.1.tar.gz \
  --file "%TEMP%\opencode\personaflux-artifacts-v0.1.tar.gz"
```

Then enable a public URL for the bucket (R2 → Settings → Public access) and use
`https://pub-<hash>.r2.dev/model/personaflux-v0.1.tar.gz`.

The tarball must contain the version directory at its top level, because that is
what the registry scans for:

```
personaflux-v0.1-20261013-222549/metadata.json
personaflux-v0.1-20261013-222549/items.npy
personaflux-v0.1-20261013-222549/item_meta.parquet
personaflux-v0.1-20261013-222549/popularity.json
personaflux-v0.1-20261013-222549/similarity.npz
```

`items.npy` and the parquet are derived from the Retailrocket dataset, whose terms
are non-commercial: publish them to a bucket you control, not to a public release
of the repository. Without the artefact the API still serves, from database
popularity, and says so on `/api/v1/ml/health`.

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

For the Cloud Run service, set `DATABASE_URL` to the **`DATABASE_URL_UNPOOLED`**
value from `.env.local` (with the `postgresql+psycopg://` scheme, though either
form works now). Setting it to the pooler URL also connects, minus the statement
timeout.

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

A fresh Neon branch has no tables and no products. With `.env.local` in place the
scripts read the same connection the API does, so nothing has to be exported by
hand:

```
cd personalflux/backend
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
- *Bad deploy*: `gcloud run revisions list` then
  `gcloud run services update-traffic personaflux-api --to-revisions <previous>=100`.
  The previous revision keeps running until the new one passes its startup probe.
  Migrations are additive in this project, so a rollback does not need a down
  migration.
- *Bad model promoted*: promote the previous version. No restart, no redeploy.
- *API unhealthy but database fine*: check `/health/model`; if the poller is
  behind or the artefact fetch failed, restore `MODEL_ARTIFACT_URL` and redeploy a
  revision, or promote a model that is already on disk. The storefront keeps
  working either way, because the catalogue endpoints do not depend on the model.
- *Database lost*: restore from Neon (point-in-time or a branch), then re-run the
  catalogue importers. Events are append-only and idempotent by key, so replays
  are safe.

## Deliberately deferred

No Redis, no queue, no object store, no CDN, no multi-region. Each has a trigger:
Redis when there is more than one instance and rate limits must be shared; a queue
when imports or training need to run in the background; an object store when the
artefact outgrows a disk; a CDN when static traffic justifies it.

