import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { baseRoutes, feed, mockApi, renderApp, type Call } from "./utils";

const saved = (c: Call) => ({
  liked_categories: c.body.liked_categories ?? [],
  blocked_categories: [],
  liked_brands: c.body.liked_brands ?? [],
  price_range: null,
});

function routes(over = {}) {
  return baseRoutes({
    "GET /recommendations/home": feed([]),
    "GET /products/categories": [
      { category: "Beauty", products: 12 },
      { category: "Kitchen", products: 8 },
    ],
    "GET /products/brands": [{ brand: "Nova", products: 5 }],
    "PATCH /recommendations/preferences": saved,
    ...over,
  });
}

const dialog = () => screen.findByRole("dialog", { name: /tell us what you like/i });

describe("first-visit onboarding", () => {
  it("saves the chosen categories and brands, then closes", async () => {
    localStorage.removeItem("pf_onboarded");
    const m = mockApi(routes());
    renderApp("/");

    await dialog();
    const u = userEvent.setup();
    await u.click(screen.getByRole("button", { name: "Beauty" }));
    await u.click(screen.getByRole("button", { name: "Nova" }));
    await u.type(screen.getByLabelText("Minimum price"), "20");
    await u.click(screen.getByRole("button", { name: /save and personalise/i }));

    await waitFor(() => expect(m.called("PATCH /recommendations/preferences")).toHaveLength(1));
    const body = m.called("PATCH /recommendations/preferences")[0].body;
    expect(body.liked_categories).toEqual(["Beauty"]);
    expect(body.liked_brands).toEqual(["Nova"]);
    expect(body.price_range).toEqual({ min: "20", max: null });

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(localStorage.getItem("pf_onboarded")).toBe("1");
  });

  it("can be skipped without saving anything", async () => {
    localStorage.removeItem("pf_onboarded");
    const m = mockApi(routes());
    renderApp("/");

    await dialog();
    await userEvent.setup().click(screen.getByRole("button", { name: "Not now" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(m.called("PATCH /recommendations/preferences")).toHaveLength(0);
  });

  it("does not appear once this browser has been through it", async () => {
    mockApi(routes());
    renderApp("/");
    expect(await screen.findByText("Recommended for you")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
