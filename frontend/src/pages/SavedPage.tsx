import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ProductCard } from "../components/ProductCard";
import { CardSkeletons, EmptyState, ErrorState } from "../components/States";
import { useSaved } from "../features/saved/SavedContext";
import { useToast } from "../features/toast/ToastContext";
import { useAsync } from "../hooks/useAsync";
import { ApiError } from "../lib/api";
import { collectionsApi, customerApi } from "../lib/endpoints";
import type { Product } from "../lib/types";

function reason(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export default function SavedPage() {
  const saved = useAsync((s) => customerApi.saved(s), []);
  const lists = useAsync((s) => collectionsApi.list(s), []);
  const ctx = useSaved();
  const toast = useToast();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  async function remove(productId: string, title: string) {
    const product = saved.data?.find((x) => x.product.id === productId)?.product;
    if (!product) return;
    try {
      await ctx.toggle(product);
      saved.setData((prev) => prev.filter((x) => x.product.id !== productId));
      toast.notify(`Removed ${title}.`, {
        action: {
          label: "Undo",
          onClick: async () => {
            await ctx.toggle(product);
            saved.reload();
          },
        },
      });
    } catch {
      toast.notify("Could not remove that item.", { tone: "error" });
    }
  }

  async function createList(e: FormEvent) {
    e.preventDefault();
    const wanted = name.trim();
    if (!wanted || busy) return;
    setBusy(true);
    try {
      await collectionsApi.create(wanted);
      setName("");
      // Fetch again rather than guess: the server owns the id and the order.
      lists.reload();
      toast.notify(`Created ${wanted}.`);
    } catch (err) {
      toast.notify(reason(err, "Could not create that list."), { tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function addToList(listId: string, listName: string, product: Product) {
    const count = (delta: number) =>
      lists.setData((prev) =>
        prev.map((l) =>
          l.id === listId ? { ...l, item_count: Math.max(0, l.item_count + delta) } : l,
        ),
      );
    count(1); // optimistic: the chip updates now, and rolls back below if the server says no
    try {
      await collectionsApi.addItem(listId, product.id);
      toast.notify(`Added ${product.title} to ${listName}.`, {
        action: {
          label: "Undo",
          onClick: async () => {
            try {
              await collectionsApi.removeItem(listId, product.id);
              count(-1);
            } catch {
              toast.notify("Could not undo that.", { tone: "error" });
            }
          },
        },
      });
    } catch (err) {
      count(-1);
      toast.notify(reason(err, "Could not add that to the list."), { tone: "error" });
    }
  }

  const hasLists = (lists.data?.length ?? 0) > 0;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Saved items</h1>

      <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="text-sm font-semibold">Your lists</h2>
        <p className="mt-1 text-xs text-slate-400">
          Group saved items into lists so a long browse stays organised.
        </p>

        {lists.loading && <p className="mt-3 text-xs text-slate-500">Loading your lists…</p>}
        {lists.error && (
          <p className="mt-3 text-xs text-slate-400">
            Could not load your lists.{" "}
            <button type="button" className="underline" onClick={lists.reload}>
              Try again
            </button>
          </p>
        )}
        {hasLists && (
          <ul className="mt-3 flex flex-wrap gap-2">
            {lists.data!.map((l) => (
              <li key={l.id}>
                <Link
                  to={`/lists/${l.id}`}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-3 py-1 text-xs hover:border-slate-500"
                >
                  {l.name}
                  <span className="text-slate-500">{l.item_count}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}

        <form className="mt-3 flex flex-wrap gap-2" onSubmit={createList}>
          <label className="sr-only" htmlFor="new-list-name">
            New list name
          </label>
          <input
            id="new-list-name"
            value={name}
            maxLength={80}
            placeholder="Kitchen ideas"
            onChange={(e) => setName(e.target.value)}
            className="w-44 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm placeholder:text-slate-600"
          />
          <button
            type="submit"
            disabled={!name.trim() || busy}
            className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-900 hover:bg-white disabled:opacity-40"
          >
            Create list
          </button>
        </form>
      </section>

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
                    <>
                      <button
                        className="rounded-md bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
                        onClick={() => void remove(s.product.id, s.product.title)}
                      >
                        Remove<span className="sr-only"> {s.product.title}</span>
                      </button>
                      {hasLists && (
                        <select
                          aria-label={`Add ${s.product.title} to a list`}
                          value=""
                          onChange={(e) => {
                            const list = lists.data?.find((l) => l.id === e.target.value);
                            if (list) void addToList(list.id, list.name, s.product);
                          }}
                          className="rounded-md bg-slate-800 px-2 py-1.5 text-xs"
                        >
                          <option value="">Add to list…</option>
                          {lists.data!.map((l) => (
                            <option key={l.id} value={l.id}>
                              {l.name}
                            </option>
                          ))}
                        </select>
                      )}
                    </>
                  }
                />
              </li>
            ))}
          </ul>
        ))}
    </div>
  );
}
