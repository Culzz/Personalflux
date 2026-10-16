import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type RecResponse } from "../api";

export default function Home() {
  const [feed, setFeed] = useState<RecResponse | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.home().then(setFeed).catch(() => setErr("Backend not reachable"));
  }, []);

  if (err) return <p>{err}</p>;
  if (!feed) return <p>Loading recommendations...</p>;

  return (
    <div>
      <p className="muted">
        {feed.strategy} {feed.fallback_used ? "(fallback)" : ""} ·{" "}
        {feed.model_version || "no model"}
      </p>
      <div className="grid">
        {feed.recommendations.map((r) => (
          <Link key={r.product_id} className="card" to={`/products/${r.product.id}`}>
            <div>{r.product.title}</div>
            <div className="muted">{r.product.category || "uncategorised"}</div>
            <div className="muted">{r.explanation}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
