import { useEffect, useState } from "react";
import { api, type RecResponse } from "../api";
import ProductCard from "../components/ProductCard";

export default function Home() {
  const [feed, setFeed] = useState<RecResponse | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.home().then(setFeed).catch(() => setErr("Backend not reachable"));
  }, []);

  if (err) return <p>{err}</p>;
  if (!feed) return <p className="muted">Loading your feed...</p>;

  return (
    <div>
      <div className="hero">
        <h1>For you</h1>
        <p>
          {feed.strategy.replace(/_/g, " ")}
          {feed.fallback_used ? " · popular fallback" : ""} ·{" "}
          {feed.model_version || "no model loaded"}
        </p>
      </div>
      <div className="grid">
        {feed.recommendations.map((r) => (
          <ProductCard key={r.product_id} p={r.product} reason={r.explanation} />
        ))}
      </div>
    </div>
  );
}
