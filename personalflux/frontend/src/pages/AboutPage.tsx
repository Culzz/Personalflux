import { Link } from "react-router-dom";

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-3xl font-bold">About PersonaFlux</h1>
      <p className="text-slate-300">
        PersonaFlux is a storefront whose recommendations adapt to you. It keeps
        a long-term picture of what you like, and lets what you are looking at
        right now change the ranking without wiping that history.
      </p>
      <h2 className="text-xl font-semibold">How it works</h2>
      <ul className="list-disc space-y-2 pl-6 text-sm text-slate-300">
        <li>Views, carts, saves and dismissals are recorded as events with your consent.</li>
        <li>A session model scores items similar to what you are browsing; a long-term blend adds your history.</li>
        <li>Every recommendation carries the reason it was shown, and new visitors get popular picks until a signal exists.</li>
        <li>Offline results live in the model card. The business dashboard shows live activity only.</li>
      </ul>
      <h2 className="text-xl font-semibold">The catalog</h2>
      <p className="text-sm text-slate-300">
        Browsing data comes from the public Retailrocket e-commerce sample, whose items have dataset
        identifiers rather than real names. A small curated showcase sits on top so search, filters
        and prices behave like a real shop. Prices on sample rows are stable demo prices, not retail prices.
      </p>
      <div className="flex gap-2">
        <Link to="/discover" className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
          Browse the catalog
        </Link>
        <Link to="/register" className="rounded-md bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700">
          Create an account
        </Link>
      </div>
    </div>
  );
}
