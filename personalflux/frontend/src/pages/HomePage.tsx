import { Link } from "react-router-dom";
import { RecommendationList } from "../components/RecommendationList";
import { ProductCard } from "../components/ProductCard";
import { CardSkeletons, EmptyState, ErrorState } from "../components/States";
import { useAuth } from "../features/auth/AuthContext";
import { useTracking } from "../features/tracking/useTracking";
import { useAsync } from "../hooks/useAsync";
import { customerApi, productsApi, recsApi } from "../lib/endpoints";
import type { RecommendationResponse } from "../lib/types";

const STRATEGY_TEXT: Record<string, string> = {
  personalized_hybrid: "Based on what you are looking at now and your earlier activity.",
  session_based: "Based on what you have looked at in this session.",
  history_based: "Based on your earlier activity.",
};

function strategyNote(data: RecommendationResponse, canTrack: boolean): string | null {
  if (STRATEGY_TEXT[data.strategy]) return STRATEGY_TEXT[data.strategy];
  if (data.fallback_used) {
    return canTrack
      ? "Popular picks for now. Look around and this list will adapt to you."
      : "Popular picks. Allow personalisation in Settings to get recommendations that adapt to what you look at.";
  }
  return null;
}

export default function HomePage() {
  const { user } = useAuth();
  const { canTrack } = useTracking();

  const feed = useAsync((s) => recsApi.home({ limit: 12 }, s), [user?.id, canTrack]);
  const trending = useAsync((s) => recsApi.trending({ limit: 8 }, s), []);
  const categories = useAsync((s) => productsApi.categories(s), []);
  const recent = useAsync(
    (s) => (user ? customerApi.history(8, s) : Promise.resolve([])),
    [user?.id],
  );

  return (
    <div className="space-y-10">
      <section aria-labelledby="for-you">
        <h1 id="for-you" className="text-2xl font-bold">Recommended for you</h1>
        {feed.data && (
          <p className="mt-1 text-sm text-slate-400" data-testid="strategy-note">
            {strategyNote(feed.data, canTrack)}
          </p>
        )}
        <div className="mt-4">
          {feed.loading && <CardSkeletons count={8} />}
          {feed.error && <ErrorState error={feed.error} onRetry={feed.reload} />}
          {feed.data &&
            (feed.data.recommendations.length === 0 ? (
              <EmptyState title="No recommendations right now">
                Try <Link className="text-violet-300 underline" to="/discover">browsing the catalog</Link>.
              </EmptyState>
            ) : (
              <RecommendationList
                data={feed.data}
                onDismiss={(id) =>
                  feed.setData((prev) => ({
                    ...prev,
                    recommendations: prev.recommendations.filter((r) => r.product_id !== id),
                  }))
                }
              />
            ))}
        </div>
      </section>

      {categories.data && categories.data.length > 0 && (
        <section aria-labelledby="cats">
          <h2 id="cats" className="text-lg font-semibold">Browse by category</h2>
          <ul className="mt-3 flex flex-wrap gap-2">
            {categories.data.slice(0, 14).map((c) => (
              <li key={c.category}>
                <Link
                  to={`/discover?category=${encodeURIComponent(c.category)}`}
                  className="rounded-full border border-slate-700 px-3 py-1 text-sm hover:border-violet-400"
                >
                  {c.category} <span className="text-slate-500">({c.products})</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {user && recent.data && recent.data.length > 0 && (
        <section aria-labelledby="recent">
          <h2 id="recent" className="text-lg font-semibold">Recently viewed</h2>
          <ul className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {recent.data.map((v) => (
              <li key={v.product.id}><ProductCard product={v.product} /></li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="trending">
        <h2 id="trending" className="text-lg font-semibold">Trending</h2>
        <div className="mt-3">
          {trending.loading && <CardSkeletons count={4} />}
          {trending.error && <ErrorState error={trending.error} onRetry={trending.reload} />}
          {trending.data && <RecommendationList data={trending.data} />}
        </div>
      </section>
    </div>
  );
}
