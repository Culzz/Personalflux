import { Activity, BarChart3, FlaskConical, HeartPulse, Lock } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/States";
import { useAuth } from "../features/auth/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { analyticsApi, mlApi } from "../lib/endpoints";

const DAYS = 30;

/** Counts, straight out of the database. */
function num(v: number | null | undefined) {
  return typeof v === "number" ? v.toLocaleString() : "—";
}

/** Ratios arrive as fractions; nobody reads 0.0312 as a click-through rate. */
function pct(v: number | null | undefined) {
  return typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "—";
}

/** A multiple rather than a share, so it stays a plain number. */
function multiple(v: number | null | undefined) {
  return typeof v === "number" ? v.toFixed(2) : "—";
}

export default function BusinessPage() {
  const { user } = useAuth();
  const over = useAsync((s) => analyticsApi.overview(DAYS, s), []);
  const cats = useAsync((s) => analyticsApi.categories(DAYS, s), []);
  const segs = useAsync((s) => analyticsApi.segments(DAYS, s), []);
  const rec = useAsync((s) => analyticsApi.recs(DAYS, s), []);
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
        <p>The analytics service did not answer.</p>
        <button type="button" className="mt-2 underline" onClick={over.reload}>
          Try again
        </button>
      </EmptyState>
    );
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold">Business overview</h1>
        <p className="mt-1 text-sm text-slate-400">
          <BarChart3 size={14} className="mr-1 inline" />
          Live activity, last {DAYS} days. Not model evaluation.
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
          <p className="font-display text-xl">
            {health.loading ? "…" : health.data ? health.data.model_version ?? "fallback" : "unknown"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {health.data?.status ?? (health.loading ? "" : "the model service did not answer")}
          </p>
          {health.data?.worker_behind && (
            <p className="mt-1 text-xs text-amber-300">
              A worker is still serving the previous version.
            </p>
          )}
        </div>
      </section>

      <Section
        title="Categories"
        loading={cats.loading}
        failed={!cats.loading && !cats.data}
        onRetry={cats.reload}
        empty={(cats.data?.categories.length ?? 0) === 0}
        emptyNote="No category activity in this window yet."
      >
        {(cats.data?.categories ?? []).slice(0, 8).map((c) => (
          <div key={c.category} className="flex justify-between gap-2 border-b border-slate-800 py-2 last:border-0">
            <span>{c.category}</span>
            <span className="text-slate-400">{c.events} events · {c.purchases} buys</span>
          </div>
        ))}
      </Section>

      <Section
        title="Segments"
        loading={segs.loading}
        failed={!segs.loading && !segs.data}
        onRetry={segs.reload}
        empty={(segs.data?.segments.length ?? 0) === 0}
        emptyNote="No customer segments yet."
      >
        {(segs.data?.segments ?? []).map((s) => (
          <div key={s.segment} className="flex justify-between gap-2 border-b border-slate-800 py-2 last:border-0">
            <span>{s.segment}</span>
            <span className="text-slate-400">{s.customers}</span>
          </div>
        ))}
      </Section>

      <Section
        title="Recommendations"
        icon={<FlaskConical size={16} className="mr-1 inline" />}
        loading={rec.loading}
        failed={!rec.loading && !rec.data}
        onRetry={rec.reload}
        empty={false}
        emptyNote=""
      >
        {rec.data && (
          <>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
              <Metric label="Impressions" value={num(rec.data.impressions)} />
              <Metric label="Clicks" value={num(rec.data.clicks_from_recommendations)} />
              <Metric label="Attributed clicks" value={num(rec.data.attributed_clicks)} />
              <Metric label="Click-through rate" value={pct(rec.data.click_through_rate)} />
              <Metric label="Requests shown" value={num(rec.data.recommendation_requests_with_impressions)} />
              <Metric label="Impressions / request" value={multiple(rec.data.impressions_per_request)} />
              <Metric label="Catalogue coverage" value={pct(rec.data.catalogue_coverage_ratio)} />
              <Metric label="Fallback rate" value={pct(rec.data.fallback_rate)} />
            </dl>
            <p className="mt-3 text-xs text-slate-500">
              {num(rec.data.distinct_products_shown)} distinct products shown to people.
            </p>
            {Object.keys(rec.data.impressions_by_model_version ?? {}).length > 0 && (
              <p className="mt-2 text-xs text-slate-500">
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
        )}
      </Section>
    </div>
  );
}

interface SectionProps {
  title: string;
  icon?: ReactNode;
  loading: boolean;
  failed: boolean;
  onRetry: () => void;
  empty: boolean;
  emptyNote: string;
  children: ReactNode;
}

/** One panel. Loading, failed and empty are three different things to a reader,
 *  so the panel never shows an empty list when the request simply failed. */
function Section({ title, icon, loading, failed, onRetry, empty, emptyNote, children }: SectionProps) {
  return (
    <section>
      <h2 className="text-lg font-semibold">{icon}{title}</h2>
      <div className="mt-3 rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm">
        {loading ? (
          <p className="text-slate-400">Loading…</p>
        ) : failed ? (
          <p className="text-slate-400">
            Could not load this.{" "}
            <button type="button" className="underline" onClick={onRetry}>
              Try again
            </button>
          </p>
        ) : empty ? (
          <p className="text-slate-400">{emptyNote}</p>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-lg font-semibold">{value}</dd>
    </div>
  );
}
