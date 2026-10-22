import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderApp, signedIn, user, mockApi } from "./utils";

const analyst = user({ role: "analyst" });

function mlRoutes() {
  return signedIn(
    {
      "GET /ml/experiments": [
        { id: "e1", name: "baseline vs hybrid", configuration: {}, created_at: "2026-01-01", kind: "offline_evaluation",
          runs: [{ model_version: "v1", metrics: { recall_at_10: 0.09 } }] },
      ],
      "GET /ml/models": { serving: "v1", versions: [{ version: "v1", status: "serving", details: null, created_at: "2026-01-01", promoted_at: null }] },
      "GET /ml/health": { status: "ready", model_loaded: true, model_version: "v1", fallback_mode: null },
    },
    analyst,
  );
}

describe("ml console", () => {
  it("shows experiments and model versions to an analyst", async () => {
    mockApi(mlRoutes());
    renderApp("/ml");
    expect(await screen.findByText("baseline vs hybrid")).toBeInTheDocument();
    expect(screen.getByText("0.0900")).toBeInTheDocument();
    expect(screen.getAllByText("v1").length).toBeGreaterThan(0);
  });

  it("locks customers out", async () => {
    mockApi(signedIn());
    renderApp("/ml");
    expect(await screen.findByText(/analyst, ML engineer or admin/i)).toBeInTheDocument();
  });
});
