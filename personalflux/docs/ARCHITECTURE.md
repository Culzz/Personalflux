# Architecture

Modular monolith: React + TypeScript storefront, FastAPI backend, PostgreSQL,
offline Python ML. No microservices.

```
browser -> frontend (Vite/nginx) -> FastAPI (/api/v1) -> PostgreSQL
                                            -> model artifact (loaded once, in memory)
```

## Request path

A recommendation request identifies the customer (JWT) or anonymous session
(`X-Session-Id`), gathers session + history signals, scores candidates from
the loaded artifact, applies availability and exclusion rules, and returns
items with grounded explanations. Impressions are posted back separately and
feed the analytics tables.

The model is never retrained per request. Training happens offline in `ml/`;
a validated artifact is registered with `POST /ml/models/scan` and released
with `POST /ml/models/{version}/promote`. Promoting an older version rolls back.

## Which model a worker serves

The choice of serving version lives in the database, not in a process. Promotion
writes the version under a Postgres advisory lock, and a partial unique index
(`uq_model_versions_one_serving`) allows exactly one serving row, so two
promotions cannot both win. The artifact itself is immutable and checksum
verified, so a bad file is refused and the current model keeps serving.

Each worker keeps its own copy in memory (loading it is fast and avoids a shared
dependency on the request path). A background poller re-reads the serving version
every `MODEL_POLL_SECONDS` and hot-swaps when it differs, which is what makes a
promotion reach every process without a restart. `/health/model` returns 503
while a worker has not caught up, and `/api/v1/ml/health` reports both the
serving and desired version. Instant fan-out across many instances would need a
message bus; polling is enough at this size and is noted as a trigger, not a gap.

## Attribution

An impression means "a person could have seen this". The frontend reports only
cards that were actually on screen (half visible for a short dwell), each keyed
`request_id:product_id`. A click on a recommendation carries the same request id,
position and model version, so a click can be matched to the impression — and
therefore to the request and the model version — that caused it. Impressions are
unique by key, so a retry or a remount cannot inflate the numbers, and
`/analytics/recommendations` reports attributed clicks and the fallback rate
alongside plain counts.

## Layers

- `frontend/src`: routes in `pages/`, server state in `features/`, HTTP in `lib/`.
- `backend/app/api/v1`: auth, products, events, customers, recommendations, analytics, ml, admin.
- `backend/app/services`: events, profile, recommendation ranking, imports, model admin.
- `backend/app/ml`: artifact loading and registry (serving only, no training).
- `ml/src`: preprocessing, baselines, adaptive ranker, evaluation. Results in `ml/reports/`.

## Data

UUIDs for app entities; source dataset ids preserved separately. Money as
`Numeric`, never float. Events are append-only and idempotent by key.
Customer deletion cascades. Offline metrics and live activity are reported
separately by design (`/ml/experiments` vs `/analytics/*`).

## Capacity

Single-node deployment. Reference data: ~225k catalog rows, ~2.7M events.
Reads dominate (catalog, feeds); writes are single-row event inserts.
PostgreSQL handles this comfortably on one node, so there is no cache,
queue, replica, or object store yet. Add those on measured need, not before:
Redis for rate limits across workers first, managed Postgres + backups when
leaving localhost, a CDN when static traffic justifies it.
