const base = import.meta.env.VITE_API_URL || "";

function sessionId() {
  let id = localStorage.getItem("pf-session");
  if (!id) {
    id = "sess-" + Math.random().toString(36).slice(2, 14);
    localStorage.setItem("pf-session", id);
  }
  return id;
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

export const api = {
  home: (): Promise<RecResponse> => req("/api/v1/recommendations/home"),
  trending: (): Promise<RecResponse> => req("/api/v1/recommendations/trending"),
  products: (q = ""): Promise<{ items: Product[] }> =>
    req("/api/v1/products?page_size=24" + (q ? `&q=${encodeURIComponent(q)}` : "")),
  product: (id: string): Promise<Product> => req(`/api/v1/products/${id}`),
  similar: (id: string): Promise<RecResponse> =>
    req(`/api/v1/recommendations/similar/${id}`),
  login: async (email: string, password: string) => {
    const data = await req("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("pf-token", data.access_token);
    return data;
  },
  register: async (email: string, password: string) => {
    const data = await req("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("pf-token", data.access_token);
    return data;
  },
  event: (product_id: string, event_type: string) =>
    req("/api/v1/events", {
      method: "POST",
      body: JSON.stringify({ product_id, event_type }),
    }).catch(() => null),
};
