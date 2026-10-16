import { api } from "./api";
import type {
  CategoryCount, EventType, PreferencesResponse, Product, ProductPage,
  RecommendationResponse, SavedProduct, TokenResponse, User, ViewedProduct,
} from "./types";

type Sig = AbortSignal | undefined;

export const authApi = {
  login: (email: string, password: string) =>
    api<TokenResponse>("/auth/login", { method: "POST", body: { email, password }, noRefresh: true }),
  register: (email: string, password: string, tracking_consent: boolean) =>
    api<TokenResponse>("/auth/register", {
      method: "POST", body: { email, password, tracking_consent }, noRefresh: true,
    }),
  logout: () => api<void>("/auth/logout", { method: "POST", noRefresh: true }),
};

export interface ProductQuery {
  q?: string; category?: string; min_price?: string; max_price?: string;
  sort?: string; page?: number; page_size?: number;
}

export const productsApi = {
  list: (query: ProductQuery, signal?: Sig) => api<ProductPage>("/products", { query: { ...query }, signal }),
  get: (id: string, signal?: Sig) => api<Product>(`/products/${id}`, { signal }),
  categories: (signal?: Sig) => api<CategoryCount[]>("/products/categories", { signal }),
  related: (id: string, signal?: Sig) => api<Product[]>(`/products/${id}/related`, { signal }),
};

export const recsApi = {
  home: (query: { limit?: number; category?: string }, signal?: Sig) =>
    api<RecommendationResponse>("/recommendations/home", { query, signal }),
  similar: (id: string, limit = 8, signal?: Sig) =>
    api<RecommendationResponse>(`/recommendations/similar/${id}`, { query: { limit }, signal }),
  trending: (query: { limit?: number; category?: string }, signal?: Sig) =>
    api<RecommendationResponse>("/recommendations/trending", { query, signal }),
  impressions: (body: {
    request_id: string; model_version: string | null;
    items: { product_id: string; position: number }[];
  }) => api<unknown>("/recommendations/impressions", { method: "POST", body }),
  feedback: (body: { product_id: string; feedback: "save" | "dismiss"; request_id?: string | null }) =>
    api<unknown>("/recommendations/feedback", { method: "POST", body }),
};

export const eventsApi = {
  send: (body: {
    event_type: EventType; product_id?: string; idempotency_key?: string;
    context?: Record<string, string | number | boolean>;
  }) => api<unknown>("/events", { method: "POST", body }),
};

export const customerApi = {
  preferences: (signal?: Sig) => api<PreferencesResponse>("/customers/me/preferences", { signal }),
  updatePreferences: (body: {
    liked_categories?: string[]; blocked_categories?: string[];
    price_range?: { min: string | null; max: string | null } | null;
  }) => api<PreferencesResponse>("/customers/me/preferences", { method: "PATCH", body }),
  resetPreferences: (includeExplicit: boolean) =>
    api<PreferencesResponse>("/customers/me/preferences", {
      method: "DELETE", query: { include_explicit: includeExplicit },
    }),
  history: (limit = 30, signal?: Sig) => api<ViewedProduct[]>("/customers/me/history", { query: { limit }, signal }),
  removeFromHistory: (id: string) => api<void>(`/customers/me/history/${id}`, { method: "DELETE" }),
  clearHistory: () => api<void>("/customers/me/history", { method: "DELETE" }),
  saved: (signal?: Sig) => api<SavedProduct[]>("/customers/me/saved", { signal }),
  save: (id: string) => api<void>(`/customers/me/saved/${id}`, { method: "PUT" }),
  unsave: (id: string) => api<void>(`/customers/me/saved/${id}`, { method: "DELETE" }),
  updateSettings: (tracking_consent: boolean) =>
    api<User>("/customers/me/settings", { method: "PATCH", body: { tracking_consent } }),
  exportData: () => api<unknown>("/customers/me/export"),
  deleteAccount: (password: string) =>
    api<void>("/customers/me/delete", { method: "POST", body: { password } }),
};
