import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ProductCard } from "../components/ProductCard";
import { CardSkeletons, EmptyState, ErrorState } from "../components/States";
import { useToast } from "../features/toast/ToastContext";
import { useAsync } from "../hooks/useAsync";
import { ApiError } from "../lib/api";
import { collectionsApi } from "../lib/endpoints";

function reason(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export default function CollectionPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const list = useAsync((s) => collectionsApi.get(id, s), [id]);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");

  async function rename(e: FormEvent) {
    e.preventDefault();
    const wanted = name.trim();
    if (!wanted || !list.data) return;
    try {
      const updated = await collectionsApi.rename(id, wanted);
      list.setData((prev) => ({ ...prev, name: updated.name }));
      setEditing(false);
      toast.notify("List renamed.");
    } catch (err) {
      toast.notify(reason(err, "Could not rename that list."), { tone: "error" });
    }
  }

  async function removeItem(productId: string, title: string) {
    const before = list.data;
    if (!before) return;
    list.setData((prev) => ({ ...prev, items: prev.items.filter((p) => p.id !== productId) }));
    try {
      await collectionsApi.removeItem(id, productId);
      toast.notify(`Removed ${title} from ${before.name}.`, {
        action: {
          label: "Undo",
          onClick: async () => {
            try {
              await collectionsApi.addItem(id, productId);
              list.reload();
            } catch {
              toast.notify("Could not undo that.", { tone: "error" });
            }
          },
        },
      });
    } catch (err) {
      list.setData(() => before); // put the card back where it was
      toast.notify(reason(err, "Could not remove that item."), { tone: "error" });
    }
  }

  async function deleteList() {
    if (!list.data) return;
    const name = list.data.name;
    try {
      await collectionsApi.remove(id);
      toast.notify(`Deleted ${name}.`);
      navigate("/saved");
    } catch (err) {
      toast.notify(reason(err, "Could not delete that list."), { tone: "error" });
    }
  }

  if (list.loading) return <CardSkeletons count={4} />;
  if (list.error) return <ErrorState error={list.error} onRetry={list.reload} />;
  if (!list.data) return null;

  return (
    <div className="space-y-4">
      {editing ? (
        <form className="flex flex-wrap items-center gap-2" onSubmit={rename}>
          <label className="sr-only" htmlFor="list-name">
            List name
          </label>
          <input
            id="list-name"
            defaultValue={list.data.name}
            maxLength={80}
            autoFocus
            onChange={(e) => setName(e.target.value)}
            className="w-56 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm"
          />
          <button
            type="submit"
            className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-900 hover:bg-white"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="rounded-md bg-slate-800 px-3 py-1.5 text-sm hover:bg-slate-700"
          >
            Cancel
          </button>
        </form>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold">{list.data.name}</h1>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setName(list.data!.name);
                setEditing(true);
              }}
              className="rounded-md bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
            >
              Rename
            </button>
            <button
              type="button"
              onClick={() => void deleteList()}
              className="rounded-md bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
            >
              Delete list
            </button>
          </div>
        </div>
      )}

      <p className="text-xs text-slate-400">
        {list.data.items.length} {list.data.items.length === 1 ? "item" : "items"} ·{" "}
        <Link className="underline" to="/saved">
          Back to saved items
        </Link>
      </p>

      {list.data.items.length === 0 ? (
        <EmptyState title="This list is empty">
          Add items to it from{" "}
          <Link className="underline" to="/saved">
            saved items
          </Link>
          .
        </EmptyState>
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {list.data.items.map((p) => (
            <li key={p.id}>
              <ProductCard
                product={p}
                actions={
                  <button
                    className="rounded-md bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
                    onClick={() => void removeItem(p.id, p.title)}
                  >
                    Remove<span className="sr-only"> {p.title} from this list</span>
                  </button>
                }
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
