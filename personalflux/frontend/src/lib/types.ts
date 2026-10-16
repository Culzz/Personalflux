// Shapes returned by the PersonaFlux API (see docs/API.md).

export interface User {
  id: string;
  email: string;
  role: "customer" | "analyst" | "admin" | "ml_engineer";
  tracking_consent: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Product {
  id: string;
  title: string;
  description: string | null;
  category: string | null;
  price: string | null; // exact decimal as a string, e.g. "12.50"
  image_url: string | null;
  is_active: boolean;
  catalog_source: string;
}

export interface ProductPage {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

export interface CategoryCount {
  category: string;
  products: number;
}

export type RecSource = "similarity" | "popularity" | "popularity_fallback";

export interface Recommendation {
  product_id: string;
  product: Product;
  rank: number;
  score: number; // a ranking score, not a purchase probability
  source: RecSource;
  reason_codes: string[];
  explanation: string;
}

export interface RecommendationResponse {
  request_id: string | null;
  model_version: string | null;
  strategy: string;
  fallback_used: boolean;
  recommendations: Recommendation[];
}

export interface CategoryShare {
  category: string;
  share: number;
}

export interface PreferencesResponse {
  explicit: {
    liked_categories?: string[];
    blocked_categories?: string[];
    price_range?: { min: string | null; max: string | null };
  };
  inferred: {
    long_term_categories: CategoryShare[];
    recent_categories: CategoryShare[];
    events_considered: number;
    note: string;
  };
  profile_reset_at: string | null;
}

export interface ViewedProduct {
  product: Product;
  last_seen: string;
}

export interface SavedProduct {
  product: Product;
  saved_at: string;
}

export type EventType =
  | "view"
  | "click"
  | "search"
  | "compare"
  | "add_to_cart"
  | "purchase"
  | "save"
  | "dismiss";
