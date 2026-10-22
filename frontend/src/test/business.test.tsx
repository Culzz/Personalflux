import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { apiError, baseRoutes, mockApi, renderApp, signedIn, user } from "./utils";

const overview = {
  kind: "live_activity", window_days: 30, customers_total: 9,
  events_total: 120, events_by_type: { view: 100, click: 20 },
  active_customers: 5, anonymous_sessions: 3, impressions: 40,
};

const recs = {
  impressions: 40, recommendation_requests_with_impressions: 10,
  distinct_products_shown: 6, impressions_per_request: 4,
  catalogue_coverage_ratio: 0.5, impressions_by_model_version: { v1: 30, None: 10 },
  fallback_impressions: 10, fallback_rate: 0.25,
  engagement_from_recommendations: { click: 3 },
  clicks_from_recommendations: 3, attributed_clicks: 2,
  click_through_rate: 0.075,
  definitions: { impression: "a product that was displayed to a person" },
};

const analyst = user({ role: "analyst", email: "ops@shop.dev" });

const asAnalyst = (over = {}) =>
  signedIn(
    {
      "GET /analytics/overview": overview,
      "GET /analytics/categories": {
        categories: [{ category: "Category A", events: 9, views: 7, add_to_cart: 1, purchases: 1 }],
      },
      "GET /analytics/segments": { segments: [{ segment: "returning", customers: 4 }] },
      "GET /analytics/recommendations": recs,
      "GET /ml/health": { status: "ok", model_loaded: true, model_version: "v1" },
      ...over,
    },
    analyst,
  );

describe("business overview", () => {
  it("reads the rates as percentages and names the model in use", async () => {
    mockApi(asAnalyst());
    renderApp("/business");

    expect(await screen.findByRole("heading", { name: "Business overview" })).toBeInTheDocument();
    expect(await screen.findByText("7.5%")).toBeInTheDocument();   // click-through rate 0.075
    expect(screen.getByText("25.0%")).toBeInTheDocument();         // fallback rate 0.25
    expect(screen.getByText("50.0%")).toBeInTheDocument();         // catalogue coverage 0.5
    expect(screen.getByText("4.00")).toBeInTheDocument();          // impressions per request
    expect(screen.getByText("v1")).toBeInTheDocument();
    expect(screen.getByText(/fallback 10/)).toBeInTheDocument();
  });

  it("says a panel failed instead of showing it as empty, and can retry", async () => {
    const m = mockApi(asAnalyst({
      "GET /analytics/categories": apiError(500, "internal_error", "boom"),
    }));
    renderApp("/business");
    const u = userEvent.setup();

    const retry = await screen.findByRole("button", { name: "Try again" });
    // The failure must not read as "there is no data".
    expect(screen.queryByText("No category activity in this window yet.")).not.toBeInTheDocument();

    await u.click(retry);
    await waitFor(() => expect(m.called("GET /analytics/categories")).toHaveLength(2));
  });

  it("distinguishes an empty window from a failed request", async () => {
    mockApi(asAnalyst({ "GET /analytics/categories": { categories: [] } }));
    renderApp("/business");

    expect(await screen.findByText("No category activity in this window yet.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });

  it("tells a customer that the metrics need an analyst role", async () => {
    mockApi(signedIn());
    renderApp("/business");

    expect(await screen.findByText("Analyst role needed")).toBeInTheDocument();
  });

  it("asks a signed-out visitor to sign in", async () => {
    mockApi(baseRoutes());
    renderApp("/business");

    expect(await screen.findByText("Sign in to view business metrics")).toBeInTheDocument();
  });
});
