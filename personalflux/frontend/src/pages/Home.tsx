import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, TrendingUp } from "lucide-react";
import { api, type RecResponse } from "../api";
import ProductCard, { SkeletonGrid } from "../components/ProductCard";
import EmptyState from "../components/EmptyState";

export default function Home() {
  const [feed, setFeed] = useState<RecResponse | null>(null);
  const [trend, setTrend] = useState<RecResponse | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.home().then(setFeed).catch(() => setErr("Backend not reachable"));
    api.trending().then(setTrend).catch(() => {});
  }, []);

  if (err) return <p>{err}</p>;
  if (!feed) return (
    <div>
      <div className="hero"><h1>For you</h1></div>
      <SkeletonGrid />
    </div>
  );

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
            <ProductCard key={r.product_id} p={r.product} reason={r.explanation} />
          ))}
        </div>
      )}
      {(trend?.recommendations.length || 0) > 0 && (
        <div style={{ marginTop: 32 }}>
          <h2><TrendingUp size={18} style={{ verticalAlign: -3 }} /> Trending now</h2>
          <div className="grid">
            {trend!.recommendations.slice(0, 3).map((r) => (
              <ProductCard key={r.product_id} p={r.product} reason={r.explanation} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
