import { Link } from "react-router-dom";
import type { Product } from "../api";

export function imageFor(p: Product) {
  if (p.image_url) return p.image_url;
  return `https://picsum.photos/seed/${p.id}/600/450`;
}

export default function ProductCard({ p, reason }: { p: Product; reason?: string }) {
  return (
    <Link className="card" to={`/products/${p.id}`}>
      <img src={imageFor(p)} alt={p.title} loading="lazy" />
      <div className="pad">
        {p.category && <span className="tag">{p.category}</span>}
        <div className="title">{p.title}</div>
        {p.price && <div className="price">${p.price}</div>}
        {reason && <div className="muted" style={{ marginTop: 6 }}>{reason}</div>}
      </div>
    </Link>
  );
}
