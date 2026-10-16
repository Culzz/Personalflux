import { ProductCard } from "../components/ProductCard";
import { CardSkeletons, EmptyState, ErrorState } from "../components/States";
import { useSaved } from "../features/saved/SavedContext";
import { useAsync } from "../hooks/useAsync";
import { customerApi } from "../lib/endpoints";

export default function SavedPage() {
  const saved = useAsync((s) => customerApi.saved(s), []);
  const ctx = useSaved();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Saved items</h1>
      {saved.loading && <CardSkeletons count={4} />}
      {saved.error && <ErrorState error={saved.error} onRetry={saved.reload} />}
      {saved.data &&
        (saved.data.length === 0 ? (
          <EmptyState title="Nothing saved yet">Use the Save button on any product to keep it here.</EmptyState>
        ) : (
          <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {saved.data.map((s) => (
              <li key={s.product.id}>
                <ProductCard
                  product={s.product}
                  actions={
                    <button
                      className="rounded-md bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
                      onClick={async () => {
                        await ctx.toggle(s.product);
                        saved.setData((prev) => prev.filter((x) => x.product.id !== s.product.id));
                      }}
                    >
                      Remove<span className="sr-only"> {s.product.title}</span>
                    </button>
                  }
                />
              </li>
            ))}
          </ul>
        ))}
    </div>
  );
}
