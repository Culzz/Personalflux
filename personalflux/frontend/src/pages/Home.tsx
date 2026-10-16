import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { History, Sparkles, TrendingUp } from "lucide-react";
import { api, isLoggedIn, type Prefs, type RecResponse } from "../api";
import ProductCard, { SkeletonGrid } from "../components/ProductCard";
import EmptyState from "../components/EmptyState";

export default function Home() {
  const [feed, setFeed] = useState<RecResponse | null>(null);
  const [trend, setTrend] = useState<RecResponse | null>(null);
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.home().then((f) => {
      setFeed(f);
      if (f.request_id) {
        api.impressions(f.request_id, f.model_version, f.recommendations.map((r, i) => ({
          product_id: r.product_id, position: i + 1,
        })));
      }
    }).catch(() => setErr("Backend not reachable"));
    api.trending().then(setTrend).catch(() => {});
    if (isLoggedIn()) api.prefs().then(setPrefs).catch(() => {});
  }, []);

  if (err) return <p>{err}</p>;
  if (!feed) return (
    <div>
      <div className="hero"><h1>For you</h1></div>
      <SkeletonGrid />
    </div>
  );

  const recent = prefs?.inferred.recent_categories.slice(0, 3).map((c) => c.category) || [];
  const longTerm = prefs?.inferred.long_term_categories.slice(0, 3).map((c) => c.category) || [];

  return (
    <div>
      <div className="hero">
        <h1>For you</h1>
        <p>
          <Sparkles size={14} style={{ verticalAlign: -2 }} />{" "}
          {feed.strategy.replace(/_/g, " ")}
          {feed.fallback_used ? " · popular fallback" : " · personalised"} ·{" "}
          {feed.model_version || "no model loaded"}
        </p>
        {prefs && (recent.length > 0 || longTerm.length > 0) && (
          <p className="muted">
            <History size={13} style={{ verticalAlign: -2 }} /> Recent: {recent.join(", ") || "—"} ·
            Long-term: {longTerm.join(", ") || "—"}
          </p>
        )}
      </div>
      {feed.recommendations.length === 0 ? (
        <EmptyState
          icon={<Sparkles size={28} />}
          title="Nothing personal yet"
          hint="Browse a few products and your feed will adapt to recent intent without losing long-term taste."
          action={<Link to="/discover"><button>Discover products</button></Link>}
        />
      ) : (
        <div className="grid">
          {feed.recommendations.map((r) => (
            <ProductCard key={r.product_id} p={r.product} reason={r.explanation} codes={r.reason_codes} />
          ))}
        </div>
      )}
      {(trend?.recommendations.length || 0) > 0 && (
        <div style={{ marginTop: 32 }}>
          <h2><TrendingUp size={18} style={{ verticalAlign: -3 }} /> Trending now</h2>
          <div className="grid">
            {trend!.recommendations.slice(0, 3).map((r) => (
              <ProductCard key={r.product_id} p={r.product} reason={r.explanation} codes={r.reason_codes} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
