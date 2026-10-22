import {
  createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode,
} from "react";
import type { Product } from "../../lib/types";

export const COMPARE_MAX = 4;
const KEY = "pf_compare";

/** Just enough to draw the compare bar without re-fetching the products. */
export interface CompareEntry {
  id: string;
  title: string;
  image_url: string | null;
}

interface CompareValue {
  entries: CompareEntry[];
  ids: string[];
  has: (id: string) => boolean;
  /** Adds or removes. Returns false when the list is full and the item is new. */
  toggle: (product: Product) => boolean;
  remove: (id: string) => void;
  clear: () => void;
}

const Ctx = createContext<CompareValue | null>(null);

function read(): CompareEntry[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.slice(0, COMPARE_MAX) : [];
  } catch {
    return [];
  }
}

/** Which products the visitor wants side by side. Kept in this browser only. */
export function CompareProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<CompareEntry[]>(read);

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(entries));
    } catch {
      /* private mode: the list just does not survive a reload */
    }
  }, [entries]);

  const has = useCallback((id: string) => entries.some((e) => e.id === id), [entries]);

  const toggle = useCallback((product: Product) => {
    const exists = entries.some((e) => e.id === product.id);
    if (!exists && entries.length >= COMPARE_MAX) return false;
    setEntries((prev) =>
      exists
        ? prev.filter((e) => e.id !== product.id)
        : [...prev, { id: product.id, title: product.title, image_url: product.image_url }],
    );
    return true;
  }, [entries]);

  const remove = useCallback((id: string) => setEntries((p) => p.filter((e) => e.id !== id)), []);
  const clear = useCallback(() => setEntries([]), []);

  const value = useMemo<CompareValue>(() => ({
    entries, ids: entries.map((e) => e.id), has, toggle, remove, clear,
  }), [entries, has, toggle, remove, clear]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCompare(): CompareValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useCompare must be used inside CompareProvider");
  return v;
}
