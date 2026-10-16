import type { TokenResponse } from "./types";
import { getSessionId } from "./storage";

const BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
export const API_ROOT = `${BASE}/api/v1`;

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId: string | null = null,
    public details: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// The access token lives in memory only. It is never written to storage.
let accessToken: string | null = null;
let authLostHandler: (() => void) | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}
export function getAccessToken(): string | null {
  return accessToken;
}
export function setAuthLostHandler(fn: (() => void) | null): void {
  authLostHandler = fn;
}

type Query = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Query;
  signal?: AbortSignal;
  /** Set on login/register/refresh/logout so a 401 is not retried through a refresh. */
  noRefresh?: boolean;
}

function buildUrl(path: string, query?: Query): string {
  const url = new URL(API_ROOT + path);
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  }
  return url.toString();
}

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const sid = getSessionId();
  if (sid) headers["X-Session-Id"] = sid;
  try {
    return await fetch(buildUrl(path, opts.query), {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      credentials: "include", // sends the HttpOnly refresh cookie to /auth/*
      signal: opts.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, "network_error", "Could not reach the server. Check your connection and try again.");
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T;
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    /* empty or non-JSON body */
  }
  if (!res.ok) {
    const e = (data as { error?: { code?: string; message?: string; request_id?: string; details?: unknown } } | null)?.error;
    throw new ApiError(
      res.status,
      e?.code ?? "http_error",
      e?.message ?? `Request failed (${res.status}).`,
      e?.request_id ?? res.headers.get("x-request-id"),
      e?.details ?? null,
    );
  }
  return data as T;
}

let refreshing: Promise<TokenResponse | null> | null = null;

async function doRefresh(): Promise<TokenResponse | null> {
  try {
    const res = await fetch(`${API_ROOT}/auth/refresh`, { method: "POST", credentials: "include" });
    if (res.status === 401) {
      accessToken = null;
      return null;
    }
    if (!res.ok) return null;
    const data = (await res.json()) as TokenResponse;
    accessToken = data.access_token;
    return data;
  } catch {
    return null; // network problem: keep the current state, do not log the user out
  }
}

/**
 * Exchanges the refresh cookie for a new access token. Calls made at the same moment share
 * one request, and a cross-tab lock stops two tabs from using the same (single-use) cookie.
 */
export function refreshSession(): Promise<TokenResponse | null> {
  if (!refreshing) {
    const run = () => doRefresh();
    const locked =
      typeof navigator !== "undefined" && "locks" in navigator
        ? navigator.locks.request("pf-refresh", run)
        : run();
    refreshing = locked.finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

export async function api<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  let res = await send(path, opts);
  if (res.status === 401 && accessToken && !opts.noRefresh) {
    const renewed = await refreshSession();
    if (renewed) {
      res = await send(path, opts);
    } else if (accessToken === null) {
      // The server rejected the refresh (401), so the session is really gone.
      // (A network failure leaves the token in place and does not log anyone out.)
      authLostHandler?.();
    }
  }
  return parse<T>(res);
}
