import { memo } from "react";
import { Link } from "react-router-dom";
import type { Product } from "../api";

export function imageFor(p: Product) {
  if (p.image_url) return p.image_url;
  return `https://picsum.photos/seed/${p.id}/600/450`;
}

function Card({ p, reason }: { p: Product; reason?: string }) {
  return (
    <Link className="card" to={`/products/${p.id}`}>
      <img src={imageFor(p)} alt={p.title} loading="lazy" decoding="async" />
      <div className="pad">
        {p.category && <span className="tag">{p.category}</span>}
        <div className="title">{p.title}</div>
        {p.price && <div className="price">${p.price}</div>}
        {reason && <div className="muted" style={{ marginTop: 6 }}>{reason}</div>}
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
