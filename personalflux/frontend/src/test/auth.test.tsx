import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { apiError, baseRoutes, mockApi, renderApp, signedIn, token, user } from "./utils";

describe("signing in and out", () => {
  it("sends anonymous visitors from a protected page to sign in", async () => {
    mockApi(baseRoutes());
    renderApp("/saved");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("signs in, shows the account, adopts the account's consent, and returns to where they were going", async () => {
    const m = mockApi(baseRoutes({
      "POST /auth/login": token(user({ tracking_consent: true })),
      "GET /customers/me/saved": [], "GET /customers/me/history": [],
    }));
    renderApp("/login");
    const u = userEvent.setup();
    await u.type(await screen.findByLabelText("Email"), "ann@shop.dev");
    await u.type(screen.getByLabelText("Password"), "correct-horse-battery");
    await u.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("ann@shop.dev")).toBeInTheDocument();
    expect(m.called("POST /auth/login")[0].body).toEqual({ email: "ann@shop.dev", password: "correct-horse-battery" });
    expect(localStorage.getItem("pf_consent")).toBe("granted");
    expect(localStorage.getItem("pf_has_session")).toBe("1");
  });

  it("shows the server's message for wrong credentials and stays on the form", async () => {
    mockApi(baseRoutes({ "POST /auth/login": apiError(401, "unauthorized", "Incorrect email or password.") }));
    renderApp("/login");
    const u = userEvent.setup();
    await u.type(await screen.findByLabelText("Email"), "ann@shop.dev");
    await u.type(screen.getByLabelText("Password"), "wrong-password-1");
    await u.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("registers with tracking OFF unless the box is ticked", async () => {
    const m = mockApi(baseRoutes({ "POST /auth/register": token(user({ tracking_consent: false })) }));
    renderApp("/register");
    const u = userEvent.setup();
    await u.type(await screen.findByLabelText("Email"), "new@shop.dev");
    await u.type(screen.getByLabelText("Password"), "a-long-password");
    await u.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() => expect(m.called("POST /auth/register")).toHaveLength(1));
    expect(m.called("POST /auth/register")[0].body.tracking_consent).toBe(false);
    expect(localStorage.getItem("pf_consent")).toBe("denied");
  });

  it("registers with tracking ON when the visitor ticks the box", async () => {
    const m = mockApi(baseRoutes({ "POST /auth/register": token() }));
    renderApp("/register");
    const u = userEvent.setup();
    await u.type(await screen.findByLabelText("Email"), "new@shop.dev");
    await u.type(screen.getByLabelText("Password"), "a-long-password");
    await u.click(screen.getByRole("checkbox"));
    await u.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() => expect(m.called("POST /auth/register")).toHaveLength(1));
    expect(m.called("POST /auth/register")[0].body.tracking_consent).toBe(true);
  });

  it("restores a returning session silently through the refresh cookie", async () => {
    mockApi(signedIn());
    renderApp("/");
    expect(await screen.findByText("ann@shop.dev")).toBeInTheDocument();
  });

  it("falls back to anonymous when the refresh is rejected, and forgets the hint", async () => {
    localStorage.setItem("pf_has_session", "1");
    mockApi(baseRoutes({ "POST /auth/refresh": apiError(401, "unauthorized", "Invalid session.") }));
    renderApp("/");
    expect(await screen.findByRole("link", { name: "Sign in" })).toBeInTheDocument();
    expect(localStorage.getItem("pf_has_session")).toBeNull();
  });

  it("does not even try a refresh for a visitor who never signed in", async () => {
    const m = mockApi(baseRoutes());
    renderApp("/");
    await screen.findByRole("heading", { name: "Recommended for you" });
    expect(m.called("POST /auth/refresh")).toHaveLength(0);
  });

  it("signs out", async () => {
    const m = mockApi(signedIn({ "POST /auth/logout": null }));
    renderApp("/");
    const u = userEvent.setup();
    await u.click(await screen.findByText("ann@shop.dev"));
    await u.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("link", { name: "Sign in" })).toBeInTheDocument();
    expect(m.called("POST /auth/logout")).toHaveLength(1);
    expect(localStorage.getItem("pf_has_session")).toBeNull();
  });
});
