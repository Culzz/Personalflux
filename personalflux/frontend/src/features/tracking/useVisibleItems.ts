import { useEffect, useRef, useState } from "react";

/**
 * Which of a list of product ids have been on screen long enough to count as
 * *displayed*.
 *
 * An impression means "a person could have seen this", so a card is only counted
 * once at least half of it has been visible for a short dwell. That is stricter
 * than counting whatever the API returned, which is the mistake that makes a
 * click-through rate look better than it is.
 *
 * When `IntersectionObserver` is unavailable (jsdom in tests, very old browsers)
 * every item is treated as displayed: the honest fallback is that we cannot tell,
 * and over-counting is at least not silent.
 */
export function useVisibleItems(productIds: string[], dwellMs = 800): string[] {
  const [visible, setVisible] = useState<string[]>([]);
  const counted = useRef(new Set<string>());
  const key = productIds.join("|");

  useEffect(() => {
    if (productIds.length === 0) return;
    if (typeof IntersectionObserver === "undefined") {
      const fresh = productIds.filter((id) => !counted.current.has(id));
      fresh.forEach((id) => counted.current.add(id));
      if (fresh.length > 0) setVisible((v) => [...v, ...fresh]);
      return;
    }

    const timers = new Map<Element, number>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const id = (entry.target as HTMLElement).dataset.impressionFor;
          if (!id) continue;
          if (entry.isIntersecting) {
            if (counted.current.has(id) || timers.has(entry.target)) continue;
            timers.set(
              entry.target,
              window.setTimeout(() => {
                timers.delete(entry.target);
                if (!counted.current.has(id)) {
                  counted.current.add(id);
                  setVisible((v) => [...v, id]);
                }
              }, dwellMs),
            );
          } else {
            const timer = timers.get(entry.target);
            if (timer !== undefined) {
              window.clearTimeout(timer);
              timers.delete(entry.target);
            }
          }
        }
      },
      { threshold: 0.5 },
    );

    document.querySelectorAll<HTMLElement>("[data-impression-for]").forEach((el) => observer.observe(el));
    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
      observer.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, dwellMs]);

  return visible;
}
