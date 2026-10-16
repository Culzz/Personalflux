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
