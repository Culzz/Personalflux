const base = import.meta.env.VITE_API_URL || "";

function sessionId() {
  let id = localStorage.getItem("pf-session");
  if (!id) {
    id = "sess-" + Math.random().toString(36).slice(2, 14);
    localStorage.setItem("pf-session", id);
  }
  return id;
}

export function isLoggedIn() {
  return !!localStorage.getItem("pf-token");
}

export function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("pf-token");
  if (token) return { Authorization: `Bearer ${token}` };
  return { "X-Session-Id": sessionId() };
}

async function req(path: string, init?: RequestInit) {
  const res = await fetch(base + path, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

const cache = new Map<string, { at: number; data: unknown }>();
async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < ttlMs) return hit.data as T;
  const data = await fn();
  cache.set(key, { at: Date.now(), data });
  return data;
}

export type Product = {
  id: string;
  title: string;
  description: string | null;
  category: string | null;
  price: string | null;
  image_url: string | null;
};

export type RecItem = {
  product_id: string;
  product: Product;
  rank: number;
  score: number;
  source: string;
  reason_codes: string[];
  explanation: string;
};

export type RecResponse = {
  request_id: string | null;
  model_version: string | null;
  strategy: string;
  fallback_used: boolean;
  recommendations: RecItem[];
};

export type Prefs = {
  explicit: Record<string, unknown>;
  inferred: {
    long_term_categories: { category: string; share: number }[];
    recent_categories: { category: string; share: number }[];
    events_considered: number;
  };
  profile_reset_at: string | null;
};

export const api = {
  home: (): Promise<RecResponse> =>
    cached("home", 30000, () => req("/api/v1/recommendations/home")),
  trending: (): Promise<RecResponse> =>
    cached("trending", 60000, () => req("/api/v1/recommendations/trending")),
  products: (q = ""): Promise<{ items: Product[] }> =>
    cached(`products:${q}`, 30000, () =>
      req("/api/v1/products?page_size=24" + (q ? `&q=${encodeURIComponent(q)}` : ""))
    ),
  categories: (): Promise<{ category: string; products: number }[]> =>
    cached("cats", 300000, () => req("/api/v1/products/categories")),
  product: (id: string): Promise<Product> =>
    cached(`p:${id}`, 60000, () => req(`/api/v1/products/${id}`)),
  similar: (id: string): Promise<RecResponse> =>
    cached(`sim:${id}`, 60000, () => req(`/api/v1/recommendations/similar/${id}`)),
  login: async (email: string, password: string) => {
    const data = await req("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("pf-token", data.access_token);
    cache.clear();
    return data;
  },
  register: async (email: string, password: string) => {
    const data = await req("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("pf-token", data.access_token);
    cache.clear();
    return data;
  },
  logout() {
    localStorage.removeItem("pf-token");
    cache.clear();
  },
  event: (product_id: string, event_type: string) =>
    req("/api/v1/events", {
      method: "POST",
      body: JSON.stringify({ product_id, event_type }),
    }).catch(() => null),
  saved: (): Promise<{ product: Product }[]> => req("/api/v1/customers/me/saved"),
  save: (id: string) =>
    req(`/api/v1/customers/me/saved/${id}`, { method: "PUT" }).catch(() =>
      req("/api/v1/recommendations/feedback", {
        method: "POST",
        body: JSON.stringify({ product_id: id, feedback: "save" }),
      }).catch(() => null)
    ),
  unsave: (id: string) => req(`/api/v1/customers/me/saved/${id}`, { method: "DELETE" }).catch(() => null),
  prefs: (): Promise<Prefs> => req("/api/v1/customers/me/preferences"),
  updatePrefs: (body: object): Promise<Prefs> =>
    req("/api/v1/customers/me/preferences", { method: "PATCH", body: JSON.stringify(body) }),
  resetPrefs: (): Promise<Prefs> => req("/api/v1/customers/me/preferences", { method: "DELETE" }),
};
