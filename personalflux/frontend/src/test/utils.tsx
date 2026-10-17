import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import App from "../App";
import type { Product, Recommendation, RecommendationResponse, TokenResponse, User } from "../lib/types";

export interface Call {
  method: string;
  path: string;
  search: URLSearchParams;
  headers: Record<string, string>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  body: any;
}

type Handler = unknown | ((call: Call) => unknown);

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export function apiError(status: number, code: string, message: string): Response {
  return json({ error: { code, message, request_id: "req-test" } }, status);
}

/** Replaces fetch with a router keyed by "METHOD /path" (path without /api/v1). null = 204. */
export function mockApi(routes: Record<string, Handler>) {
  const calls: Call[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.toString() : (input as Request).url);
    const method = (init?.method ?? "GET").toUpperCase();
    const call: Call = {
      method,
      path: url.pathname.replace("/api/v1", ""),
      search: url.searchParams,
      headers: (init?.headers ?? {}) as Record<string, string>,
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    };
    calls.push(call);
    const key = `${method} ${call.path}`;
    if (!(key in routes)) return apiError(404, "not_found", `No mock for ${key}`);
    const h = routes[key];
    const out = typeof h === "function" ? (h as (c: Call) => unknown)(call) : h;
    if (out instanceof Response) return out;
    if (out === null) return new Response(null, { status: 204 });
    return json(out);
  });
  return {
    calls,
    called: (key: string) => calls.filter((c) => `${c.method} ${c.path}` === key),
  };
}

export function renderApp(route = "/") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <App />
    </MemoryRouter>,
  );
}

export const product = (id: string, extra: Partial<Product> = {}): Product => ({
  id, title: `Item ${id}`, description: null, category: "Category A", price: "9.99",
  image_url: null, brand: null, stock: null, currency: null, external_url: null,
  is_active: true, catalog_source: "retailrocket", ...extra,
});

export const rec = (p: Product, rank: number, explanation: string, source: Recommendation["source"] = "similarity"): Recommendation => ({
  product_id: p.id, product: p, rank, score: 1 / rank, source, reason_codes: ["x"], explanation,
});

export const feed = (recs: Recommendation[], extra: Partial<RecommendationResponse> = {}): RecommendationResponse => ({
  request_id: "req-feed", model_version: "v1", strategy: "session_based", fallback_used: false,
  recommendations: recs, ...extra,
});

export const user = (extra: Partial<User> = {}): User => ({
  id: "u1", email: "ann@shop.dev", role: "customer", tracking_consent: true,
  created_at: "2026-01-01T00:00:00Z", ...extra,
});

export const token = (u: User = user()): TokenResponse => ({
  access_token: "tok-1", token_type: "bearer", expires_in: 1800, user: u,
});

/** Routes every page needs so that rendering does not hit an unmocked endpoint. */
export const baseRoutes = (over: Record<string, Handler> = {}): Record<string, Handler> => ({
  "GET /recommendations/home": feed([]),
  "GET /recommendations/trending": feed([], { request_id: "req-trend", strategy: "popularity" }),
  "GET /products/categories": [],
  "POST /recommendations/impressions": { stored: 1 },
  "POST /events": { stored: true },
  ...over,
});

/** Starts the app already signed in (silent refresh succeeds). */
export function signedIn(over: Record<string, Handler> = {}, u: User = user()): Record<string, Handler> {
  localStorage.setItem("pf_has_session", "1");
  return baseRoutes({
    "POST /auth/refresh": token(u),
    "GET /customers/me/saved": [],
    "GET /customers/me/history": [],
    ...over,
  });
}
