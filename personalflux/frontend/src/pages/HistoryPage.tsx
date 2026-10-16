import { ProductCard } from "../components/ProductCard";
import { CardSkeletons, EmptyState, ErrorState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { customerApi } from "../lib/endpoints";

export default function HistoryPage() {
  const history = useAsync((s) => customerApi.history(60, s), []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Recently viewed</h1>
        {history.data && history.data.length > 0 && (
          <button
            className="rounded-md bg-slate-800 px-3 py-1.5 text-sm hover:bg-slate-700"
            onClick={async () => {
              if (!window.confirm("Delete your whole viewing history? This cannot be undone.")) return;
              await customerApi.clearHistory();
              history.setData(() => []);
            }}
          >
            Clear all history
          </button>
        )}
      </div>
      <p className="text-sm text-slate-400">This is what PersonaFlux has recorded about your browsing. Remove anything you like.</p>
      {history.loading && <CardSkeletons count={4} />}
      {history.error && <ErrorState error={history.error} onRetry={history.reload} />}
      {history.data &&
        (history.data.length === 0 ? (
          <EmptyState title="No history recorded">
            Nothing is stored until personalisation is on and you start browsing.
          </EmptyState>
        ) : (
          <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {history.data.map((h) => (
              <li key={h.product.id}>
                <ProductCard
                  product={h.product}
                  explanation={`Last viewed ${new Date(h.last_seen).toLocaleString()}`}
                  actions={
                    <button
                      className="rounded-md bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
                      onClick={async () => {
                        await customerApi.removeFromHistory(h.product.id);
                        history.setData((prev) => prev.filter((x) => x.product.id !== h.product.id));
                      }}
                    >
                      Remove<span className="sr-only"> {h.product.title}</span>
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
