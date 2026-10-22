import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { baseRoutes, feed, mockApi, product, rec, renderApp } from "./utils";

const p1 = product("p1");
const p2 = product("p2", { category: "Category B" });

const personal = feed([
  rec(p1, 1, 'Similar to "Item p9", which you looked at recently.'),
  rec(p2, 2, "Similar to items you looked at recently."),
]);

function routes(over = {}) {
  return baseRoutes({
    "GET /recommendations/home": personal,
    "GET /products/p1": p1,
    "GET /recommendations/similar/p1": feed([], { request_id: "req-sim" }),
    "GET /products/p1/related": [],
    ...over,
  });
}

describe("home feed", () => {
  it("shows each recommendation with the server's explanation", async () => {
    mockApi(routes());
    renderApp("/");
    expect(await screen.findByText('Similar to "Item p9", which you looked at recently.')).toBeInTheDocument();
    expect(screen.getByText("Similar to items you looked at recently.")).toBeInTheDocument();
    expect(screen.getByTestId("strategy-note")).toHaveTextContent("Based on what you have looked at in this session.");
  });

  it("reports what was shown, once, when the visitor allowed personalisation", async () => {
    localStorage.setItem("pf_consent", "granted");
    const m = mockApi(routes());
    renderApp("/");
    await screen.findByText("Similar to items you looked at recently.");
    await waitFor(() => expect(m.called("POST /recommendations/impressions").length).toBeGreaterThan(0));
    const forFeed = m.called("POST /recommendations/impressions").filter((c) => c.body.request_id === "req-feed");
    expect(forFeed).toHaveLength(1);
    expect(forFeed[0].body.items).toEqual([
      { product_id: "p1", position: 1 }, { product_id: "p2", position: 2 },
    ]);
    expect(forFeed[0].body.model_version).toBe("v1");
  });

  it("sends NOTHING about the visitor when personalisation is declined", async () => {
    localStorage.setItem("pf_consent", "denied");
    const m = mockApi(routes());
    renderApp("/");
    await screen.findByText("Similar to items you looked at recently.");
    expect(m.called("POST /recommendations/impressions")).toHaveLength(0);
    expect(m.called("POST /events")).toHaveLength(0);
    expect(m.calls.every((c) => c.headers["X-Session-Id"] === undefined)).toBe(true);
  });

  it("asks first when no choice has been made, and sends nothing meanwhile", async () => {
    const m = mockApi(routes());
    renderApp("/");
    expect(await screen.findByRole("region", { name: "Privacy choices" })).toBeInTheDocument();
    await screen.findByText("Similar to items you looked at recently.");
    expect(m.called("POST /recommendations/impressions")).toHaveLength(0);
  });

  it("the banner stores the choice and goes away", async () => {
    mockApi(routes());
    renderApp("/");
    const u = userEvent.setup();
    await u.click(await screen.findByRole("button", { name: "Allow" }));
    expect(localStorage.getItem("pf_consent")).toBe("granted");
    expect(localStorage.getItem("pf_session_id")).toMatch(/^sess-/);
    expect(screen.queryByRole("region", { name: "Privacy choices" })).not.toBeInTheDocument();
  });

  it("declining forgets any session id", async () => {
    localStorage.setItem("pf_session_id", "sess-leftover-1234");
    mockApi(routes());
    renderApp("/");
    await userEvent.setup().click(await screen.findByRole("button", { name: "No thanks" }));
    expect(localStorage.getItem("pf_consent")).toBe("denied");
    expect(localStorage.getItem("pf_session_id")).toBeNull();
  });

  it("explains popularity picks honestly, and nudges toward consent only when it is off", async () => {
    const pop = feed([rec(p1, 1, "Popular with other shoppers.", "popularity_fallback")],
      { strategy: "popularity", fallback_used: true });
    localStorage.setItem("pf_consent", "denied");
    mockApi(routes({ "GET /recommendations/home": pop }));
    renderApp("/");
    expect(await screen.findByTestId("strategy-note")).toHaveTextContent(/allow personalisation in settings/i);
  });

  it("says the list will adapt when tracking is on", async () => {
    const pop = feed([rec(p1, 1, "Popular with other shoppers.", "popularity_fallback")],
      { strategy: "popularity", fallback_used: true });
    localStorage.setItem("pf_consent", "granted");
    mockApi(routes({ "GET /recommendations/home": pop }));
    renderApp("/");
    expect(await screen.findByTestId("strategy-note")).toHaveTextContent(/this list will adapt/i);
  });

  it("'Not interested' hides the card and reports it", async () => {
    localStorage.setItem("pf_consent", "granted");
    const m = mockApi(routes({ "POST /recommendations/feedback": { stored: true } }));
    renderApp("/");
    const u = userEvent.setup();
    const card = (await screen.findByText('Similar to "Item p9", which you looked at recently.')).closest("article")!;
    await u.click(within(card).getByRole("button", { name: /not interested/i }));
    await waitFor(() => expect(screen.queryByText('Similar to "Item p9", which you looked at recently.')).not.toBeInTheDocument());
    expect(m.called("POST /recommendations/feedback")[0].body).toEqual({
      product_id: "p1", feedback: "dismiss", request_id: "req-feed",
    });
  });

  it("'Not interested' still hides the card when tracking is off, without reporting it", async () => {
    localStorage.setItem("pf_consent", "denied");
    const m = mockApi(routes());
    renderApp("/");
    const u = userEvent.setup();
    const card = (await screen.findByText('Similar to "Item p9", which you looked at recently.')).closest("article")!;
    await u.click(within(card).getByRole("button", { name: /not interested/i }));
    await waitFor(() => expect(screen.queryByText('Similar to "Item p9", which you looked at recently.')).not.toBeInTheDocument());
    expect(m.called("POST /recommendations/feedback")).toHaveLength(0);
  });

  it("opening a recommendation records a click linked to that request, then a view", async () => {
    localStorage.setItem("pf_consent", "granted");
    const m = mockApi(routes());
    renderApp("/");
    const u = userEvent.setup();
    await u.click(await screen.findByRole("link", { name: "Item p1" }));
    await screen.findByRole("heading", { name: "Item p1" });
    await waitFor(() => expect(m.called("POST /events").length).toBeGreaterThanOrEqual(2));
    const events = m.called("POST /events").map((c) => c.body);
    expect(events).toContainEqual({ event_type: "click", product_id: "p1", context: { source: "recommendation", request_id: "req-feed", model_version: "v1", position: 1 } });
    const view = events.find((e) => e.event_type === "view");
    expect(view).toMatchObject({ product_id: "p1" });
    expect(view.idempotency_key).toMatch(/^view-/);
  });

  it("shows a friendly error with a retry when the feed fails", async () => {
    mockApi(routes({ "GET /recommendations/home": new Response("{}", { status: 500 }) }));
    renderApp("/");
    expect(await screen.findByRole("alert")).toHaveTextContent(/request failed|something went wrong/i);
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("shows an empty state when there is nothing to recommend", async () => {
    mockApi(routes({ "GET /recommendations/home": feed([]) }));
    renderApp("/");
    expect(await screen.findByText("No recommendations right now")).toBeInTheDocument();
  });
});
