import { useState, type FormEvent } from "react";
import { Lock, Plus, ShieldCheck } from "lucide-react";
import { EmptyState } from "../components/States";
import { useAuth } from "../features/auth/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { adminApi, productsApi } from "../lib/endpoints";
import { ApiError } from "../lib/api";

const input = "w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2";

export default function AdminPage() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [msg, setMsg] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [price, setPrice] = useState("");
  const [category, setCategory] = useState("");

  const isAdmin = user?.role === "admin";
  const catalog = useAsync(
    (s) => (isAdmin ? productsApi.list({ q: q || undefined, page, page_size: 12 }, s) : Promise.resolve(null)),
    [isAdmin, page],
  );
  const users = useAsync((s) => (isAdmin ? adminApi.users(s) : Promise.resolve([])), [isAdmin]);
  const logs = useAsync((s) => (isAdmin ? adminApi.auditLogs(s) : Promise.resolve([])), [isAdmin]);

  if (!isAdmin) {
    return (
      <EmptyState title="Admins only">
        <Lock size={16} className="mx-auto mb-2 opacity-60" />
        <p>Product and user administration needs an admin account.</p>
      </EmptyState>
    );
  }

  async function search(e: FormEvent) {
    e.preventDefault();
    setPage(1);
    catalog.reload();
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await productsApi.create({ title, price: price || null, category: category || null });
      setTitle(""); setPrice(""); setCategory("");
      setMsg("Product created and live in the catalog.");
      catalog.reload();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "Could not create the product.");
    }
  }

  async function toggleActive(id: string, active: boolean) {
    await productsApi.update(id, { is_active: !active });
    catalog.reload();
  }

  async function setRole(id: string, role: string) {
    await adminApi.updateUser(id, { role });
    users.reload();
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold"><ShieldCheck size={20} className="mr-1 inline" />Admin</h1>
        {msg && <p role="status" className="mt-2 text-sm">{msg}</p>}
      </section>
      <section>
        <h2 className="text-lg font-semibold">Products</h2>
        <form onSubmit={search} className="mt-2 flex gap-2">
          <input aria-label="Search products" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title or category" className={input} />
          <button type="submit" className="shrink-0 rounded-md bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700">Search</button>
        </form>
        <ul className="mt-3 space-y-2">
          {(catalog.data?.items ?? []).map((p) => (
            <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-900 p-3 text-sm">
              <div>
                <p className="font-medium">{p.title} {!p.is_active && <span className="text-slate-500">(inactive)</span>}</p>
                <p className="text-xs text-slate-500">{p.category ?? "uncategorised"} · {p.price ?? "no price"}</p>
              </div>
              <button onClick={() => void toggleActive(p.id, p.is_active)} className="rounded-md bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700">
                {p.is_active ? "Deactivate" : "Activate"}
              </button>
            </li>
          ))}
        </ul>
        <form onSubmit={create} className="mt-4 space-y-2 rounded-xl border border-dashed border-slate-700 p-4">
          <p className="text-sm font-medium"><Plus size={14} className="mr-1 inline" />New product</p>
          <input aria-label="Title" required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" className={input} />
          <div className="flex gap-2">
            <input aria-label="Category" value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Category" className={input} />
            <input aria-label="Price" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Price" className={input} />
          </div>
          <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">Create product</button>
        </form>
      </section>
      <section>
        <h2 className="text-lg font-semibold">Users</h2>
        <ul className="mt-2 space-y-2">
          {(users.data ?? []).map((u) => (
            <li key={u.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-900 p-3 text-sm">
              <span>{u.email} · {u.role}{!u.is_active && " · inactive"}</span>
              <select aria-label={`Role for ${u.email}`} value={u.role} onChange={(e) => void setRole(u.id, e.target.value)} className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm">
                {["customer", "analyst", "admin", "ml_engineer"].map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="text-lg font-semibold">Recent admin activity</h2>
        <ul className="mt-2 space-y-1 text-sm text-slate-400">
          {(logs.data ?? []).slice(0, 10).map((l) => (
            <li key={l.id}>{l.action} · {l.target_type}{l.created_at ? ` · ${l.created_at}` : ""}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
