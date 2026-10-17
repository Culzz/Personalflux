import { api } from "./api";
import type {
  BrandCount, CategoryCount, EventType, PreferencesResponse, Product, ProductPage,
  RecommendationResponse, SavedProduct, StatedPreferences, TokenResponse, User, ViewedProduct,
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
  brands: (signal?: Sig) => api<BrandCount[]>("/products/brands", { signal }),
  related: (id: string, signal?: Sig) => api<Product[]>(`/products/${id}/related`, { signal }),
  create: (body: { title: string; description?: string | null; category?: string | null; price?: string | null; image_url?: string | null; is_active?: boolean }) =>
    api<Product>("/products", { method: "POST", body }),
  update: (id: string, body: { title?: string; description?: string | null; category?: string | null; price?: string | null; image_url?: string | null; is_active?: boolean }) =>
    api<Product>(`/products/${id}`, { method: "PATCH", body }),
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
  statedPreferences: (signal?: Sig) =>
    api<StatedPreferences>("/recommendations/preferences", { signal }),
  updateStatedPreferences: (body: {
    liked_categories?: string[]; blocked_categories?: string[]; liked_brands?: string[];
    price_range?: { min: string | null; max: string | null } | null;
  }) => api<StatedPreferences>("/recommendations/preferences", { method: "PATCH", body }),
};

export const eventsApi = {
  send: (body: {
    event_type: EventType; product_id?: string; idempotency_key?: string;
    context?: Record<string, string | number | boolean>;
  }) => api<unknown>("/events", { method: "POST", body }),
};

export const customerApi = {  preferences: (signal?: Sig) => api<PreferencesResponse>("/customers/me/preferences", { signal }),
  updatePreferences: (body: {
    liked_categories?: string[]; blocked_categories?: string[]; liked_brands?: string[];
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

export interface AnalyticsOverview {
  kind: string;
  window_days: number;
  customers_total: number;
  events_total: number;
  events_by_type: Record<string, number>;
  active_customers: number | null;
  anonymous_sessions: number | null;
  impressions: number;
}

export interface AnalyticsCategories {
  categories: { category: string; events: number; views: number; add_to_cart: number; purchases: number }[];
}

export interface AnalyticsSegments {
  segments: { segment: string; customers: number }[];
}

export interface AnalyticsRecs {
  impressions: number;
  recommendation_requests_with_impressions: number;
  engagement_from_recommendations: Record<string, number>;
  click_through_rate: number | null;
}

export interface MlHealth {
  status: string;
  model_loaded: boolean;
  model_version: string | null;
  fallback_mode: string | null;
}

export const analyticsApi = {
  overview: (days = 30, signal?: Sig) =>
    api<AnalyticsOverview>("/analytics/overview", { query: { days }, signal }).catch(() => null),
  categories: (days = 30, signal?: Sig) =>
    api<AnalyticsCategories>("/analytics/categories", { query: { days }, signal }).catch(() => null),
  segments: (days = 30, signal?: Sig) =>
    api<AnalyticsSegments>("/analytics/segments", { query: { days }, signal }).catch(() => null),
  recs: (days = 30, signal?: Sig) =>
    api<AnalyticsRecs>("/analytics/recommendations", { query: { days }, signal }).catch(() => null),
};

export const mlApi = {
  health: (signal?: Sig) => api<MlHealth>("/ml/health", { signal }).catch(() => null),
  models: (signal?: Sig) => api<{ serving: string | null; versions: ModelVersion[] }>("/ml/models", { signal }),
  scan: () => api<{ added: ModelVersion[] }>("/ml/models/scan", { method: "POST" }),
  promote: (version: string) => api<ModelVersion>(`/ml/models/${encodeURIComponent(version)}/promote`, { method: "POST" }),
  experiments: (signal?: Sig) => api<Experiment[]>("/ml/experiments", { signal }),
};

export interface ModelVersion {
  version: string;
  status: string;
  details: string | null;
  created_at: string;
  promoted_at: string | null;
}

export interface Experiment {
  id: string;
  name: string;
  configuration: Record<string, unknown>;
  created_at: string;
  kind: string;
  runs: { model_version: string; metrics: Record<string, number> }[];
}

export interface AdminUser {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AuditLog {
  id: string;
  actor_user_id: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export const adminApi = {
  users: (signal?: Sig) => api<AdminUser[]>("/admin/users", { signal }),
  updateUser: (id: string, body: { role?: string; is_active?: boolean }) =>
    api<AdminUser>(`/admin/users/${id}`, { method: "PATCH", body }),
  auditLogs: (signal?: Sig) => api<AuditLog[]>("/admin/audit-logs", { signal }),
};
