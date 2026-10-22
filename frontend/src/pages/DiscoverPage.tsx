import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { Pagination } from "../components/Pagination";
import { ProductCard } from "../components/ProductCard";
import { SaveButton } from "../components/SaveButton";
import { CardSkeletons, EmptyState, ErrorState } from "../components/States";
import { useTracking } from "../features/tracking/useTracking";
import { useAsync } from "../hooks/useAsync";
import { productsApi } from "../lib/endpoints";
import type { CategoryCount } from "../lib/types";

const PAGE_SIZE = 12;
const SORTS = [
  ["newest", "Newest"], ["price_asc", "Price: low to high"],
  ["price_desc", "Price: high to low"], ["title", "Title A to Z"],
] as const;

interface FormProps {
  initial: { q: string; category: string; min: string; max: string; sort: string };
  categories: CategoryCount[];
  onSubmit: (v: FormProps["initial"]) => void;
}

function FilterForm({ initial, categories, onSubmit }: FormProps) {
  const [v, setV] = useState(initial);
  const [error, setError] = useState<string | null>(null);

  function submit(e: FormEvent) {
    e.preventDefault();
    const bad = (s: string) => s !== "" && !(Number(s) >= 0);
    if (bad(v.min) || bad(v.max)) return setError("Prices must be numbers of 0 or more.");
    if (v.min !== "" && v.max !== "" && Number(v.min) > Number(v.max)) {
      return setError("Minimum price cannot be above the maximum.");
    }
    setError(null);
    onSubmit(v);
  }
  const field = "rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm";

  return (
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-6" role="search" aria-label="Search products">
      <div className="sm:col-span-2">
        <label htmlFor="q" className="mb-1 block text-xs text-slate-400">Search</label>
        <input id="q" className={`${field} w-full`} value={v.q} onChange={(e) => setV({ ...v, q: e.target.value })} />
      </div>
      <div className="sm:col-span-2">
        <label htmlFor="cat" className="mb-1 block text-xs text-slate-400">Category</label>
        <select id="cat" className={`${field} w-full`} value={v.category} onChange={(e) => setV({ ...v, category: e.target.value })}>
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.category} value={c.category}>{c.category} ({c.products})</option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="min" className="mb-1 block text-xs text-slate-400">Min price</label>
        <input id="min" inputMode="decimal" className={`${field} w-full`} value={v.min} onChange={(e) => setV({ ...v, min: e.target.value })} />
      </div>
      <div>
        <label htmlFor="max" className="mb-1 block text-xs text-slate-400">Max price</label>
        <input id="max" inputMode="decimal" className={`${field} w-full`} value={v.max} onChange={(e) => setV({ ...v, max: e.target.value })} />
      </div>
      <div className="sm:col-span-2">
        <label htmlFor="sort" className="mb-1 block text-xs text-slate-400">Sort by</label>
        <select id="sort" className={`${field} w-full`} value={v.sort} onChange={(e) => setV({ ...v, sort: e.target.value })}>
          {SORTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>
      <div className="flex items-end">
        <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
          Search
        </button>
      </div>
      {error && <p role="alert" className="text-sm text-red-300 sm:col-span-6">{error}</p>}
    </form>
  );
}

export default function DiscoverPage() {
  const [params, setParams] = useSearchParams();
  const { track } = useTracking();

  const q = params.get("q") ?? "";
  const category = params.get("category") ?? "";
  const min = params.get("min_price") ?? "";
  const max = params.get("max_price") ?? "";
  const sort = params.get("sort") ?? "newest";
  const page = Math.max(1, Number(params.get("page") ?? 1) || 1);

  const categories = useAsync((s) => productsApi.categories(s), []);
  const results = useAsync(
    (s) =>
      productsApi.list(
        { q: q || undefined, category: category || undefined, min_price: min || undefined,
          max_price: max || undefined, sort, page, page_size: PAGE_SIZE },
        s,
      ),
    [q, category, min, max, sort, page],
  );

  function apply(v: FormProps["initial"]) {
    const next = new URLSearchParams();
    if (v.q.trim()) next.set("q", v.q.trim());
    if (v.category) next.set("category", v.category);
    if (v.min) next.set("min_price", v.min);
    if (v.max) next.set("max_price", v.max);
    if (v.sort !== "newest") next.set("sort", v.sort);
    setParams(next);
    // A search is recorded with its category only. The words typed are never sent.
    track("search", undefined, v.category ? { category: v.category } : undefined);
  }

  function goTo(p: number) {
    const next = new URLSearchParams(params);
    next.set("page", String(p));
    setParams(next);
  }

  const totalPages = results.data ? Math.max(1, Math.ceil(results.data.total / PAGE_SIZE)) : 1;
  const formKey = [q, category, min, max, sort].join("|");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Discover</h1>
      <FilterForm
        key={formKey}
        initial={{ q, category, min, max, sort }}
        categories={categories.data ?? []}
        onSubmit={apply}
      />
      <p className="text-sm text-slate-400" aria-live="polite">
        {results.data ? `${results.data.total} product${results.data.total === 1 ? "" : "s"} found` : "\u00a0"}
      </p>
      {results.loading && <CardSkeletons count={PAGE_SIZE} />}
      {results.error && <ErrorState error={results.error} onRetry={results.reload} />}
      {results.data &&
        (results.data.items.length === 0 ? (
          <EmptyState title="No products match those filters">Try removing a filter or searching for something else.</EmptyState>
        ) : (
          <>
            <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {results.data.items.map((p) => (
                <li key={p.id}>
                  <ProductCard product={p} actions={<SaveButton product={p} />} />
                </li>
              ))}
            </ul>
            <Pagination page={page} totalPages={totalPages} onChange={goTo} />
          </>
        ))}
    </div>
  );
}
