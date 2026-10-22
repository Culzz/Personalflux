import { useCallback, useRef } from "react";
import { eventsApi, recsApi } from "../../lib/endpoints";
import type { EventType } from "../../lib/types";
import { useAuth } from "../auth/AuthContext";
import { useConsent } from "../consent/ConsentContext";

/**
 * Nothing is sent unless the visitor allowed personalisation (and, when signed in,
 * their account setting is on). The server enforces the account setting as well.
 */
export function useTracking() {
  const { user } = useAuth();
  const { consent } = useConsent();
  const canTrack = consent === "granted" && (!user || user.tracking_consent);
  const sentImpressions = useRef(new Set<string>());

  const track = useCallback(
    (
      event_type: EventType,
      product_id?: string,
      context?: Record<string, string | number | boolean>,
      idempotency_key?: string,
    ) => {
      if (!canTrack) return;
      void eventsApi.send({ event_type, product_id, context, idempotency_key }).catch(() => undefined);
    },
    [canTrack],
  );

  /** Reports items that were actually displayed. Safe to call repeatedly: a
   *  `request_id:product_id` pair is only ever sent once. */
  const recordImpressions = useCallback(
    (
      requestId: string | null,
      modelVersion: string | null,
      items: { product_id: string; position: number }[],
    ) => {
      if (!canTrack || !requestId || items.length === 0) return;
      const fresh = items.filter((it) => !sentImpressions.current.has(`${requestId}:${it.product_id}`));
      if (fresh.length === 0) return;
      fresh.forEach((it) => sentImpressions.current.add(`${requestId}:${it.product_id}`));
      void recsApi
        .impressions({ request_id: requestId, model_version: modelVersion, items: fresh })
        .catch(() =>
          // Let a failed report be retried on the next visibility change rather
          // than silently losing the impression.
          fresh.forEach((it) => sentImpressions.current.delete(`${requestId}:${it.product_id}`)),
        );
    },
    [canTrack],
  );

  return { canTrack, track, recordImpressions };
}
