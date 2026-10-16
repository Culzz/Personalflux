import { useEffect, useState } from "react";
import { Activity, BarChart3, FlaskConical, HeartPulse, Lock } from "lucide-react";
import { api } from "../api";
import EmptyState from "../components/EmptyState";

function num(v: unknown) {
  return typeof v === "number" ? v.toLocaleString() : "—";
}

export default function Business() {
  const [over, setOver] = useState<Record<string, unknown> | null>(null);
  const [cats, setCats] = useState<{ categories: { category: string; events: number; views: number; purchases: number }[] } | null>(null);
  const [segs, setSegs] = useState<{ segments: { segment: string; customers: number }[] } | null>(null);
  const [rec, setRec] = useState<Record<string, unknown> | null>(null);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    api.overview().then((d) => { if (!d) setDenied(true); else setOver(d as Record<string, unknown>); });
    api.analyticsCategories().then((d) => d && setCats(d as typeof cats));
    api.segments().then((d) => d && setSegs(d as typeof segs));
    api.recPerf().then((d) => d && setRec(d as Record<string, unknown>));
    api.mlHealth().then((d) => d && setHealth(d as Record<string, unknown>));
  }, []);

  if (denied) {
    return (
      <div>
        <div className="hero"><h1>Business</h1></div>
        <EmptyState
          icon={<Lock size={28} />}
          title="Analyst role needed"
          hint="Business metrics require an analyst or admin account. Live activity only — offline model results stay under ML experiments."
        />
      </div>
    );
  }
  if (!over) return <p className="muted">Loading live activity...</p>;

  return (
    <div>
      <div className="hero">
        <h1><BarChart3 size={20} style={{ verticalAlign: -3 }} /> Business overview</h1>
        <p className="muted">Live activity, last 30 days. Not model evaluation.</p>
      </div>
      <div className="grid">
        <div className="card"><div className="pad">
          <div className="muted"><Activity size={14} /> Events</div>
          <h2>{num(over.events_total)}</h2>
        </div></div>
        <div className="card"><div className="pad">
          <div className="muted">Active customers</div>
          <h2>{num(over.active_customers)}</h2>
        </div></div>
        <div className="card"><div className="pad">
          <div className="muted"><HeartPulse size={14} /> Model</div>
          <h2 style={{ fontSize: 18 }}>{(health?.model_version as string) || (health ? "fallback" : "…")}</h2>
          <div className="muted">{(health?.status as string) || ""}</div>
        </div></div>
      </div>
      <h3 style={{ marginTop: 24 }}>Categories</h3>
      <div className="card"><div className="pad">
        {(cats?.categories || []).slice(0, 8).map((c) => (
          <div key={c.category} className="row" style={{ justifyContent: "space-between" }}>
            <span>{c.category}</span>
            <span className="muted">{c.events} events · {c.purchases} buys</span>
          </div>
        )) || <span className="muted">No data yet.</span>}
      </div></div>
      <h3 style={{ marginTop: 24 }}>Segments</h3>
      <div className="card"><div className="pad">
        {(segs?.segments || []).map((s) => (
          <div key={s.segment} className="row" style={{ justifyContent: "space-between" }}>
            <span>{s.segment}</span><span className="muted">{s.customers}</span>
          </div>
        )) || <span className="muted">No data yet.</span>}
      </div></div>
      <h3 style={{ marginTop: 24 }}><FlaskConical size={16} /> Recommendations</h3>
      <div className="card"><div className="pad">
        <div className="muted">
          {String(rec?.impressions ?? "—")} impressions · CTR {String(rec?.click_through_rate ?? "—")}
        </div>
      </div></div>
    </div>
  );
}
