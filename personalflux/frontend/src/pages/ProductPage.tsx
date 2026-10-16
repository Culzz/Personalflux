import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type Product, type RecResponse } from "../api";

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

  if (!product) return <p>Loading...</p>;

  return (
    <div>
      <h2>{product.title}</h2>
      <p className="muted">{product.category || "uncategorised"}</p>
      <h3>Similar</h3>
      <div className="grid">
        {(similar?.recommendations || []).map((r) => (
          <div key={r.product_id} className="card">
            <div>{r.product.title}</div>
            <div className="muted">{r.explanation}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
