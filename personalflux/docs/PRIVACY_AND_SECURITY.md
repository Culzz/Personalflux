# Privacy and security

## What is collected

- Account: email and an Argon2id password hash. Nothing else is asked.
- Behavioural events the customer actually generated: views, clicks, searches
  (category only, never the words typed), comparisons, carts, purchases, saves,
  dismissals, plus recommendation impressions with rank and model version.
- Explicit preferences the customer stated (liked/blocked categories, price range)
  and tracking consent. Inferred interests are computed, never stored.

## Consent and control

- Personalisation runs on consent. The banner offers allow/deny; denying still
  leaves a working shop with popularity fallback.
- Customers can view, reset, export (`GET /customers/me/export`) and delete
  (`POST /customers/me/delete`, password-confirmed, cascades to events,
  preferences, saved items, curated lists, impressions and sessions) their data.
- History can be cleared per item or wiped entirely.

## Transport and sessions

- HTTPS in deployment; `Secure` refresh cookies in production.
- Refresh cookie: HttpOnly, `SameSite=Strict`, scoped to `/api/v1/auth`.
  Access tokens are short-lived JWTs kept in frontend memory only.
- Refresh tokens rotate on each use; reuse revokes every session of that user.
- CORS allow-lists the storefront origin only. Auth endpoints are rate-limited
  (10/min per IP); recommendation endpoints 120/min.

## Access control

- Roles: customer, analyst, admin, ml_engineer. Registration creates customers only.
- Every customer endpoint derives identity from the token; cross-user access is
  denied and tested. Analytics endpoints return aggregates, never individual histories.
- Admin actions (products, users, model promotion) are audited.

## Retention

- Refresh tokens expire after 14 days; access tokens after 30 minutes.
- Behavioural events have no fixed expiry yet; account deletion removes them.
  Set a retention job before using this with real customers.

## ML safety

- Explanations are generated from ranking signals that actually fired, never invented.
- Popularity bias and coverage are tracked; offline metrics and live outcomes are
  reported separately. Model promotion is explicit and reversible.

## Operator checklist

- Long random `JWT_SECRET_KEY`, `APP_ENV=production`, managed Postgres with backups.
- Review `JWT_SECRET_KEY`, CORS origins, and cookie flags on every deploy.
- Keep dependencies updated; production errors never return stack traces or secrets.
