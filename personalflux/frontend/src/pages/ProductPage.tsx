import { useEffect, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import { ProductCard } from "../components/ProductCard";
import { ProductImage } from "../components/ProductImage";
import { RecommendationList } from "../components/RecommendationList";
import { SaveButton } from "../components/SaveButton";
import { CardSkeletons, EmptyState, ErrorState, PageLoading } from "../components/States";
import { useCart } from "../features/cart/CartContext";
import { useTracking } from "../features/tracking/useTracking";
import { useAsync } from "../hooks/useAsync";
import { ApiError } from "../lib/api";
import { productsApi, recsApi } from "../lib/endpoints";
import { formatPrice, newKey } from "../lib/format";

export default function ProductPage() {
  const { id = "" } = useParams();
  const { canTrack, track } = useTracking();
  const cart = useCart();

  const product = useAsync((s) => productsApi.get(id, s), [id]);
  const similar = useAsync((s) => recsApi.similar(id, 8, s), [id]);
  const related = useAsync((s) => productsApi.related(id, s), [id]);

  // One view event per visit, even if React re-runs the effect (the key lets the server de-duplicate).
  const viewKey = useRef<{ id: string; key: string } | null>(null);
  useEffect(() => {
    if (!id || !canTrack) return;
    if (viewKey.current?.id !== id) viewKey.current = { id, key: newKey("view") };
    track("view", id, undefined, viewKey.current.key);
  }, [id, canTrack, track]);

  if (product.loading) return <PageLoading />;
  if (product.error) {
    if (product.error instanceof ApiError && product.error.status === 404) {
      return (
        <EmptyState title="Product not found">
          It may have been removed. <Link className="text-violet-300 underline" to="/discover">Back to Discover</Link>
        </EmptyState>
      );
    }
    return <ErrorState error={product.error} onRetry={product.reload} />;
  }
  const p = product.data;
  if (!p) return null;
  const inCart = cart.items.some((i) => i.id === p.id);

  return (
    <div className="space-y-10">
      <div className="grid gap-8 md:grid-cols-2">
        <ProductImage title={p.title} category={p.category} imageUrl={p.image_url} />
        <div className="space-y-4">
          {p.category && <p className="text-sm text-violet-300">{p.category}</p>}
          <h1 className="text-2xl font-bold">{p.title}</h1>
          <p className="text-xl">{formatPrice(p.price)}</p>
          {p.description && <p className="text-slate-300">{p.description}</p>}
          <p className="text-xs text-slate-500">
            {p.is_active ? "In stock and ready to ship." : "Currently unavailable."}
          </p>
          {!p.description && !p.image_url && (
            <p className="text-xs text-slate-500">
              This one comes from the public Retailrocket dataset, which ships without photos or
              descriptions, so it shows as a placeholder tile.
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <button
              disabled={inCart}
              onClick={() => {
                cart.add(p);
                track("add_to_cart", p.id, { source: "product_page" });
              }}
              className="rounded-md bg-violet-600 px-4 py-2 font-medium text-white enabled:hover:bg-violet-500 disabled:opacity-60"
            >
              {inCart ? "In cart" : "Add to cart"}
            </button>
            <SaveButton product={p} />
          </div>
        </div>
      </div>

      <section aria-labelledby="similar">
        <h2 id="similar" className="text-lg font-semibold">Similar items</h2>
        <div className="mt-3">
          {similar.loading && <CardSkeletons count={4} />}
          {similar.error && <ErrorState error={similar.error} onRetry={similar.reload} />}
          {similar.data &&
            (similar.data.recommendations.length === 0
              ? <EmptyState title="No similar items yet" />
              : <RecommendationList data={similar.data} />)}
        </div>
      </section>

      {related.data && related.data.length > 0 && (
        <section aria-labelledby="related">
          <h2 id="related" className="text-lg font-semibold">More in {p.category}</h2>
          <ul className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {related.data.map((r) => (
              <li key={r.id}><ProductCard product={r} /></li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
