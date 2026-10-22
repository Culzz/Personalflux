import { ProductCard } from "../components/ProductCard";
import { CardSkeletons, EmptyState, ErrorState } from "../components/States";
import { useToast } from "../features/toast/ToastContext";
import { useAsync } from "../hooks/useAsync";
import { customerApi } from "../lib/endpoints";

export default function HistoryPage() {
  const history = useAsync((s) => customerApi.history(60, s), []);
  const toast = useToast();

  async function remove(productId: string, title: string) {
    const before = history.data;
    history.setData((prev) => prev.filter((x) => x.product.id !== productId)); // optimistic
    try {
      await customerApi.removeFromHistory(productId);
      toast.notify(`Removed ${title} from your history.`);
    } catch {
      if (before) history.setData(() => before); // put it back if the server said no
      toast.notify("Could not update your history.", { tone: "error" });
    }
  }

  async function clearAll() {
    if (!window.confirm("Delete your whole viewing history? This cannot be undone.")) return;
    const before = history.data;
    history.setData(() => []);
    try {
      await customerApi.clearHistory();
    } catch {
      if (before) history.setData(() => before);
      toast.notify("Could not clear your history.", { tone: "error" });
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Recently viewed</h1>
        {history.data && history.data.length > 0 && (
          <button
            className="rounded-md bg-slate-800 px-3 py-1.5 text-sm hover:bg-slate-700"
            onClick={() => void clearAll()}
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
                      onClick={() => void remove(h.product.id, h.product.title)}
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
