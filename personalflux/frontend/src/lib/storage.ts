// Small, failure-tolerant wrappers around localStorage (it can throw in private mode).
import { newKey } from "./format";

const CONSENT_KEY = "pf_consent";
const SESSION_KEY = "pf_session_id";
const HAS_SESSION_KEY = "pf_has_session";
const CART_KEY = "pf_cart";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
}
function remove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

export type ConsentValue = "granted" | "denied";

export function readConsent(): ConsentValue | null {
  const v = read(CONSENT_KEY);
  return v === "granted" || v === "denied" ? v : null;
}
export function writeConsent(v: ConsentValue): void {
  write(CONSENT_KEY, v);
}

/** The anonymous session id exists only while the visitor has allowed personalisation. */
export function getSessionId(): string | null {
  if (readConsent() !== "granted") return null;
  let id = read(SESSION_KEY);
  if (!id) {
    id = newKey("sess");
    write(SESSION_KEY, id);
  }
  return id;
}
export function clearSessionId(): void {
  remove(SESSION_KEY);
}

/** A hint only: "this browser had a login", so we know whether to try a silent refresh. */
export function hasSessionFlag(): boolean {
  return read(HAS_SESSION_KEY) === "1";
}
export function setSessionFlag(on: boolean): void {
  if (on) write(HAS_SESSION_KEY, "1");
  else remove(HAS_SESSION_KEY);
}

export function readCartRaw(): string | null {
  return read(CART_KEY);
}
export function writeCartRaw(v: string): void {
  write(CART_KEY, v);
}
