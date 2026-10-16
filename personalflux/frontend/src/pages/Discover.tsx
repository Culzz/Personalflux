import { useEffect, useState } from "react";
import { SearchX } from "lucide-react";
import { api, type Product } from "../api";
import ProductCard, { SkeletonGrid } from "../components/ProductCard";
import EmptyState from "../components/EmptyState";

export default function Discover() {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [cats, setCats] = useState<{ category: string; products: number }[]>([]);
  const [items, setItems] = useState<Product[] | null>(null);

  useEffect(() => { api.categories().then(setCats).catch(() => {}); }, []);

  useEffect(() => {
    setItems(null);
    const t = setTimeout(() => {
      api.products(q).then((d) => {
        const list = cat ? d.items.filter((p) => p.category === cat) : d.items;
        setItems(list);
      }).catch(() => setItems([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q, cat]);

  return (
    <div className="layout">
      <aside className="side">
        <h4>Categories</h4>
        <label>
          <input type="radio" name="cat" checked={cat === ""} onChange={() => setCat("")} />
          All
        </label>
        {cats.map((c) => (
          <label key={c.category}>
            <input type="radio" name="cat" checked={cat === c.category} onChange={() => setCat(c.category)} />
            {c.category} ({c.products})
          </label>
        ))}
      </aside>
      <div>
        <div className="hero">
          <h1>Discover</h1>
          <p>Search the catalog. Views feed back into your recommendations.</p>
        </div>
        <div className="row">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search products" />
        </div>
        {!items ? <SkeletonGrid /> :
          items.length === 0 ? (
            <EmptyState
              icon={<SearchX size={28} />}
              title="No matches"
              hint="Try a shorter search or a different category."
            />
          ) : (
            <div className="grid">
              {items.map((p) => <ProductCard key={p.id} p={p} />)}
            </div>
          )}
      </div>
    </div>
  );
}
