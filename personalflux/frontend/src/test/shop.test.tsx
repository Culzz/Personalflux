import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { apiError, baseRoutes, feed, mockApi, product, rec, renderApp, signedIn } from "./utils";

const p1 = product("p1", { price: "19.99" });
const p2 = product("p2");

function productRoutes(over = {}) {
  return baseRoutes({
    "GET /products/p1": p1,
    "GET /recommendations/similar/p1": feed([rec(p2, 1, 'Often looked at together with "Item p1".')], { request_id: "req-sim", strategy: "item_similarity" }),
    "GET /products/p1/related": [product("p3")],
    ...over,
  });
}

describe("product page", () => {
  it("shows the product, similar items with explanations, and related products", async () => {
    mockApi(productRoutes());
    renderApp("/products/p1");
    expect(await screen.findByRole("heading", { name: "Item p1" })).toBeInTheDocument();
    expect(screen.getByText("19.99")).toBeInTheDocument();
    expect(await screen.findByText('Often looked at together with "Item p1".')).toBeInTheDocument();
    expect(await screen.findByText("More in Category A")).toBeInTheDocument();
  });

  it("shows the dataset fallback note only when the item has no photo or description", async () => {
    mockApi(productRoutes({
      "GET /products/p1": product("p1", { description: "Hand-thrown stoneware mug.", image_url: "https://cdn.example/mug.jpg" }),
    }));
    renderApp("/products/p1");
    await screen.findByRole("heading", { name: "Item p1" });
    expect(screen.getByText(/In stock/)).toBeInTheDocument();
    expect(screen.queryByText(/ships without photos or descriptions/)).not.toBeInTheDocument();
  });

  it("shows brand, stock and a source link when the catalog provides them", async () => {
    mockApi(productRoutes({
      "GET /products/p1": product("p1", {
        brand: "Acme", stock: 3, currency: "USD", price: "12.50",
        external_url: "https://dummyjson.com/products/1",
      }),
    }));
    renderApp("/products/p1");
    await screen.findByRole("heading", { name: "Item p1" });
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByText(/Only 3 left/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View at source/ }))
      .toHaveAttribute("href", "https://dummyjson.com/products/1");
  });

  it("asks anonymous visitors to sign in before tuning recommendations", async () => {
    mockApi(productRoutes());
    renderApp("/products/p1");
    await screen.findByRole("heading", { name: "Item p1" });
    const u = userEvent.setup();
    await u.click(screen.getByRole("button", { name: "More like this" }));
    expect(await screen.findByText(/Sign in to tune your recommendations/)).toBeInTheDocument();
  });

  it("records a stated preference when a signed-in shopper asks for more like this", async () => {
    const empty = { long_term_categories: [], recent_categories: [], events_considered: 0, note: "" };
    const m = mockApi(signedIn({
      ...productRoutes(),
      "GET /customers/me/preferences": {
        explicit: { liked_categories: ["Beauty"] }, inferred: empty, profile_reset_at: null,
      },
      "PATCH /customers/me/preferences": (c) => ({
        explicit: c.body, inferred: empty, profile_reset_at: null,
      }),
    }));
    renderApp("/products/p1");
    await screen.findByRole("heading", { name: "Item p1" });
    const u = userEvent.setup();
    await u.click(screen.getByRole("button", { name: "More like this" }));

    await waitFor(() => expect(m.called("PATCH /customers/me/preferences")).toHaveLength(1));
    const body = m.called("PATCH /customers/me/preferences")[0].body;
    expect(body.liked_categories).toEqual(["Beauty", "Category A"]);  // appended, not replaced
    expect(body.blocked_categories).toEqual([]);
    expect(await screen.findByText(/more from Category A/)).toBeInTheDocument();
  });

  it("records one view with an idempotency key when tracking is on", async () => {
    localStorage.setItem("pf_consent", "granted");
    const m = mockApi(productRoutes());
    renderApp("/products/p1");
    await screen.findByRole("heading", { name: "Item p1" });
    await waitFor(() => expect(m.called("POST /events").length).toBeGreaterThan(0));
    const views = m.called("POST /events").filter((c) => c.body.event_type === "view");
    expect(new Set(views.map((v) => v.body.idempotency_key)).size).toBe(1);   // same key even if re-sent
    expect(views[0].body.product_id).toBe("p1");
  });

  it("records nothing without consent", async () => {
    localStorage.setItem("pf_consent", "denied");
    const m = mockApi(productRoutes());
    renderApp("/products/p1");
    await screen.findByRole("heading", { name: "Item p1" });
    expect(m.called("POST /events")).toHaveLength(0);
  });

  it("handles a missing product", async () => {
    mockApi(productRoutes({ "GET /products/p1": apiError(404, "not_found", "Product not found.") }));
    renderApp("/products/p1");
    expect(await screen.findByText("Product not found")).toBeInTheDocument();
  });

  it("Save asks anonymous visitors to sign in instead of failing", async () => {
    mockApi(productRoutes());
    renderApp("/products/p1");
    const u = userEvent.setup();
    const main = await screen.findByRole("heading", { name: "Item p1" });
    await u.click(within(main.parentElement!).getByRole("button", { name: /save/i }));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});

describe("demo cart", () => {
  it("add to cart records the signal, and a demo order records purchases and empties the cart", async () => {
    localStorage.setItem("pf_consent", "granted");
    const m = mockApi(productRoutes());
    renderApp("/products/p1");
    const u = userEvent.setup();
    await u.click(await screen.findByRole("button", { name: "Add to cart" }));
    expect(screen.getByRole("button", { name: "In cart" })).toBeDisabled();
    await waitFor(() => expect(m.called("POST /events").some((c) => c.body.event_type === "add_to_cart")).toBe(true));

    await u.click(screen.getAllByRole("link", { name: /Cart/ })[0]);
    expect(await screen.findByText(/no payment and no real order/i)).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Place demo order" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Nothing was charged");
    const purchase = m.called("POST /events").find((c) => c.body.event_type === "purchase");
    expect(purchase!.body).toEqual({ event_type: "purchase", product_id: "p1", context: { source: "demo_checkout" } });
    expect(screen.getByText("Your cart is empty")).toBeInTheDocument();
  });

  it("without consent the order works but nothing is recorded, and it says so", async () => {
    localStorage.setItem("pf_consent", "denied");
    const m = mockApi(productRoutes());
    renderApp("/products/p1");
    const u = userEvent.setup();
    await u.click(await screen.findByRole("button", { name: "Add to cart" }));
    await u.click(screen.getAllByRole("link", { name: /Cart/ })[0]);
    await u.click(await screen.findByRole("button", { name: "Place demo order" }));
    expect(await screen.findByRole("status")).toHaveTextContent("was not recorded");
    expect(m.called("POST /events")).toHaveLength(0);
  });

  it("keeps the cart across page loads", async () => {
    localStorage.setItem("pf_cart", JSON.stringify([{ id: "p1", title: "Item p1", category: null, price: "5.00" }]));
    mockApi(baseRoutes());
    renderApp("/cart");
    expect(await screen.findByRole("link", { name: "Item p1" })).toBeInTheDocument();
  });
});

describe("discover", () => {
  const page = (n: number, total: number) => ({
    items: Array.from({ length: n }, (_, i) => product(`d${i}`)), total, page: 1, page_size: 12,
  });
  const routes = (over = {}) => baseRoutes({
    "GET /products": page(3, 30),
    "GET /products/categories": [{ category: "Category A", products: 2 }],
    ...over,
  });

  it("lists products and paginates", async () => {
    const m = mockApi(routes());
    renderApp("/discover");
    expect(await screen.findByText("30 products found")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(m.called("GET /products").some((c) => c.search.get("page") === "2")).toBe(true));
  });

  it("sends the filters to the API", async () => {
    const m = mockApi(routes());
    renderApp("/discover");
    const u = userEvent.setup();
    await u.type(await screen.findByLabelText("Search"), "lamp");
    await u.selectOptions(screen.getByLabelText("Category"), "Category A");
    await u.type(screen.getByLabelText("Min price"), "5");
    await u.selectOptions(screen.getByLabelText("Sort by"), "price_asc");
    await u.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => {
      const all = m.called("GET /products");
      const last = all[all.length - 1];
      expect(Object.fromEntries(last.search)).toMatchObject({
        q: "lamp", category: "Category A", min_price: "5", sort: "price_asc", page: "1", page_size: "12",
      });
    });
  });

  it("records a search WITHOUT the words typed", async () => {
    localStorage.setItem("pf_consent", "granted");
    const m = mockApi(routes());
    renderApp("/discover");
    const u = userEvent.setup();
    await u.type(await screen.findByLabelText("Search"), "very private phrase");
    await u.selectOptions(screen.getByLabelText("Category"), "Category A");
    await u.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => expect(m.called("POST /events")).toHaveLength(1));
    const sent = m.called("POST /events")[0].body;
    expect(sent).toEqual({ event_type: "search", context: { category: "Category A" } });
    expect(JSON.stringify(sent)).not.toContain("private");
  });

  it("rejects an impossible price range without calling the API again", async () => {
    const m = mockApi(routes());
    renderApp("/discover");
    const u = userEvent.setup();
    await screen.findByText("30 products found");
    const before = m.called("GET /products").length;
    await u.type(screen.getByLabelText("Min price"), "50");
    await u.type(screen.getByLabelText("Max price"), "5");
    await u.click(screen.getByRole("button", { name: "Search" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/minimum price cannot be above/i);
    expect(m.called("GET /products")).toHaveLength(before);
  });

  it("shows an empty state", async () => {
    mockApi(routes({ "GET /products": { items: [], total: 0, page: 1, page_size: 12 } }));
    renderApp("/discover");
    expect(await screen.findByText("No products match those filters")).toBeInTheDocument();
  });
});
