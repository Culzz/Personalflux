// A demo cart kept in this browser only. There is no payment and no real order:
// it exists so add-to-cart and purchase signals can be produced and tested end to end.
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { readCartRaw, writeCartRaw } from "../../lib/storage";
import type { Product } from "../../lib/types";

export interface CartItem {
  id: string;
  title: string;
  category: string | null;
  price: string | null;
}

interface CartValue {
  items: CartItem[];
  add: (product: Product) => void;
  remove: (id: string) => void;
  clear: () => void;
}

const Ctx = createContext<CartValue | null>(null);

function load(): CartItem[] {
  try {
    const parsed = JSON.parse(readCartRaw() ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(load);

  const commit = useCallback((next: CartItem[]) => {
    writeCartRaw(JSON.stringify(next));
    setItems(next);
  }, []);

  const add = useCallback(
    (p: Product) => {
      if (items.some((i) => i.id === p.id)) return;
      commit([...items, { id: p.id, title: p.title, category: p.category, price: p.price }]);
    },
    [items, commit],
  );
  const remove = useCallback((id: string) => commit(items.filter((i) => i.id !== id)), [items, commit]);
  const clear = useCallback(() => commit([]), [commit]);

  const value = useMemo(() => ({ items, add, remove, clear }), [items, add, remove, clear]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCart(): CartValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useCart must be used inside CartProvider");
  return v;
}
