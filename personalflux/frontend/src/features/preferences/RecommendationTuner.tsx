import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../../lib/api";
import { customerApi } from "../../lib/endpoints";
import type { Product } from "../../lib/types";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../toast/ToastContext";

type Direction = "more" | "less";

/**
 * "More like this" / "Show me less like this", straight from a product.
 *
 * These write a stated (explicit) preference for the product's category, so the
 * dashboard can show them apart from anything inferred from behaviour, and a
 * reset clears them like any other preference.
 */
export function RecommendationTuner({ product }: { product: Product }) {
  const { user } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [busy, setBusy] = useState<Direction | null>(null);
  const category: string = product.category ?? "";
  if (!category) return null;

  async function nudge(direction: Direction) {
    if (!user) {
      notify("Sign in to tune your recommendations.", {
        action: {
          label: "Sign in",
          onClick: () => navigate("/login", { state: { from: location.pathname + location.search } }),
        },
      });
      return;
    }
    setBusy(direction);
    try {
      // Read then write, because the API replaces the whole list.
      const current = await customerApi.preferences();
      const liked = new Set(current.explicit.liked_categories ?? []);
      const blocked = new Set(current.explicit.blocked_categories ?? []);
      if (direction === "more") {
        liked.add(category);
        blocked.delete(category);        // a category cannot be both
      } else {
        blocked.add(category);
        liked.delete(category);
      }
      await customerApi.updatePreferences({
        liked_categories: [...liked],
        blocked_categories: [...blocked],
      });
      notify(direction === "more"
        ? `Got it — more from ${category}. Saved as a stated preference.`
        : `Got it — less from ${category}. Saved as a stated preference.`);
    } catch (err) {
      notify(err instanceof ApiError ? err.message : "Could not update your recommendations.",
             { tone: "error" });
    } finally {
      setBusy(null);
    }
  }

  const base = "rounded-md border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-60";
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" disabled={busy !== null} onClick={() => nudge("more")} className={base}>
        More like this
      </button>
      <button type="button" disabled={busy !== null} onClick={() => nudge("less")} className={base}>
        Show me less like this
      </button>
    </div>
  );
}
