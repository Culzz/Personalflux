import { useEffect } from "react";
import { useTracking } from "../features/tracking/useTracking";
import { useVisibleItems } from "../features/tracking/useVisibleItems";
import { recsApi } from "../lib/endpoints";
import type { RecommendationResponse } from "../lib/types";
import { ProductCard } from "./ProductCard";
import { SaveButton } from "./SaveButton";

interface Props {
  data: RecommendationResponse;
  /** Called after "Not interested" so the parent can remove the card. */
  onDismiss?: (productId: string) => void;
}

/** Renders recommendations, reports impressions and clicks, and handles save and dismiss. */
export function RecommendationList({ data, onDismiss }: Props) {
  const { canTrack, track, recordImpressions } = useTracking();
  const items = data.recommendations.map((r, i) => ({ product_id: r.product_id, position: i + 1 }));
  const ids = items.map((i) => i.product_id);
  const visible = useVisibleItems(ids);
  const visibleKey = visible.join(",");

  // Only the cards a person could actually see count as impressions.
  useEffect(() => {
    const positionOf = new Map(items.map((i) => [i.product_id, i.position]));
    const shown = visible
      .map((id) => ({ product_id: id, position: positionOf.get(id) ?? 1 }))
      .sort((a, b) => a.position - b.position);
    recordImpressions(data.request_id, data.model_version, shown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.request_id, data.model_version, visibleKey, recordImpressions]);

  async function dismiss(productId: string) {
    onDismiss?.(productId); // hide immediately
    if (!canTrack) return;
    try {
      await recsApi.feedback({ product_id: productId, feedback: "dismiss", request_id: data.request_id });
    } catch {
      /* the card is already hidden; a failed report only affects future feeds */
    }
  }

  return (
    <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {data.recommendations.map((r, i) => (
        <li key={r.product_id} data-impression-for={r.product_id}>
          <ProductCard
            product={r.product}
            explanation={r.explanation}
            reasons={r.reason_codes}
            onOpen={() =>
              track("click", r.product_id, {
                source: "recommendation",
                // The click names the request, position and model version that
                // produced it, so it can be attributed rather than just counted.
                ...(data.request_id ? { request_id: data.request_id } : {}),
                ...(data.model_version ? { model_version: data.model_version } : {}),
                position: i + 1,
              })
            }
            actions={
              <>
                <SaveButton product={r.product} requestId={data.request_id} />
                {onDismiss && (
                  <button
                    onClick={() => dismiss(r.product_id)}
                    className="rounded-md bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
                  >
                    Not interested
                    <span className="sr-only"> in {r.product.title}</span>
                  </button>
                )}
              </>
            }
          />
        </li>
      ))}
    </ul>
  );
}
