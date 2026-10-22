import { describe, expect, it, vi } from "vitest";
import { ApiError, api, getAccessToken, setAccessToken, setAuthLostHandler } from "../lib/api";
import { clearSessionId, getSessionId, readConsent, writeConsent } from "../lib/storage";
import { formatPrice, newKey } from "../lib/format";
import { apiError, mockApi, token } from "./utils";

describe("storage and consent", () => {
  it("gives no session id until the visitor allows personalisation", () => {
    expect(getSessionId()).toBeNull();
    writeConsent("denied");
    expect(getSessionId()).toBeNull();
    expect(localStorage.getItem("pf_session_id")).toBeNull();
  });

  it("creates one stable id after consent and can forget it", () => {
    writeConsent("granted");
    const id = getSessionId();
    expect(id).toMatch(/^[A-Za-z0-9_-]{8,64}$/);
    expect(getSessionId()).toBe(id);
    clearSessionId();
    expect(getSessionId()).not.toBe(id);
  });

  it("ignores junk consent values", () => {
    localStorage.setItem("pf_consent", "maybe");
    expect(readConsent()).toBeNull();
  });
});

describe("format helpers", () => {
  it("formats exact decimal strings and missing prices", () => {
    expect(formatPrice("12.5")).toBe("12.50");
    expect(formatPrice("1234.5")).toBe("1,234.50");
    expect(formatPrice(null)).toBe("Price not listed");
    expect(formatPrice("abc")).toBe("Price not listed");
  });

  it("makes keys the API accepts", () => {
    for (let i = 0; i < 20; i++) expect(newKey("view")).toMatch(/^[A-Za-z0-9_-]{8,64}$/);
  });
});

describe("api client", () => {
  it("sends the bearer token and session id only when they exist", async () => {
    const m = mockApi({ "GET /ping": { ok: true } });
    await api("/ping");
    expect(m.calls[0].headers.Authorization).toBeUndefined();
    expect(m.calls[0].headers["X-Session-Id"]).toBeUndefined();

    writeConsent("granted");
    setAccessToken("abc");
    await api("/ping");
    expect(m.calls[1].headers.Authorization).toBe("Bearer abc");
    expect(m.calls[1].headers["X-Session-Id"]).toMatch(/^sess-/);
  });

  it("always sends credentials so the refresh cookie travels", async () => {
    mockApi({ "GET /ping": {} });
    await api("/ping");
    expect((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].credentials).toBe("include");
  });

  it("skips empty query values", async () => {
    const m = mockApi({ "GET /ping": {} });
    await api("/ping", { query: { a: "1", b: "", c: undefined, d: null, e: 0 } });
    expect([...m.calls[0].search.keys()]).toEqual(["a", "e"]);
  });

  it("turns the standard error body into an ApiError", async () => {
    mockApi({ "GET /ping": apiError(404, "not_found", "Product not found.") });
    await expect(api("/ping")).rejects.toMatchObject({
      name: "ApiError", status: 404, code: "not_found", message: "Product not found.", requestId: "req-test",
    });
  });

  it("reports unreachable servers as a friendly ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    const err = (await api("/ping").catch((e: unknown) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
    expect(err.message).toMatch(/could not reach the server/i);
  });

  it("returns undefined for 204 responses", async () => {
    mockApi({ "DELETE /thing": null });
    await expect(api("/thing", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("shares ONE refresh between simultaneous 401s, then retries each request", async () => {
    setAccessToken("old");
    let refreshCalls = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        refreshCalls++;
        await new Promise((r) => setTimeout(r, 10));
        return new Response(JSON.stringify(token()), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      const auth = (init?.headers as Record<string, string>).Authorization;
      return auth === "Bearer tok-1"
        ? new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "Content-Type": "application/json" } })
        : apiError(401, "unauthorized", "Invalid or expired token.");
    });
    const results = await Promise.all([api("/a"), api("/b"), api("/c")]);
    expect(results).toEqual([{ ok: true }, { ok: true }, { ok: true }]);
    expect(refreshCalls).toBe(1);
    expect(getAccessToken()).toBe("tok-1");
  });

  it("clears the token and tells the app when the server rejects the refresh", async () => {
    setAccessToken("old");
    const lost = vi.fn();
    setAuthLostHandler(lost);
    mockApi({ "GET /a": apiError(401, "unauthorized", "x"), "POST /auth/refresh": apiError(401, "unauthorized", "x") });
    await expect(api("/a")).rejects.toMatchObject({ status: 401 });
    expect(getAccessToken()).toBeNull();
    expect(lost).toHaveBeenCalledTimes(1);
  });

  it("does NOT log anyone out when the refresh fails only because of the network", async () => {
    setAccessToken("old");
    const lost = vi.fn();
    setAuthLostHandler(lost);
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).endsWith("/auth/refresh")) throw new TypeError("offline");
      return apiError(401, "unauthorized", "x");
    });
    await expect(api("/a")).rejects.toMatchObject({ status: 401 });
    expect(getAccessToken()).toBe("old");
    expect(lost).not.toHaveBeenCalled();
  });

  it("does not try to refresh for login-style calls", async () => {
    setAccessToken("old");
    const m = mockApi({ "POST /auth/login": apiError(401, "unauthorized", "Incorrect email or password.") });
    await expect(api("/auth/login", { method: "POST", body: {}, noRefresh: true })).rejects.toBeInstanceOf(ApiError);
    expect(m.called("POST /auth/refresh")).toHaveLength(0);
  });
});
