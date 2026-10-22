import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { apiError, mockApi, product, renderApp, signedIn, type Call } from "./utils";

const p1 = product("p1");
const p2 = product("p2");
const savedRow = (p: typeof p1) => ({ product: p, saved_at: "2026-01-01T00:00:00Z" });
const list = (extra: Record<string, unknown> = {}) => ({
  id: "c1", name: "Kitchen ideas", item_count: 0,
  created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", ...extra,
});

describe("curated lists", () => {
  it("creates a list from the saved page", async () => {
    let held: unknown[] = [];
    const m = mockApi(signedIn({
      "GET /customers/me/saved": [savedRow(p1)],
      "GET /customers/me/collections": () => held,
      "POST /customers/me/collections": (c: Call) => {
        held = [list({ name: c.body.name })];
        return held[0];
      },
    }));
    renderApp("/saved");
    const u = userEvent.setup();

    await u.type(await screen.findByLabelText("New list name"), "Kitchen ideas");
    await u.click(screen.getByRole("button", { name: "Create list" }));

    await waitFor(() => expect(m.called("POST /customers/me/collections")).toHaveLength(1));
    expect(m.called("POST /customers/me/collections")[0].body).toEqual({ name: "Kitchen ideas" });
    expect(await screen.findByRole("link", { name: /Kitchen ideas/ })).toHaveTextContent("0");
  });

  it("will not offer to create a list without a name", async () => {
    mockApi(signedIn());
    renderApp("/saved");
    expect(await screen.findByRole("button", { name: "Create list" })).toBeDisabled();
  });

  it("shows the server's reason when a name is refused", async () => {
    mockApi(signedIn({
      "POST /customers/me/collections":
        apiError(409, "conflict", "You already have a list with that name."),
    }));
    renderApp("/saved");
    const u = userEvent.setup();

    await u.type(await screen.findByLabelText("New list name"), "Gifts");
    await u.click(screen.getByRole("button", { name: "Create list" }));

    expect(await screen.findByText("You already have a list with that name.")).toBeInTheDocument();
  });

  it("adds a saved product to a list and moves that list's count", async () => {
    const m = mockApi(signedIn({
      "GET /customers/me/saved": [savedRow(p1)],
      "GET /customers/me/collections": [list()],
      "PUT /customers/me/collections/c1/items/p1": null,
    }));
    renderApp("/saved");
    const u = userEvent.setup();

    await u.selectOptions(await screen.findByLabelText("Add Item p1 to a list"), "c1");

    await waitFor(() => expect(m.called("PUT /customers/me/collections/c1/items/p1")).toHaveLength(1));
    expect(await screen.findByRole("link", { name: /Kitchen ideas/ })).toHaveTextContent("1");
    expect(await screen.findByText("Added Item p1 to Kitchen ideas.")).toBeInTheDocument();
  });

  it("puts the count back when the server refuses an addition", async () => {
    mockApi(signedIn({
      "GET /customers/me/saved": [savedRow(p1)],
      "GET /customers/me/collections": [list()],
      "PUT /customers/me/collections/c1/items/p1":
        apiError(409, "conflict", "A list holds up to 100 products."),
    }));
    renderApp("/saved");
    const u = userEvent.setup();

    await u.selectOptions(await screen.findByLabelText("Add Item p1 to a list"), "c1");

    expect(await screen.findByText("A list holds up to 100 products.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Kitchen ideas/ })).toHaveTextContent("0");
  });

  it("shows a list and takes an item back out of it", async () => {
    const m = mockApi(signedIn({
      "GET /customers/me/collections/c1": list({ items: [p1, p2] }),
      "DELETE /customers/me/collections/c1/items/p1": null,
    }));
    renderApp("/lists/c1");
    const u = userEvent.setup();

    expect(await screen.findByRole("heading", { name: "Kitchen ideas" })).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Remove Item p1 from this list" }));

    await waitFor(() =>
      expect(m.called("DELETE /customers/me/collections/c1/items/p1")).toHaveLength(1));
    expect(screen.queryByRole("link", { name: "Item p1" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Item p2" })).toBeInTheDocument();
  });

  it("says an empty list is empty", async () => {
    mockApi(signedIn({ "GET /customers/me/collections/c1": list({ items: [] }) }));
    renderApp("/lists/c1");
    expect(await screen.findByText("This list is empty")).toBeInTheDocument();
  });

  it("renames a list", async () => {
    mockApi(signedIn({
      "GET /customers/me/collections/c1": list({ items: [] }),
      "PATCH /customers/me/collections/c1": (c: Call) => list({ name: c.body.name }),
    }));
    renderApp("/lists/c1");
    const u = userEvent.setup();

    await u.click(await screen.findByRole("button", { name: "Rename" }));
    const input = screen.getByLabelText("List name");
    await u.clear(input);
    await u.type(input, "Winter picks");
    await u.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("heading", { name: "Winter picks" })).toBeInTheDocument();
  });

  it("deletes a list and returns to the saved items", async () => {
    const m = mockApi(signedIn({
      "GET /customers/me/collections/c1": list({ items: [] }),
      "DELETE /customers/me/collections/c1": null,
    }));
    renderApp("/lists/c1");
    const u = userEvent.setup();

    await u.click(await screen.findByRole("button", { name: "Delete list" }));

    await waitFor(() => expect(m.called("DELETE /customers/me/collections/c1")).toHaveLength(1));
    expect(await screen.findByRole("heading", { name: "Saved items" })).toBeInTheDocument();
  });
});
