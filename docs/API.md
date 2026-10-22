# PersonaFlux API (v0.6)

Base URL in development: `http://localhost:8000`. Interactive docs: `/docs` (disabled when `APP_ENV=production`).
All application routes live under `/api/v1`. Health checks are `/health` (liveness), `/health/db` (database
readiness) and `/health/model` (this worker is serving the version the database asks for).

## Authentication

- `POST /auth/login` or `/auth/register` returns a short-lived **access token** (JWT, default 30 minutes) in the body.
  Send it as `Authorization: Bearer <token>`. The token lives in frontend memory only, never in storage.
- The same response sets an **HttpOnly refresh cookie** (`refresh_token`, `SameSite=Strict`, path `/api/v1/auth`,
  `Secure` when `APP_ENV=production`). Browsers must call the API with `credentials: "include"`. Strict means the
  cookie is never sent on navigation from another site; silent refresh only happens on same-site API calls.
- `POST /auth/refresh` rotates the refresh token (each works once) and sets the replacement cookie. Each login is a
  **family** of tokens; a retired token presented again outside a short grace window (`REFRESH_REUSE_GRACE_SECONDS`,
  default 10s) is treated as theft and the whole family is revoked, with an `auth.refresh_reuse` audit entry. Inside
  the window — two tabs refreshing at the same moment — the token is only rejected, so a race cannot log a real user
  out. A token whose family is revoked cannot refresh even if it had not expired.
- `POST /auth/logout` revokes the whole family and clears the cookie with matching flags, and the client drops its
  in-memory token plus saved-ids cache.
- Identity always comes from the token. No endpoint accepts a user id from the client.
- Anonymous visitors send `X-Session-Id` (8-64 characters: letters, digits, `-`, `_`) instead of a token.
- Roles: `customer`, `analyst`, `admin`, `ml_engineer`. Registration creates `customer` accounts only.

## Conventions

- **Errors** always look like `{"error": {"code", "message", "request_id", "details?"}}`. Codes include
  `unauthorized`, `forbidden`, `not_found`, `conflict`, `validation_error`, `rate_limited`, `payload_too_large`, `internal_error`.
- Every response carries `X-Request-ID`. Send your own (8-64 characters) to correlate logs.
- Money is returned as a decimal **string** (for example `"12.50"`), never a float.
- Recommendation `score` is a ranking score, not a purchase probability. Scores from different `source` values are not comparable.
- `POST /events`: `201` stored, `200` duplicate (same `idempotency_key`), `202` not stored because tracking is off.
  A `context` that carries `request_id` (and optionally `position`, `model_version`) is turned into attribution
  columns, so a click points at the impression — and the model version — that produced it.
- Rate limits (per IP): auth endpoints 10/min, recommendation endpoints 120/min. The limiter keeps
  counters in process memory, so it is per-worker; use one worker or shared storage before scaling out.
- Analytics are labelled `live_activity`. Offline evaluation lives under `/ml/experiments` and is labelled `offline_evaluation`.
  `/analytics/recommendations` returns its `definitions` alongside the numbers.
- **Impression**: a product a person could actually see (at least half the card on screen for a short dwell), not
  everything the API returned. `POST /recommendations/impressions` is keyed `request_id:product_id`, so a repeated
  report is ignored; a click that names the same key is an **attributed click**.

## Endpoints

| Method | Path | Who can call | Summary |
|---|---|---|---|
| GET | `/api/v1/admin/audit-logs` | admin | Audit Logs |
| GET | `/api/v1/admin/users` | admin | List Users |
| PATCH | `/api/v1/admin/users/{user_id}` | admin | Update User |
| GET | `/api/v1/analytics/categories` | analyst, admin | Categories |
| GET | `/api/v1/analytics/overview` | analyst, admin | Overview |
| GET | `/api/v1/analytics/recommendations` | analyst, admin | Recommendation Performance |
| GET | `/api/v1/analytics/segments` | analyst, admin | Segments |
| POST | `/api/v1/auth/login` | public (rate-limited) | Login |
| POST | `/api/v1/auth/logout` | public (rate-limited) | Logout |
| GET | `/api/v1/auth/me` | any logged-in user | Me |
| POST | `/api/v1/auth/refresh` | public (rate-limited) | Refresh |
| POST | `/api/v1/auth/register` | public (rate-limited) | Register |
| GET | `/api/v1/customers/me/collections` | logged-in customer (own data only) | List Lists |
| POST | `/api/v1/customers/me/collections` | logged-in customer (own data only) | Create List |
| GET | `/api/v1/customers/me/collections/{collection_id}` | logged-in customer (own data only) | Get List |
| PATCH | `/api/v1/customers/me/collections/{collection_id}` | logged-in customer (own data only) | Rename List |
| DELETE | `/api/v1/customers/me/collections/{collection_id}` | logged-in customer (own data only) | Delete List |
| PUT | `/api/v1/customers/me/collections/{collection_id}/items/{product_id}` | logged-in customer (own data only) | Add To List |
| DELETE | `/api/v1/customers/me/collections/{collection_id}/items/{product_id}` | logged-in customer (own data only) | Remove From List |
| POST | `/api/v1/customers/me/delete` | logged-in customer (own data only) | Delete Account |
| GET | `/api/v1/customers/me/export` | logged-in customer (own data only) | Export My Data |
| GET | `/api/v1/customers/me/history` | logged-in customer (own data only) | Get History |
| DELETE | `/api/v1/customers/me/history` | logged-in customer (own data only) | Clear History |
| DELETE | `/api/v1/customers/me/history/{product_id}` | logged-in customer (own data only) | Remove From History |
| GET | `/api/v1/customers/me/preferences` | logged-in customer (own data only) | Get Preferences |
| PATCH | `/api/v1/customers/me/preferences` | logged-in customer (own data only) | Update Preferences |
| DELETE | `/api/v1/customers/me/preferences` | logged-in customer (own data only) | Reset Preferences |
| GET | `/api/v1/customers/me/saved` | logged-in customer (own data only) | List Saved |
| PUT | `/api/v1/customers/me/saved/{product_id}` | logged-in customer (own data only) | Save Item |
| DELETE | `/api/v1/customers/me/saved/{product_id}` | logged-in customer (own data only) | Unsave Item |
| PATCH | `/api/v1/customers/me/settings` | logged-in customer (own data only) | Update Settings |
| POST | `/api/v1/events` | bearer token or X-Session-Id | Record Event |
| GET | `/api/v1/ml/experiments` | analyst, ml_engineer, admin | List Experiments |
| GET | `/api/v1/ml/health` | public | Ml Health |
| GET | `/api/v1/ml/models` | analyst, ml_engineer, admin | List Models |
| POST | `/api/v1/ml/models/scan` | ml_engineer, admin | Scan Models |
| POST | `/api/v1/ml/models/{version}/promote` | ml_engineer, admin | Promote |
| POST | `/api/v1/ml/training-runs` | ml_engineer, admin | Request Training Run |
| GET | `/api/v1/products` | public | List Products |
| POST | `/api/v1/products` | admin | Create Product |
| GET | `/api/v1/products/brands` | public | List Brands |
| GET | `/api/v1/products/categories` | public | List Categories |
| GET | `/api/v1/products/compare` | public | Compare Products |
| GET | `/api/v1/products/{product_id}` | public | Get Product |
| PATCH | `/api/v1/products/{product_id}` | admin | Update Product |
| GET | `/api/v1/products/{product_id}/related` | public | Related Products |
| POST | `/api/v1/recommendations/feedback` | bearer token or X-Session-Id | Record Feedback |
| GET | `/api/v1/recommendations/home` | public; bearer token or X-Session-Id personalises | Home Feed |
| POST | `/api/v1/recommendations/impressions` | bearer token or X-Session-Id | Record Impressions |
| GET | `/api/v1/recommendations/preferences` | bearer token or X-Session-Id | Get Stated Preferences |
| PATCH | `/api/v1/recommendations/preferences` | bearer token or X-Session-Id | Update Stated Preferences |
| GET | `/api/v1/recommendations/similar/{product_id}` | public; bearer token or X-Session-Id personalises | Similar |
| GET | `/api/v1/recommendations/trending` | public; bearer token or X-Session-Id personalises | Trending |
| GET | `/health` | see code | Health |
| GET | `/health/db` | see code | Health Db |

## Curated lists

A list is a named group of products that belongs to one customer. It is how the
saved items become something a person can organise, and it is the one customer
area where the collection itself is the resource rather than a single row.

- A customer keeps up to 20 lists, each with a unique name (compared exactly,
  after trimming and collapsing whitespace), holding up to 100 products.
- Adding a product that is already on a list changes nothing: the call is
  idempotent and only a first insertion counts. A first insertion also records a
  `save` event with `context.source = "collection"`, so the signal reaches the
  recommender the same way a plain save does, and a repeat does not inflate it.
- Someone else's list answers `404`, not `403`: a `403` would confirm that the id
  exists.
- Limits and duplicate names answer `409` with a message meant to be shown.
  Deleting a list removes its entries and never touches the products.

## Recommendation response

```json
{
  "request_id": "9f2c...",
  "model_version": "personaflux-v0.1-20261013-222549",
  "strategy": "session_based",
  "fallback_used": true,
  "recommendations": [
    {
      "product_id": "uuid",
      "product": { "id": "uuid", "title": "...", "category": "...", "price": null },
      "rank": 1,
      "score": 1.0,
      "source": "similarity",
      "reason_codes": ["similar_to_session_items"],
      "explanation": "Similar to \"...\", which you looked at recently."
    }
  ]
}
```

`strategy`: `personalized_hybrid`, `session_based`, `history_based`, `item_similarity`, or `popularity`.
`source`: `similarity`, `popularity`, or `popularity_fallback` (padding when personal signals run out).
`fallback_used` is true when any item came from `popularity_fallback`.
Reason codes: `similar_to_session_items`, `similar_to_history`, `item_similarity`, `popular`, `popular_in_category`,
`matches_stated_preference`, `catalog_default`. An explanation is only produced for a signal that actually fired.
