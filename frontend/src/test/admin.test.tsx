import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockApi, product, renderApp, signedIn, user } from "./utils";

const admin = user({ role: "admin" });

function adminRoutes(over = {}) {
  return signedIn(
    {
      "GET /products": { items: [product("p1")], total: 1, page: 1, page_size: 12 },
      "GET /admin/users": [{ id: "u2", email: "staff@shop.dev", role: "analyst", is_active: true, created_at: "2026-01-01" }],
      "GET /admin/audit-logs": [],
      ...over,
    },
    admin,
  );
}

describe("admin", () => {
  it("lists products and users for an admin", async () => {
    mockApi(adminRoutes());
    renderApp("/admin");
    expect(await screen.findByText("Item p1")).toBeInTheDocument();
    expect(screen.getByText(/staff@shop.dev/)).toBeInTheDocument();
  });

  it("creates a product from the form", async () => {
    const m = mockApi(adminRoutes({ "POST /products": product("p9", { title: "New thing" }) }));
    renderApp("/admin");
    const u = userEvent.setup();
    await u.type(await screen.findByLabelText("Title"), "New thing");
    await u.click(screen.getByRole("button", { name: "Create product" }));
    await screen.findByText("Product created and live in the catalog.");
    expect(m.called("POST /products").length).toBe(1);
  });

  it("locks customers out", async () => {
    mockApi(signedIn());
    renderApp("/admin");
    expect(await screen.findByText("Admins only")).toBeInTheDocument();
  });
});
