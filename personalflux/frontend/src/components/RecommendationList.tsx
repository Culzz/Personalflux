import { useEffect } from "react";
import { useTracking } from "../features/tracking/useTracking";
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
  const ids = data.recommendations.map((r) => r.product_id).join(",");

  useEffect(() => {
    recordImpressions(
      data.request_id,
      data.model_version,
      data.recommendations.map((r) => r.product_id),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.request_id, ids, recordImpressions]);

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
      {data.recommendations.map((r) => (
        <li key={r.product_id}>
          <ProductCard
            product={r.product}
            explanation={r.explanation}
            reasons={r.reason_codes}
            onOpen={() =>
              track("click", r.product_id, {
                source: "recommendation",
                ...(data.request_id ? { request_id: data.request_id } : {}),
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
