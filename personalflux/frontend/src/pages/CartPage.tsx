import { useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/States";
import { useCart } from "../features/cart/CartContext";
import { useTracking } from "../features/tracking/useTracking";
import { formatPrice } from "../lib/format";

export default function CartPage() {
  const cart = useCart();
  const { canTrack, track } = useTracking();
  const [ordered, setOrdered] = useState<number | null>(null);

  function placeOrder() {
    const n = cart.items.length;
    for (const item of cart.items) track("purchase", item.id, { source: "demo_checkout" });
    cart.clear();
    setOrdered(n);
  }

  if (cart.items.length === 0) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Cart</h1>
        {ordered !== null && (
          <p role="status" className="rounded-lg border border-violet-700 bg-violet-950/40 p-4 text-sm">
            Demo order placed for {ordered} item{ordered === 1 ? "" : "s"}. Nothing was charged.
            {canTrack
              ? " Purchased items will no longer be recommended to you."
              : " Personalisation is off, so this purchase was not recorded."}
          </p>
        )}
        <EmptyState title="Your cart is empty">
          <Link to="/discover" className="text-violet-300 underline">Find something to add</Link>
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Cart</h1>
      <p className="text-sm text-slate-400">This is a demo cart. There is no payment and no real order.</p>
      <ul className="divide-y divide-slate-800 rounded-xl border border-slate-800">
        {cart.items.map((i) => (
          <li key={i.id} className="flex items-center justify-between gap-4 p-4">
            <div>
              <Link to={`/products/${i.id}`} className="font-medium hover:underline">{i.title}</Link>
              <p className="text-sm text-slate-400">{formatPrice(i.price)}</p>
            </div>
            <button onClick={() => cart.remove(i.id)} className="rounded-md bg-slate-800 px-3 py-1.5 text-sm hover:bg-slate-700">
              Remove<span className="sr-only"> {i.title}</span>
            </button>
          </li>
        ))}
      </ul>
      <button onClick={placeOrder} className="rounded-md bg-violet-600 px-4 py-2 font-medium text-white hover:bg-violet-500">
        Place demo order
      </button>
    </div>
  );
}
