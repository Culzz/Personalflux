import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { clearSessionId, readConsent, writeConsent, type ConsentValue } from "../../lib/storage";

interface ConsentValueCtx {
  consent: ConsentValue | null;
  setConsent: (v: ConsentValue) => void;
}

const Ctx = createContext<ConsentValueCtx | null>(null);

export function ConsentProvider({ children }: { children: ReactNode }) {
  const [consent, setState] = useState<ConsentValue | null>(() => readConsent());

  const setConsent = useCallback((v: ConsentValue) => {
    writeConsent(v);
    if (v === "denied") clearSessionId(); // no identifier is kept without permission
    setState(v);
  }, []);

  const value = useMemo(() => ({ consent, setConsent }), [consent, setConsent]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useConsent(): ConsentValueCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useConsent must be used inside ConsentProvider");
  return v;
}
