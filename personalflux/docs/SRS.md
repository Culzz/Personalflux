# Requirements

PersonaFlux personalises a single storefront. The scope is deliberately small:
one deployment, no marketplace, no payments. This note collects the functional
scope, the non-functional targets, and what version 1 refuses to do, so the
rest of the docs have something to point at.

## Functional (v1)

1. **Shop the catalog.** Browse, search by title, open a product, see related
   items.
2. **Recommend.** A personalised home feed plus similar and trending lists.
   Every item carries an explanation for a signal that actually fired. Anonymous
   visitors get popularity until they consent.
3. **Learn from behaviour.** Record view, click, search, cart, purchase, save and
   dismiss events, with consent, exactly once per event.
4. **Let customers stay in control.** Saved items, stated preferences, history,
   data export and account deletion.
5. **Operate the model.** Register artifacts, keep offline evaluation separate
   from live activity, promote or roll back a version. Analysts and admins see
   live activity; ML staff see offline evaluation.

## Non-functional

- **Latency.** Recommendation p95 is measured in-process and surfaced at
  `GET /api/v1/ml/health`. Target: comfortably interactive on the reference
  dataset (see *Load shape*).
- **Availability.** A single node, so no formal SLA yet. The API degrades rather
  than fails: no model artifact means database popularity; a dead database makes
  `/health/db` return 503 while `/health` stays up.
- **Durability.** Postgres holds all state and must be backed up. Events are
  append-only; deletion of an account cascades.
- **Security.** Argon2id passwords, short access tokens held in memory, rotating
  HttpOnly refresh cookies, per-IP rate limits, role-based access, audited admin
  actions. Details in `PRIVACY_AND_SECURITY.md`; endpoint list in `API.md`.

## Non-goals (v1)

- Payments, checkout, orders, shipping.
- Email or push notifications.
- Real-time transport (WebSockets/SSE); plain request/response HTTP only.
- Multi-tenant or multi-region operation.
- Online learning in the serving path. Training is offline and promotion is manual.

## Load shape

Read-heavy. Product and feed reads dominate; writes are single-row event inserts
plus the occasional save or preference change. The reference deployment is sized
for a handful of requests per second with 2-3x peaks, which one Postgres node
handles without a cache, queue or replica. The numeric estimates and the exact
triggers for adding those live in `ARCHITECTURE.md`.
