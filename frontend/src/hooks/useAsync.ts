import { useCallback, useEffect, useState } from "react";

interface State<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
}

/** Runs an async loader whenever `deps` change. Stale and aborted responses are ignored. */
export function useAsync<T>(loader: (signal: AbortSignal) => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const ac = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    loader(ac.signal)
      .then((data) => {
        if (!ac.signal.aborted) setState({ data, error: null, loading: false });
      })
      .catch((error) => {
        if (!ac.signal.aborted) setState({ data: null, error, loading: false });
      });
    return () => ac.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  const setData = useCallback(
    (fn: (prev: T) => T) => setState((s) => (s.data === null ? s : { ...s, data: fn(s.data) })),
    [],
  );
  return { ...state, reload, setData };
}
