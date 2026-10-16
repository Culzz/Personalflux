import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { formatPrice } from "../lib/format";
import type { Product } from "../lib/types";
import { ProductImage } from "./ProductImage";

interface Props {
  product: Product;
  explanation?: string;
  onOpen?: () => void;
  actions?: ReactNode;
}

export function ProductCard({ product, explanation, onOpen, actions }: Props) {
  const to = `/products/${product.id}`;
  return (
    <article className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <Link to={to} onClick={onOpen} tabIndex={-1} aria-hidden="true">
        <ProductImage title={product.title} category={product.category} imageUrl={product.image_url} />
      </Link>
      <div className="flex flex-1 flex-col gap-1">
        {product.category && <p className="text-xs text-violet-300">{product.category}</p>}
        <h3 className="text-sm font-semibold leading-snug">
          <Link to={to} onClick={onOpen} className="hover:underline">
            {product.title}
          </Link>
        </h3>
        <p className="text-sm text-slate-300">{formatPrice(product.price)}</p>
        {explanation && <p className="mt-1 text-xs text-slate-400">{explanation}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </article>
  );
}
