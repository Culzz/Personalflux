import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { apiError, mockApi, product, renderApp, signedIn, user } from "./utils";

const prefs = {
  explicit: { liked_categories: ["Category A"], price_range: { min: "5", max: "50" } },
  inferred: {
    long_term_categories: [{ category: "Category B", share: 1 }],
    recent_categories: [{ category: "Category A", share: 0.75 }, { category: "Category B", share: 0.25 }],
    events_considered: 4, note: "Inferred from your activity. You can reset it at any time.",
  },
  profile_reset_at: null,
};
const cats = [{ category: "Category A", products: 2 }, { category: "Category B", products: 2 }];

describe("preferences", () => {
  it("shows what was stated and what was inferred, separately", async () => {
    mockApi(signedIn({ "GET /customers/me/preferences": prefs, "GET /products/categories": cats }));
    renderApp("/preferences");
    expect(await screen.findByRole("heading", { name: "What you told us" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What we inferred from your activity" })).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText(/Based on 4 recorded events/)).toBeInTheDocument();
    const liked = screen.getByRole("group", { name: "Categories I like" });
    expect(within(liked).getByRole("checkbox", { name: "Category A" })).toBeChecked();
  });

  it("saves the stated choices, moving a category between 'like' and 'hide'", async () => {
    const m = mockApi(signedIn({
      "GET /customers/me/preferences": prefs, "GET /products/categories": cats,
      "PATCH /customers/me/preferences": prefs,
    }));
    renderApp("/preferences");
    const u = userEvent.setup();
    const hide = await screen.findByRole("group", { name: "Categories to hide" });
    await u.click(within(hide).getByRole("checkbox", { name: "Category A" }));   // was liked -> now hidden
    await u.click(screen.getByRole("button", { name: "Save preferences" }));
    await waitFor(() => expect(m.called("PATCH /customers/me/preferences")).toHaveLength(1));
    expect(m.called("PATCH /customers/me/preferences")[0].body).toEqual({
      liked_categories: [], blocked_categories: ["Category A"], price_range: { min: "5", max: "50" },
    });
  });

  it("refuses a backwards price range", async () => {
    const m = mockApi(signedIn({ "GET /customers/me/preferences": prefs, "GET /products/categories": cats }));
    renderApp("/preferences");
    const u = userEvent.setup();
    const min = await screen.findByLabelText("Min price");
    await u.clear(min);
    await u.type(min, "99");
    await u.click(screen.getByRole("button", { name: "Save preferences" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/check the price range/i);
    expect(m.called("PATCH /customers/me/preferences")).toHaveLength(0);
  });

  it("resets only inferred interests, or everything, after confirming", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const m = mockApi(signedIn({
      "GET /customers/me/preferences": prefs, "GET /products/categories": cats,
      "DELETE /customers/me/preferences": prefs,
    }));
    renderApp("/preferences");
    const u = userEvent.setup();
    await u.click(await screen.findByRole("button", { name: "Reset inferred interests" }));
    await waitFor(() => expect(m.called("DELETE /customers/me/preferences")).toHaveLength(1));
    expect(m.called("DELETE /customers/me/preferences")[0].search.get("include_explicit")).toBe("false");
    await u.click(screen.getByRole("button", { name: "Reset everything" }));
    await waitFor(() => expect(m.called("DELETE /customers/me/preferences")).toHaveLength(2));
    expect(m.called("DELETE /customers/me/preferences")[1].search.get("include_explicit")).toBe("true");
  });

  it("does nothing if the reset is not confirmed", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const m = mockApi(signedIn({ "GET /customers/me/preferences": prefs, "GET /products/categories": cats }));
    renderApp("/preferences");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Reset everything" }));
    expect(m.called("DELETE /customers/me/preferences")).toHaveLength(0);
  });
});

describe("saved items and history", () => {
  it("lists and removes saved items", async () => {
    const m = mockApi(signedIn({
      "GET /customers/me/saved": [{ product: product("s1"), saved_at: "2026-01-01T00:00:00Z" }],
      "DELETE /customers/me/saved/s1": null,
    }));
    renderApp("/saved");
    const u = userEvent.setup();
    await u.click(await screen.findByRole("button", { name: /Remove/ }));
    await waitFor(() => expect(screen.getByText("Nothing saved yet")).toBeInTheDocument());
    expect(m.called("DELETE /customers/me/saved/s1")).toHaveLength(1);
  });

  it("lists history, removes one item, and clears everything after confirming", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const m = mockApi(signedIn({
      "GET /customers/me/history": [
        { product: product("h1"), last_seen: "2026-01-01T00:00:00Z" },
        { product: product("h2"), last_seen: "2026-01-02T00:00:00Z" },
      ],
      "DELETE /customers/me/history/h1": null,
      "DELETE /customers/me/history": null,
    }));
    renderApp("/history");
    const u = userEvent.setup();
    expect(await screen.findByRole("link", { name: "Item h1" })).toBeInTheDocument();
    await u.click(screen.getAllByRole("button", { name: /Remove/ })[0]);
    await waitFor(() => expect(screen.queryByRole("link", { name: "Item h1" })).not.toBeInTheDocument());
    await u.click(screen.getByRole("button", { name: "Clear all history" }));
    expect(await screen.findByText("No history recorded")).toBeInTheDocument();
    expect(m.called("DELETE /customers/me/history")).toHaveLength(1);
  });
});

describe("settings", () => {
  it("turns personalisation off for the account and the browser", async () => {
    localStorage.setItem("pf_consent", "granted");
    const m = mockApi(signedIn({ "PATCH /customers/me/settings": user({ tracking_consent: false }) }));
    renderApp("/settings");
    const u = userEvent.setup();
    expect(await screen.findByText(/Personalisation is/)).toHaveTextContent("on");
    await u.click(screen.getByRole("button", { name: "Turn personalisation off" }));
    await waitFor(() => expect(screen.getByText(/Personalisation is/)).toHaveTextContent("off"));
    expect(m.called("PATCH /customers/me/settings")[0].body).toEqual({ tracking_consent: false });
    expect(localStorage.getItem("pf_consent")).toBe("denied");
    expect(localStorage.getItem("pf_session_id")).toBeNull();
  });

  it("keeps account deletion locked until a password is typed, then deletes and signs out", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const m = mockApi(signedIn({ "POST /customers/me/delete": null, "POST /auth/logout": null }));
    renderApp("/settings");
    const u = userEvent.setup();
    const button = await screen.findByRole("button", { name: "Delete my account" });
    expect(button).toBeDisabled();
    await u.type(screen.getByLabelText("Confirm with your password"), "correct-horse-battery");
    await u.click(button);
    await waitFor(() => expect(m.called("POST /customers/me/delete")).toHaveLength(1));
    expect(m.called("POST /customers/me/delete")[0].body).toEqual({ password: "correct-horse-battery" });
    expect(await screen.findByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows the server's reason if the password is wrong, and does not sign out", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockApi(signedIn({ "POST /customers/me/delete": apiError(403, "forbidden", "Incorrect password.") }));
    renderApp("/settings");
    const u = userEvent.setup();
    await u.type(await screen.findByLabelText("Confirm with your password"), "nope-nope-nope");
    await u.click(screen.getByRole("button", { name: "Delete my account" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect password.");
    expect(screen.getByText("ann@shop.dev", { selector: "summary" })).toBeInTheDocument();
  });
});
