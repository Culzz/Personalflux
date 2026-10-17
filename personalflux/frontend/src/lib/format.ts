const nf = new Intl.NumberFormat("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Retailrocket rows carry no currency, so those prices show as plain numbers. */
export function formatPrice(price: string | null | undefined, currency?: string | null): string {
  if (price === null || price === undefined || price === "") return "Price not listed";
  const n = Number(price);
  if (!Number.isFinite(n)) return "Price not listed";
  const amount = nf.format(n);
  if (currency === "USD") return `$${amount}`;
  return currency ? `${amount} ${currency}` : amount;
}

/** Stable colour per category for placeholder tiles (the dataset has no images). */
export function categoryHue(category: string | null): number {
  let h = 0;
  for (const ch of category ?? "none") h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}

/** A random key that satisfies the API's id rules (8-64 chars: letters, digits, - and _). */
export function newKey(prefix = "k"): string {
  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2) + Date.now().toString(36);
  return `${prefix}-${id}`.slice(0, 64);
}
