# PersonaFlux frontend

React 19 + TypeScript + Vite + Tailwind 4. Talks to the FastAPI backend (see `docs/API.md`).

## Run

```cmd
cd frontend
npm install
npm run dev        :: http://localhost:5173  (backend must be running on http://localhost:8000)
npm test           :: 60 tests (vitest + Testing Library)
npm run build      :: type-checks, then builds to dist/
```

Optional: copy `.env.example` to `.env` to change `VITE_API_URL`. Always use `localhost`, not `127.0.0.1`,
or the refresh cookie will not be sent.

## How it is organised

```
src/
  lib/          api.ts (client + token refresh), endpoints.ts (typed calls), types.ts, storage.ts, format.ts
  features/     consent/  auth/  tracking/  saved/  cart/    (React contexts and hooks)
  components/   Layout, ConsentBanner, ProductCard, RecommendationList, SaveButton, States, Pagination ...
  pages/        Home, Discover, Product, Cart, Saved, Preferences, History, Settings, Login/Register
  test/         utilities (fetch mock router) and tests
```

## Rules the code follows (and the tests enforce)

- **Nothing is sent about a visitor until they allow personalisation.** Events, impressions, feedback and the
  `X-Session-Id` header are all gated by `useTracking().canTrack`. Declining also deletes any stored session id.
- **Searches record the category only, never the words typed.**
- **The access token lives in memory only.** The refresh token is an HttpOnly cookie the browser handles.
  Simultaneous 401s share one refresh, and a cross-tab lock keeps two tabs from reusing the single-use cookie.
  A network failure during refresh does not sign anyone out; only a server 401 does.
- **Explanations are shown exactly as the server sends them.** The UI never invents a reason.
- **The demo cart is local and fake.** It exists so add-to-cart and purchase signals can be exercised.
  No payment, no order.
- Prices are strings from the API and are never converted to floating point for storage.
- The dataset has no product names, photos or prices. Items show their id and category, with a colour tile
  instead of a picture.
