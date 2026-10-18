import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { baseRoutes, feed, mockApi, product, rec, renderApp } from "./utils";

const p1 = product("p1", { price: "19.99" });
const p2 = product("p2");
const p3 = product("p3");

function productRoutes(over = {}) {
  return baseRoutes({
    "GET /products/p1": p1,
    "GET /recommendations/similar/p1": feed([rec(p2, 1, "Similar to Item p1.")]),
    "GET /products/p1/related": [p3],
    ...over,
  });
}

describe("compare", () => {
  it("queues products from the page and offers a shareable comparison link", async () => {
    mockApi(productRoutes());
    renderApp("/products/p1");
    await screen.findByRole("heading", { name: "Item p1" });
    const u = userEvent.setup();

    await u.click(screen.getByRole("button", { name: /^Compare Item p1$/ }));
    // One item alone is not a comparison, so the link waits for a second.
    expect(screen.getByText("Pick one more")).toBeInTheDocument();

    await u.click(await screen.findByRole("button", { name: /^Compare Item p3$/ }));
    const link = await screen.findByRole("link", { name: /Compare \(2\)/ });
    expect(link).toHaveAttribute("href", "/compare?ids=p1,p3");

    // Clicking again takes the product back out.
    await u.click(screen.getByRole("button", { name: /^Comparing Item p1$/ }));
    expect(await screen.findByText("Pick one more")).toBeInTheDocument();
  });

  it("lays the chosen products out side by side", async () => {
    const m = mockApi(baseRoutes({
      "GET /products/compare": [
        product("p1", { price: "19.99", brand: "Nova", stock: 3, currency: "USD" }),
        product("p2", { category: "Kitchen", description: "A sturdy mug." }),
      ],
    }));
    renderApp("/compare?ids=p1,p2");

    expect(await screen.findByRole("heading", { name: "Compare" })).toBeInTheDocument();
    // The order the visitor chose is preserved in the request.
    expect(m.called("GET /products/compare")[0].search.get("ids")).toBe("p1,p2");

    expect(screen.getByRole("rowheader", { name: "Price" })).toBeInTheDocument();
    expect(screen.getByText("$19.99")).toBeInTheDocument();
    expect(screen.getByText("Nova")).toBeInTheDocument();
    expect(screen.getByText("Only 3 left")).toBeInTheDocument();
    expect(screen.getByText("A sturdy mug.")).toBeInTheDocument();
  });

  it("explains that one product is not yet a comparison", async () => {
    mockApi(baseRoutes({ "GET /products/compare": [p1] }));
    renderApp("/compare?ids=p1");
    expect(await screen.findByText("Pick one more to compare")).toBeInTheDocument();
  });

  it("says so when nothing has been chosen", async () => {
    mockApi(baseRoutes());
    renderApp("/compare");
    expect(await screen.findByText("Nothing to compare yet")).toBeInTheDocument();
  });
});
