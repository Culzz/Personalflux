import { useEffect, useState } from "react";
import { Bookmark, BookmarkCheck } from "lucide-react";
import { useParams } from "react-router-dom";
import { api, isLoggedIn, type Product, type RecResponse } from "../api";
import ProductCard, { imageFor } from "../components/ProductCard";
import { toast } from "../App";

export default function ProductPage() {
  const { id } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [similar, setSimilar] = useState<RecResponse | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!id) return;
    api.product(id).then(setProduct).catch(() => {});
    api.similar(id).then(setSimilar).catch(() => {});
    api.event(id, "view");
  }, [id]);

  if (!product) return <p className="muted">Loading...</p>;

  async function toggleSave() {
    if (!id) return;
    if (!isLoggedIn()) { toast("Login to save items"); return; }
    if (saved) {
      setSaved(false);
      await api.unsave(id);
      toast("Removed from saved");
    } else {
      setSaved(true);
      await api.save(id);
      toast("Saved");
    }
  }

  return (
    <div>
      <div className="detail">
        <img src={imageFor(product)} alt={product.title} />
        <div>
          {product.category && <span className="tag">{product.category}</span>}
          <h1>{product.title}</h1>
          {product.price && <p>${product.price}</p>}
          {product.description && <p className="muted">{product.description}</p>}
          <div className="row">
            <button onClick={toggleSave}>
              {saved ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}{" "}
              {saved ? "Saved" : "Save"}
            </button>
            <button className="ghost" onClick={() => id && api.event(id, "dismiss").then(() => toast("Dismissed — will show less like this"))}>
              Dismiss
            </button>
          </div>
        </div>
      </div>
      <h3 style={{ marginTop: 28 }}>Often looked at together</h3>
      <div className="grid">
        {(similar?.recommendations || []).map((r) => (
          <ProductCard key={r.product_id} p={r.product} reason={r.explanation} codes={r.reason_codes} />
        ))}
      </div>
    </div>
  );
}
