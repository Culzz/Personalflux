import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode,
} from "react";
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

  // A mirror so toggle always reads the latest state, even from a callback
  // captured before a re-render (for example the toast's undo action).
  const idsRef = useRef(ids);
  useEffect(() => {
    idsRef.current = ids;
  }, [ids]);

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
      const currentlySaved = idsRef.current.has(product.id);
      // Optimistic: flip the button straight away, then roll back if the server rejects it.
      const flip = (saved: boolean) =>
        setIds((prev) => {
          const next = new Set(prev);
          if (saved) next.add(product.id);
          else next.delete(product.id);
          return next;
        });
      flip(!currentlySaved);
      try {
        if (currentlySaved) {
          await customerApi.unsave(product.id);
        } else if (requestId && canTrack) {
          await recsApi.feedback({ product_id: product.id, feedback: "save", request_id: requestId });
        } else {
          await customerApi.save(product.id);
        }
      } catch (err) {
        flip(currentlySaved);   // undo the optimistic change
        throw err;
      }
    },
    [canTrack],
  );

  const value = useMemo(() => ({ isSaved: (id: string) => ids.has(id), toggle }), [ids, toggle]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSaved(): SavedValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSaved must be used inside SavedProvider");
  return v;
}
