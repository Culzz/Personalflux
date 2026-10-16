import { useEffect, useState } from "react";
import { api, type Product } from "../api";
import ProductCard from "../components/ProductCard";

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
      <div className="hero">
        <h1>Discover</h1>
        <p>Search the catalog. Views feed back into your recommendations.</p>
      </div>
      <div className="row">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search products" />
      </div>
      <div className="grid">
        {items.map((p) => (
          <ProductCard key={p.id} p={p} />
        ))}
      </div>
    </div>
  );
}
