import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { customerApi, recsApi } from "../../lib/endpoints";
import type { Product } from "../../lib/types";
import { useAuth } from "../auth/AuthContext";
import { useTracking } from "../tracking/useTracking";

interface SavedValue {
  isSaved: (productId: string) => boolean;
  /** Saves or unsaves. Pass a requestId when the product came from a recommendation. */
  toggle: (product: Product, requestId?: string | null) => Promise<void>;
}

const Ctx = createContext<SavedValue | null>(null);

export function SavedProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { canTrack } = useTracking();
  const [ids, setIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!user) {
      setIds(new Set());
      return;
    }
    let alive = true;
    customerApi
      .saved()
      .then((rows) => alive && setIds(new Set(rows.map((r) => r.product.id))))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [user]);

  const toggle = useCallback(
    async (product: Product, requestId?: string | null) => {
      const currentlySaved = ids.has(product.id);
      if (currentlySaved) {
        await customerApi.unsave(product.id);
      } else if (requestId && canTrack) {
        await recsApi.feedback({ product_id: product.id, feedback: "save", request_id: requestId });
      } else {
        await customerApi.save(product.id);
      }
      setIds((prev) => {
        const next = new Set(prev);
        if (currentlySaved) next.delete(product.id);
        else next.add(product.id);
        return next;
      });
    },
    [ids, canTrack],
  );

  const value = useMemo(() => ({ isSaved: (id: string) => ids.has(id), toggle }), [ids, toggle]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSaved(): SavedValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSaved must be used inside SavedProvider");
  return v;
}
