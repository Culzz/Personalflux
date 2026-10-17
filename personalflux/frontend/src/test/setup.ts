import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { setAccessToken, setAuthLostHandler } from "../lib/api";

beforeEach(() => {
  // First-run onboarding is opt-out per test, so it does not sit on every page render.
  localStorage.setItem("pf_onboarded", "1");
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  setAccessToken(null);
  setAuthLostHandler(null);
  vi.restoreAllMocks();
});
