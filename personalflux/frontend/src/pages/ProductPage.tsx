import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type Product, type RecResponse } from "../api";
import ProductCard, { imageFor } from "../components/ProductCard";

export default function ProductPage() {
  const { id } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [similar, setSimilar] = useState<RecResponse | null>(null);

  useEffect(() => {
    if (!id) return;
    api.product(id).then(setProduct).catch(() => {});
    api.similar(id).then(setSimilar).catch(() => {});
    api.event(id, "view");
  }, [id]);

  if (!product) return <p className="muted">Loading...</p>;

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
            <button onClick={() => id && api.event(id, "save")}>Save</button>
            <button className="ghost" onClick={() => id && api.event(id, "dismiss")}>
              Dismiss
            </button>
          </div>
        </div>
      </div>
      <h3 style={{ marginTop: 28 }}>Often looked at together</h3>
      <div className="grid">
        {(similar?.recommendations || []).map((r) => (
          <ProductCard key={r.product_id} p={r.product} reason={r.explanation} />
        ))}
      </div>
    </div>
  );
}
