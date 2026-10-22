import { useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { productsApi, recsApi } from "../../lib/endpoints";
import { useToast } from "../toast/ToastContext";

const KEY = "pf_onboarded";

/** Has this browser already been through first-run onboarding (or skipped it)? */
export function hasOnboarded(): boolean {
  try { return localStorage.getItem(KEY) === "1"; } catch { return true; }
}

function markOnboarded(): void {
  try { localStorage.setItem(KEY, "1"); } catch { /* private mode: just ask again next time */ }
}

interface Props {
  /** saved=true when the choices were stored, so the caller can refresh the feed. */
  onDone: (saved: boolean) => void;
}

/**
 * A short, skippable first-run setup. It writes stated preferences for whoever
 * is asking, session or account, so the feed can reflect the choices before
 * anyone registers.
 */
export function OnboardingDialog({ onDone }: Props) {
  const categories = useAsync((s) => productsApi.categories(s), []);
  const brands = useAsync((s) => productsApi.brands(s), []);
  const { notify } = useToast();
  const [liked, setLiked] = useState<Set<string>>(new Set());
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [min, setMin] = useState("");
  const [max, setMax] = useState("");
  const [busy, setBusy] = useState(false);

  const flip = (setter: typeof setLiked) => (value: string) =>
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });

  async function save() {
    setBusy(true);
    try {
      await recsApi.updateStatedPreferences({
        liked_categories: [...liked],
        liked_brands: [...picked],
        price_range: min || max ? { min: min || null, max: max || null } : null,
      });
      markOnboarded();
      notify("Saved. Your recommendations will reflect these choices.");
      onDone(true);
    } catch {
      notify("Could not save your choices. You can try again from the home page.", { tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  function skip() {
    markOnboarded();
    onDone(false);
  }

  const chip = (on: boolean) =>
    `rounded-full border px-3 py-1 text-sm ${
      on ? "border-violet-400 bg-violet-600/20 text-violet-100" : "border-slate-700 hover:border-slate-500"
    }`;

  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-slate-950/70 p-4 sm:items-center">
      <div role="dialog" aria-modal="true" aria-labelledby="onboarding-title"
           className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-xl">
        <h2 id="onboarding-title" className="text-lg font-bold">Tell us what you like</h2>
        <p className="mt-1 text-sm text-slate-400">
          Pick as much or as little as you want, or skip. These are stated preferences, kept apart
          from what we infer from browsing.
        </p>

        <fieldset className="mt-4">
          <legend className="text-sm font-medium">Categories</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {(categories.data ?? []).slice(0, 12).map((c) => (
              <button key={c.category} type="button" aria-pressed={liked.has(c.category)}
                      onClick={() => flip(setLiked)(c.category)} className={chip(liked.has(c.category))}>
                {c.category}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="mt-4">
          <legend className="text-sm font-medium">Price range</legend>
          <div className="mt-2 flex items-center gap-2">
            <input inputMode="decimal" value={min} onChange={(e) => setMin(e.target.value)}
                   aria-label="Minimum price" placeholder="Min"
                   className="w-24 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm" />
            <span className="text-slate-500">to</span>
            <input inputMode="decimal" value={max} onChange={(e) => setMax(e.target.value)}
                   aria-label="Maximum price" placeholder="Max"
                   className="w-24 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm" />
          </div>
        </fieldset>

        {brands.data && brands.data.length > 0 && (
          <fieldset className="mt-4">
            <legend className="text-sm font-medium">Brands</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {brands.data.slice(0, 12).map((b) => (
                <button key={b.brand} type="button" aria-pressed={picked.has(b.brand)}
                        onClick={() => flip(setPicked)(b.brand)} className={chip(picked.has(b.brand))}>
                  {b.brand}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        <div className="mt-5 flex items-center justify-end gap-2">
          <button type="button" onClick={skip}
                  className="rounded-md px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800">
            Not now
          </button>
          <button type="button" onClick={save} disabled={busy}
                  className="rounded-md bg-violet-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-60">
            {busy ? "Saving…" : "Save and personalise"}
          </button>
        </div>
      </div>
    </div>
  );
}
