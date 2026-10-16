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

  /** Reports what was actually shown. Each recommendation request is reported once. */
  const recordImpressions = useCallback(
    (requestId: string | null, modelVersion: string | null, productIds: string[]) => {
      if (!canTrack || !requestId || productIds.length === 0) return;
      if (sentImpressions.current.has(requestId)) return;
      sentImpressions.current.add(requestId);
      void recsApi
        .impressions({
          request_id: requestId,
          model_version: modelVersion,
          items: productIds.map((product_id, i) => ({ product_id, position: i + 1 })),
        })
        .catch(() => undefined);
    },
    [canTrack],
  );

  return { canTrack, track, recordImpressions };
}
