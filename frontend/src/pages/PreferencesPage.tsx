import { useState } from "react";
import { ErrorState, PageLoading } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { ApiError } from "../lib/api";
import { customerApi, productsApi } from "../lib/endpoints";
import type { BrandCount, CategoryCount, CategoryShare, PreferencesResponse } from "../lib/types";

function Shares({ title, rows }: { title: string; rows: CategoryShare[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold">{title}</h3>
      {rows.length === 0 ? (
        <p className="mt-1 text-sm text-slate-400">Nothing yet.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {rows.map((r) => (
            <li key={r.category} className="text-sm">
              <div className="flex justify-between">
                <span>{r.category}</span>
                <span className="text-slate-400">{Math.round(r.share * 100)}%</span>
              </div>
              <div className="mt-1 h-1.5 rounded bg-slate-800" aria-hidden="true">
                <div className="h-1.5 rounded bg-violet-500" style={{ width: `${Math.round(r.share * 100)}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface EditorProps {
  initial: PreferencesResponse["explicit"];
  categories: CategoryCount[];
  brands: BrandCount[];
  onSaved: () => void;
}

/** Starts with the saved values already in place (no empty first render). */
function ExplicitEditor({ initial, categories, brands, onSaved }: EditorProps) {
  const [liked, setLiked] = useState<Set<string>>(() => new Set(initial.liked_categories ?? []));
  const [blocked, setBlocked] = useState<Set<string>>(() => new Set(initial.blocked_categories ?? []));
  const [likedBrands, setLikedBrands] = useState<Set<string>>(() => new Set(initial.liked_brands ?? []));
  const [min, setMin] = useState(initial.price_range?.min ?? "");
  const [max, setMax] = useState(initial.price_range?.max ?? "");
  const [error, setError] = useState<string | null>(null);

  function flip(setter: typeof setLiked, name: string) {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  function toggle(setA: typeof setLiked, setB: typeof setBlocked, name: string) {
    setA((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
    // A category cannot be both liked and hidden
    setB((prev) => {
      if (!prev.has(name)) return prev;
      const next = new Set(prev);
      next.delete(name);
      return next;
    });
  }

  async function save() {
    setError(null);
    const bad = (s: string) => s !== "" && !(Number(s) >= 0);
    if (bad(min) || bad(max) || (min !== "" && max !== "" && Number(min) > Number(max))) {
      return setError("Check the price range: numbers of 0 or more, with the minimum not above the maximum.");
    }
    try {
      await customerApi.updatePreferences({
        liked_categories: [...liked],
        blocked_categories: [...blocked],
        liked_brands: [...likedBrands],
        price_range: min || max ? { min: min || null, max: max || null } : null,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save preferences.");
    }
  }

  const groups = [
    ["Categories I like", liked, setLiked, setBlocked],
    ["Categories to hide", blocked, setBlocked, setLiked],
  ] as const;
  const box = "w-32 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm";

  return (
    <div className="space-y-4">
      <div className="grid gap-6 md:grid-cols-2">
        {groups.map(([label, set, setA, setB]) => (
          <fieldset key={label} className="rounded-lg border border-slate-800 p-3">
            <legend className="px-1 text-sm font-medium">{label}</legend>
            <div className="grid max-h-48 grid-cols-1 gap-1 overflow-auto sm:grid-cols-2">
              {categories.map((c) => (
                <label key={c.category} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={set.has(c.category)} onChange={() => toggle(setA, setB, c.category)} />
                  {c.category}
                </label>
              ))}
            </div>
          </fieldset>
        ))}
      </div>
      {brands.length > 0 && (
        <fieldset className="rounded-lg border border-slate-800 p-3">
          <legend className="px-1 text-sm font-medium">Brands I like</legend>
          <div className="grid max-h-48 grid-cols-1 gap-1 overflow-auto sm:grid-cols-2">
            {brands.map((b) => (
              <label key={b.brand} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={likedBrands.has(b.brand)}
                       onChange={() => flip(setLikedBrands, b.brand)} />
                {b.brand}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      <div className="flex flex-wrap gap-4">
        <div>
          <label htmlFor="pmin" className="mb-1 block text-xs text-slate-400">Min price</label>
          <input id="pmin" inputMode="decimal" value={min} onChange={(e) => setMin(e.target.value)} className={box} />
        </div>
        <div>
          <label htmlFor="pmax" className="mb-1 block text-xs text-slate-400">Max price</label>
          <input id="pmax" inputMode="decimal" value={max} onChange={(e) => setMax(e.target.value)} className={box} />
        </div>
      </div>
      <button onClick={save} className="rounded-md bg-violet-600 px-4 py-2 font-medium text-white hover:bg-violet-500">
        Save preferences
      </button>
      {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
    </div>
  );
}

export default function PreferencesPage() {
  const prefs = useAsync((s) => customerApi.preferences(s), []);
  const cats = useAsync((s) => productsApi.categories(s), []);
  const brands = useAsync((s) => productsApi.brands(s), []);
  const [note, setNote] = useState<string | null>(null);

  async function reset(includeExplicit: boolean) {
    const text = includeExplicit
      ? "Reset everything, including the preferences you chose yourself?"
      : "Reset what PersonaFlux has inferred from your activity?";
    if (!window.confirm(text)) return;
    await customerApi.resetPreferences(includeExplicit);
    setNote("Reset done.");
    prefs.reload();
  }

  if (!prefs.data) {
    if (prefs.error) return <ErrorState error={prefs.error} onRetry={prefs.reload} />;
    return <PageLoading />;
  }
  const inferred = prefs.data.inferred;

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-bold">Your preferences</h1>

      <section aria-labelledby="explicit" className="space-y-4">
        <h2 id="explicit" className="text-lg font-semibold">What you told us</h2>
        <p className="text-sm text-slate-400">These are your own choices. Hidden categories are never recommended.</p>
        {cats.data ? (
          <ExplicitEditor
            key={JSON.stringify(prefs.data.explicit)}
            initial={prefs.data.explicit}
            categories={cats.data}
            brands={brands.data ?? []}
            onSaved={() => {
              setNote("Preferences saved. They apply to your next recommendations.");
              prefs.reload();
            }}
          />
        ) : (
          <PageLoading />
        )}
      </section>

      <section aria-labelledby="inferred" className="space-y-4">
        <h2 id="inferred" className="text-lg font-semibold">What we inferred from your activity</h2>
        <p className="text-sm text-slate-400">
          {inferred.note} Based on {inferred.events_considered} recorded event{inferred.events_considered === 1 ? "" : "s"}.
        </p>
        <div className="grid gap-6 md:grid-cols-2">
          <Shares title="Recent interests (last 7 days)" rows={inferred.recent_categories} />
          <Shares title="Longer-term interests" rows={inferred.long_term_categories} />
        </div>
        <div className="flex flex-wrap gap-3">
          <button onClick={() => reset(false)} className="rounded-md bg-slate-800 px-3 py-2 text-sm hover:bg-slate-700">Reset inferred interests</button>
          <button onClick={() => reset(true)} className="rounded-md bg-slate-800 px-3 py-2 text-sm hover:bg-slate-700">Reset everything</button>
        </div>
      </section>

      {note && <p role="status" className="text-sm text-violet-300">{note}</p>}
    </div>
  );
}
