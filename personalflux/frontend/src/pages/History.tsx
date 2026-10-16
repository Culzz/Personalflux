import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { History } from "lucide-react";
import { api, isLoggedIn, type Product } from "../api";
import ProductCard, { SkeletonGrid } from "../components/ProductCard";
import EmptyState from "../components/EmptyState";

export default function HistoryPage() {
  const [items, setItems] = useState<{ product: Product }[] | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) { setItems([]); return; }
    api.history().then((d) => setItems(d as { product: Product }[])).catch(() => setItems([]));
  }, []);

  if (items === null) return <SkeletonGrid n={3} />;

  return (
    <div>
      <div className="hero">
        <h1><History size={20} style={{ verticalAlign: -3 }} /> Recently viewed</h1>
        <p>What you looked at lately. This is the recent-intent signal.</p>
      </div>
      {items.length === 0 ? (
        <EmptyState
          icon={<History size={28} />}
          title="No recent views"
          hint={isLoggedIn() ? "Products you open will show up here." : "Login to keep history across devices."}
          action={<Link to="/discover"><button>Browse catalog</button></Link>}
        />
      ) : (
        <div className="grid">
          {items.map((h, i) => <ProductCard key={h.product.id + i} p={h.product} />)}
        </div>
      )}
    </div>
  );
}
