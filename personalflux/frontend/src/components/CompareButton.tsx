import { useCompare } from "../features/compare/CompareContext";
import { useToast } from "../features/toast/ToastContext";
import type { Product } from "../lib/types";

/** Adds or removes one product from the side-by-side comparison. */
export function CompareButton({ product }: { product: Product }) {
  const { has, toggle } = useCompare();
  const { notify } = useToast();
  const active = has(product.id);

  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={() => {
        if (!active && !toggle(product)) {
          notify("You can compare up to four products at a time.");
        }
      }}
      className={`rounded-md px-3 py-1.5 text-xs font-medium ${
        active ? "bg-slate-700 text-white" : "bg-slate-800 text-slate-100 hover:bg-slate-700"
      }`}
    >
      {active ? "Comparing" : "Compare"}
      <span className="sr-only"> {product.title}</span>
    </button>
  );
}
