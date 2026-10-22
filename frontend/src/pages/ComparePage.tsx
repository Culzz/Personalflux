import type { ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CardSkeletons, EmptyState, ErrorState } from "../components/States";
import { COMPARE_MAX, useCompare } from "../features/compare/CompareContext";
import { useAsync } from "../hooks/useAsync";
import { productsApi } from "../lib/endpoints";
import { formatPrice, stockLabel } from "../lib/format";
import type { Product } from "../lib/types";

/** The ids live in the URL so a comparison can be shared or reloaded as-is. */
function idsFromUrl(raw: string | null): string[] {
  return (raw ?? "").split(",").map((s) => s.trim()).filter(Boolean).slice(0, COMPARE_MAX);
}

export default function ComparePage() {
  const [params] = useSearchParams();
  const { ids: queued } = useCompare();
  const wanted = idsFromUrl(params.get("ids"));
  const ids = wanted.length > 0 ? wanted : queued;

  const result = useAsync(
    (s) => (ids.length > 0 ? productsApi.compare(ids, s) : Promise.resolve<Product[]>([])),
    [ids.join(",")],
  );

  if (ids.length === 0) {
    return (
      <EmptyState title="Nothing to compare yet">
        Add two to four products and they will line up here, side by side.
      </EmptyState>
    );
  }
  if (result.loading) return <CardSkeletons count={3} />;
  if (result.error) return <ErrorState error={result.error} onRetry={result.reload} />;

  const products = result.data ?? [];
  if (products.length < 2) {
    return (
      <EmptyState title="Pick one more to compare">
        A comparison needs at least two products.
      </EmptyState>
    );
  }

  const rows: [string, (p: Product) => ReactNode][] = [
    ["Price", (p) => formatPrice(p.price, p.currency)],
    ["Category", (p) => p.category ?? "Not listed"],
    ["Brand", (p) => p.brand ?? "Not listed"],
    ["Availability", (p) => stockLabel(p.stock, p.is_active)],
    ["Description", (p) => <span className="whitespace-pre-line">{p.description ?? "Not listed"}</span>],
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Compare</h1>
        <p className="mt-1 text-sm text-slate-400">
          {products.length} products side by side. Fields a source does not provide are marked as not listed.
        </p>
      </div>
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full min-w-[36rem] border-collapse text-sm">
          <caption className="sr-only">Side-by-side comparison of the selected products</caption>
          <thead>
            <tr>
              <th scope="col" className="w-28 p-3 text-left align-bottom text-xs uppercase tracking-wide text-slate-500">
                Product
              </th>
              {products.map((p) => (
                <th key={p.id} scope="col" className="p-3 text-left align-bottom">
                  <div className="w-40 space-y-2">
                    <ProductThumb product={p} />
                    <Link to={`/products/${p.id}`} className="block font-medium hover:underline">
                      {p.title}
                    </Link>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, render]) => (
              <tr key={label} className="border-t border-slate-800">
                <th scope="row" className="p-3 text-left align-top text-xs uppercase tracking-wide text-slate-500">
                  {label}
                </th>
                {products.map((p) => (
                  <td key={p.id} className="p-3 align-top text-slate-300">
                    {render(p)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">
        Choosing products to compare does not change your recommendations.
      </p>
    </div>
  );
}

function ProductThumb({ product }: { product: Product }) {
  if (product.image_url) {
    return (
      <img src={product.image_url} alt={product.title}
           className="h-28 w-28 rounded-lg border border-slate-800 object-cover" />
    );
  }
  return (
    <div className="flex h-28 w-28 items-center justify-center rounded-lg border border-slate-800 bg-slate-950 text-center text-[11px] text-slate-500">
      No photo
    </div>
  );
}
