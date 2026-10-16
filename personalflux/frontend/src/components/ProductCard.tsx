import { memo } from "react";
import { Link } from "react-router-dom";
import type { Product } from "../api";

export function imageFor(p: Product) {
  if (p.image_url) return p.image_url;
  return `https://picsum.photos/seed/${p.id}/600/450`;
}

const labels: Record<string, string> = {
  similar_to_session_items: "Recent views",
  similar_to_history: "Your history",
  item_similarity: "Often together",
  popular: "Popular",
  popular_in_category: "Popular here",
  matches_stated_preference: "Your pick",
  catalog_default: "Catalog",
  popular_fallback: "Fallback",
};

function Card({ p, reason, codes }: { p: Product; reason?: string; codes?: string[] }) {
  return (
    <Link className="card" to={`/products/${p.id}`}>
      <img src={imageFor(p)} alt={p.title} loading="lazy" decoding="async" />
      <div className="pad">
        {p.category && <span className="tag">{p.category}</span>}
        <div className="title">{p.title}</div>
        {p.price && <div className="price">${p.price}</div>}
        {(codes?.length || reason) && (
          <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {(codes || []).slice(0, 2).map((c) => (
              <span key={c} className="tag">{labels[c] || c.replace(/_/g, " ")}</span>
            ))}
          </div>
        )}
        {reason && <div className="muted" style={{ marginTop: 6 }}>Why this · {reason}</div>}
      </div>
    </Link>
  );
}

const ProductCard = memo(Card);
export default ProductCard;

export function SkeletonGrid({ n = 6 }: { n?: number }) {
  return (
    <div className="grid">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="skel">
          <div className="img" />
          <div className="ln" style={{ width: "60%" }} />
          <div className="ln" style={{ width: "85%" }} />
        </div>
      ))}
    </div>
  );
}
