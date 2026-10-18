import { Activity, BarChart3, FlaskConical, HeartPulse, Lock } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/States";
import { useAuth } from "../features/auth/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { analyticsApi, mlApi } from "../lib/endpoints";

function num(v: number | null | undefined) {
  return typeof v === "number" ? v.toLocaleString() : "—";
}

export default function BusinessPage() {
  const { user } = useAuth();
  const over = useAsync((s) => analyticsApi.overview(30, s), []);
  const cats = useAsync((s) => analyticsApi.categories(30, s), []);
  const segs = useAsync((s) => analyticsApi.segments(30, s), []);
  const rec = useAsync((s) => analyticsApi.recs(30, s), []);
  const health = useAsync((s) => mlApi.health(s), []);

  const allowed = user && (user.role === "analyst" || user.role === "admin" || user.role === "ml_engineer");

  if (!user) {
    return (
      <EmptyState title="Sign in to view business metrics">
        <Link className="text-violet-300 underline" to="/login">Sign in</Link> with an analyst account.
      </EmptyState>
    );
  }
  if (!allowed) {
    return (
      <EmptyState title="Analyst role needed">
        <Lock size={16} className="mx-auto mb-2 opacity-60" />
        <p>Your account is a customer account. Business metrics need an analyst, admin or ML engineer role.</p>
      </EmptyState>
    );
  }
  if (over.loading) return <p className="text-sm text-slate-400">Loading live activity…</p>;
  if (!over.data) {
    return (
      <EmptyState title="Metrics unavailable">
        The analytics service did not answer. Check the API is running and try again.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold">Business overview</h1>
        <p className="mt-1 text-sm text-slate-400">
          <BarChart3 size={14} className="mr-1 inline" />
          Live activity, last 30 days. Not model evaluation.
        </p>
      </section>
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="text-sm text-slate-400"><Activity size={14} className="mr-1 inline" />Events</p>
          <p className="font-display text-3xl">{num(over.data.events_total)}</p>
          <p className="mt-1 text-xs text-slate-500">
            {Object.entries(over.data.events_by_type).slice(0, 4).map(([k, v]) => `${k} ${v}`).join(" · ")}
          </p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="text-sm text-slate-400">Active customers</p>
          <p className="font-display text-3xl">{num(over.data.active_customers)}</p>
          <p className="mt-1 text-xs text-slate-500">{num(over.data.anonymous_sessions)} anonymous sessions</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="text-sm text-slate-400"><HeartPulse size={14} className="mr-1 inline" />Model</p>
          <p className="font-display text-xl">{health.data?.model_version ?? (health.data ? "fallback" : "…")}</p>
          <p className="mt-1 text-xs text-slate-500">{health.data?.status ?? ""}</p>
        </div>
      </section>
      <section>
        <h2 className="text-lg font-semibold">Categories</h2>
        <div className="mt-3 rounded-xl border border-slate-800 bg-slate-900 p-4">
          {(cats.data?.categories ?? []).slice(0, 8).map((c) => (
            <div key={c.category} className="flex justify-between gap-2 border-b border-slate-800 py-2 text-sm last:border-0">
              <span>{c.category}</span>
              <span className="text-slate-400">{c.events} events · {c.purchases} buys</span>
            </div>
          ))}
          {(cats.data?.categories.length ?? 0) === 0 && <p className="text-sm text-slate-400">No data yet.</p>}
        </div>
      </section>
      <section>
        <h2 className="text-lg font-semibold">Segments</h2>
        <div className="mt-3 rounded-xl border border-slate-800 bg-slate-900 p-4">
          {(segs.data?.segments ?? []).map((s) => (
            <div key={s.segment} className="flex justify-between gap-2 border-b border-slate-800 py-2 text-sm last:border-0">
              <span>{s.segment}</span>
              <span className="text-slate-400">{s.customers}</span>
            </div>
          ))}
          {(segs.data?.segments.length ?? 0) === 0 && <p className="text-sm text-slate-400">No data yet.</p>}
        </div>
      </section>
      <section>
        <h2 className="text-lg font-semibold"><FlaskConical size={16} className="mr-1 inline" />Recommendations</h2>
        <div className="mt-3 rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm">
          {rec.data ? (
            <>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
                <Metric label="Impressions" value={rec.data.impressions} />
                <Metric label="Clicks" value={rec.data.clicks_from_recommendations} />
                <Metric label="Attributed clicks" value={rec.data.attributed_clicks} />
                <Metric label="Click-through rate" value={fmt(rec.data.click_through_rate)} />
                <Metric label="Requests shown" value={rec.data.recommendation_requests_with_impressions} />
                <Metric label="Impressions / request" value={fmt(rec.data.impressions_per_request)} />
                <Metric label="Catalogue coverage" value={fmt(rec.data.catalogue_coverage_ratio)} />
                <Metric label="Fallback rate" value={fmt(rec.data.fallback_rate)} />
              </dl>
              {Object.keys(rec.data.impressions_by_model_version ?? {}).length > 0 && (
                <p className="mt-3 text-xs text-slate-500">
                  By model version:{" "}
                  {Object.entries(rec.data.impressions_by_model_version)
                    .map(([v, n]) => `${v === "None" ? "fallback" : v} ${n}`)
                    .join(" · ")}
                </p>
              )}
              <details className="mt-3 text-xs text-slate-500">
                <summary className="cursor-pointer">How these are defined</summary>
                <ul className="mt-2 space-y-1">
                  {Object.entries(rec.data.definitions ?? {}).map(([k, v]) => (
                    <li key={k}>
                      <span className="font-medium">{k.replace(/_/g, " ")}</span> — {v}
                    </li>
                  ))}
                </ul>
              </details>
            </>
          ) : (
            <span className="text-slate-400">No data yet.</span>
          )}
        </div>
      </section>
    </div>
  );
}

function fmt(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : String(value);
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-lg font-semibold">{value}</dd>
    </div>
  );
}
