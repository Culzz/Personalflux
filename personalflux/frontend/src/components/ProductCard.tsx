import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { formatPrice } from "../lib/format";
import type { Product } from "../lib/types";
import { CompareButton } from "./CompareButton";
import { ProductImage } from "./ProductImage";

const REASON_LABELS: Record<string, string> = {
  similar_to_session_items: "Similar to what you viewed",
  similar_to_history: "From your earlier activity",
  item_similarity: "Often viewed together",
  popular: "Popular overall",
  popular_in_category: "Popular in this category",
  matches_stated_preference: "Matches a category you like",
  catalog_default: "Catalog pick",
};

interface Props {
  product: Product;
  explanation?: string;
  reasons?: string[];
  onOpen?: () => void;
  actions?: ReactNode;
}

export function ProductCard({ product, explanation, reasons, onOpen, actions }: Props) {
  const to = `/products/${product.id}`;
  return (
    <article className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900 p-3 shadow-sm">
      <Link to={to} onClick={onOpen} tabIndex={-1} aria-hidden="true">
        <ProductImage title={product.title} category={product.category} imageUrl={product.image_url} />
      </Link>
      <div className="flex flex-1 flex-col gap-1">
        {product.category && (
          <p className="text-[11px] font-semibold uppercase tracking-widest text-violet-300">{product.category}</p>
        )}
        {product.brand && <p className="text-[11px] text-slate-400">{product.brand}</p>}
        <h3 className="text-base font-medium leading-snug">
          <Link to={to} onClick={onOpen} className="hover:underline">
            {product.title}
          </Link>
        </h3>
        <p className="text-sm text-slate-300">{formatPrice(product.price, product.currency)}</p>
        {(reasons?.length ?? 0) > 0 && (
          <ul aria-label="Why this was recommended" className="mt-1 flex flex-wrap gap-1">
            {reasons!.slice(0, 3).map((c) => (
              <li key={c} className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-500">
                {REASON_LABELS[c] ?? c.replace(/_/g, " ")}
              </li>
            ))}
          </ul>
        )}
        {explanation && <p className="mt-1 text-xs text-slate-400">{explanation}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        {actions}
        <CompareButton product={product} />
      </div>
    </article>
  );
}
