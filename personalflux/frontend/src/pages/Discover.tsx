import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Product } from "../api";

export default function Discover() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<Product[]>([]);

  useEffect(() => {
    const t = setTimeout(() => {
      api.products(q).then((d) => setItems(d.items)).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div>
      <div className="row">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search products" />
      </div>
      <div className="grid">
        {items.map((p) => (
          <Link key={p.id} className="card" to={`/products/${p.id}`}>
            <div>{p.title}</div>
            <div className="muted">{p.category || "uncategorised"}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
