import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { useSaved } from "../features/saved/SavedContext";
import type { Product } from "../lib/types";

interface Props {
  product: Product;
  requestId?: string | null;
}

export function SaveButton({ product, requestId }: Props) {
  const { user } = useAuth();
  const { isSaved, toggle } = useSaved();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const saved = isSaved(product.id);

  async function onClick() {
    if (!user) {
      navigate("/login", { state: { from: location.pathname + location.search } });
      return;
    }
    setError(null);
    try {
      await toggle(product, requestId);
    } catch {
      setError("Could not update saved items.");
    }
  }

  return (
    <>
      <button
        onClick={onClick}
        aria-pressed={saved}
        className={`rounded-md px-3 py-1.5 text-xs font-medium ${
          saved ? "bg-violet-600 text-white" : "bg-slate-800 text-slate-100 hover:bg-slate-700"
        }`}
      >
        {saved ? "Saved" : "Save"}
        <span className="sr-only"> {product.title}</span>
      </button>
      {error && (
        <span role="alert" className="text-xs text-red-300">
          {error}
        </span>
      )}
    </>
  );
}
