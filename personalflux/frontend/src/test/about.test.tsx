import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderApp } from "./utils";

describe("about page", () => {
  it("explains the product and links into the catalog", async () => {
    renderApp("/about");
    expect(await screen.findByRole("heading", { name: "About PersonaFlux" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Browse the catalog" })).toHaveAttribute("href", "/discover");
  });
});
