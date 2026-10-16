import { useState } from "react";
import { FlaskConical, HeartPulse, Lock, RefreshCw, Rocket } from "lucide-react";
import { EmptyState } from "../components/States";
import { useAuth } from "../features/auth/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { mlApi } from "../lib/endpoints";
import { ApiError } from "../lib/api";

const READERS = ["analyst", "ml_engineer", "admin"];
const OPERATORS = ["ml_engineer", "admin"];

export default function MLPage() {
  const { user } = useAuth();
  const [msg, setMsg] = useState<string | null>(null);
  const health = useAsync((s) => mlApi.health(s), []);
  const exps = useAsync(
    (s) => (user && READERS.includes(user.role) ? mlApi.experiments(s) : Promise.resolve([])),
    [user?.role],
  );
  const models = useAsync(
    (s) => (user && READERS.includes(user.role) ? mlApi.models(s) : Promise.resolve(null)),
    [user?.role],
  );

  if (!user || !READERS.includes(user.role)) {
    return (
      <EmptyState title="ML console needs an analyst, ML engineer or admin account">
        <Lock size={16} className="mx-auto mb-2 opacity-60" />
        <p>Experiment results and model versions are not visible to customer accounts.</p>
      </EmptyState>
    );
  }

  async function promote(version: string) {
    setMsg(null);
    try {
      await mlApi.promote(version);
      setMsg(`Serving ${version}. Promoting an older version rolls back.`);
      models.reload();
      health.reload();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Promotion failed validation; the current model keeps serving.");
    }
  }

  async function scan() {
    setMsg(null);
    try {
      const r = await mlApi.scan();
      setMsg(r.added.length ? `Registered ${r.added.length} version(s) from disk.` : "No new versions on disk.");
      models.reload();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Scan failed.");
    }
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold">ML console</h1>
        <p className="mt-1 text-sm text-slate-400">
          <HeartPulse size={14} className="mr-1 inline" />
          {health.data
            ? `${health.data.status} · ${health.data.model_version ?? health.data.fallback_mode ?? "no model"}`
            : "Checking model service…"}
        </p>
        {msg && <p role="status" className="mt-2 text-sm">{msg}</p>}
      </section>
      <section>
        <h2 className="text-lg font-semibold"><FlaskConical size={16} className="mr-1 inline" />Experiments</h2>
        <p className="mt-1 text-xs text-slate-500">Offline evaluation. Kept separate from live engagement metrics.</p>
        <div className="mt-3 space-y-3">
          {exps.loading && <p className="text-sm text-slate-400">Loading experiments…</p>}
          {(exps.data ?? []).map((e) => (
            <div key={e.id} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="font-medium">{e.name}</p>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-xs text-slate-500">
                    <th className="py-1 pr-3">Model</th>
                    {Object.keys(e.runs[0]?.metrics ?? {}).map((k) => <th key={k} className="py-1 pr-3">{k}</th>)}
                  </tr></thead>
                  <tbody>
                    {e.runs.map((r) => (
                      <tr key={r.model_version} className="border-t border-slate-800">
                        <td className="py-1 pr-3">{r.model_version}</td>
                        {Object.values(r.metrics).map((v, i) => (
                          <td key={i} className="py-1 pr-3 text-slate-300">{typeof v === "number" ? v.toFixed(4) : String(v)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
          {exps.data && exps.data.length === 0 && !exps.loading && (
            <p className="text-sm text-slate-400">No experiments imported yet. Run the offline evaluation, then import it.</p>
          )}
        </div>
      </section>
      <section>
        <h2 className="text-lg font-semibold"><Rocket size={16} className="mr-1 inline" />Models</h2>
        <p className="mt-1 text-xs text-slate-500">Serving: {models.data?.serving ?? "none (database fallback)"}.</p>
        {OPERATORS.includes(user.role) && (
          <button onClick={() => void scan()} className="mt-2 rounded-md bg-slate-800 px-3 py-2 text-sm hover:bg-slate-700">
            <RefreshCw size={14} className="mr-1 inline" />Scan disk for versions
          </button>
        )}
        <div className="mt-3 space-y-2">
          {(models.data?.versions ?? []).map((v) => (
            <div key={v.version} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm">
              <div>
                <p className="font-medium">{v.version}</p>
                <p className="text-xs text-slate-500">{v.status}{v.promoted_at ? ` · promoted ${v.promoted_at}` : ""}</p>
              </div>
              {OPERATORS.includes(user.role) && v.version !== models.data?.serving && v.status !== "failed" && (
                <button onClick={() => void promote(v.version)} className="rounded-md bg-violet-600 px-3 py-1.5 text-white hover:bg-violet-500">
                  Promote
                </button>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
