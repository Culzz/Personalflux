import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookmarkX } from "lucide-react";
import { api, isLoggedIn, type Product } from "../api";
import ProductCard, { SkeletonGrid } from "../components/ProductCard";
import EmptyState from "../components/EmptyState";

export default function Saved() {
  const [items, setItems] = useState<Product[] | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) { setItems([]); return; }
    api.saved().then((d) => setItems(d.map((s: { product: Product }) => s.product))).catch(() => setItems([]));
  }, []);

  if (items === null) return <SkeletonGrid n={3} />;

  if (!isLoggedIn() || items.length === 0) {
    return (
      <div>
        <div className="hero"><h1>Saved</h1></div>
        <EmptyState
          icon={<BookmarkX size={28} />}
          title="No saved items"
          hint={isLoggedIn() ? "Tap save on a product and it will wait for you here." : "Login first — saved items sync to your account."}
          action={<Link to={isLoggedIn() ? "/discover" : "/auth"}><button>{isLoggedIn() ? "Discover" : "Login"}</button></Link>}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="hero"><h1>Saved</h1><p>{items.length} items you kept.</p></div>
      <div className="grid">
        {items.map((p) => <ProductCard key={p.id} p={p} />)}
      </div>
    </div>
  );
}
