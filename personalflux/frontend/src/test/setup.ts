import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { setAccessToken, setAuthLostHandler } from "../lib/api";

afterEach(() => {
  cleanup();
  localStorage.clear();
  setAccessToken(null);
  setAuthLostHandler(null);
  vi.restoreAllMocks();
});
