import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode,
} from "react";

export interface ToastAction {
  label: string;
  onClick: () => void | Promise<void>;
}

interface Toast {
  id: number;
  message: string;
  action?: ToastAction;
  tone: "info" | "error";
}

interface ToastValue {
  /** Shows a short message. Pass an action to offer an undo. */
  notify: (message: string, opts?: { action?: ToastAction; tone?: "info" | "error" }) => void;
}

const Ctx = createContext<ToastValue | null>(null);
const LIFETIME_MS = 6000;

/** Small toast stack. Toasts auto-dismiss, and any timer is cleared on unmount. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const notify = useCallback<ToastValue["notify"]>((message, opts) => {
    const id = nextId.current++;
    setToasts((prev) => [...prev, { id, message, action: opts?.action, tone: opts?.tone ?? "info" }]);
    timers.current.set(id, setTimeout(() => dismiss(id), LIFETIME_MS));
  }, [dismiss]);

  useEffect(() => {
    const pending = timers.current;
    return () => {
      pending.forEach(clearTimeout);
      pending.clear();
    };
  }, []);

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <Ctx.Provider value={value}>
      {children}
      {toasts.length > 0 && (
        <div role="status" aria-live="polite" className="toasts">
          {toasts.map((t) => (
            <div key={t.id} className={`toast ${t.tone === "error" ? "toast-error" : ""}`}>
              <span className="toast-message">{t.message}</span>
              {t.action && (
                <button
                  type="button"
                  className="toast-action"
                  onClick={() => {
                    void Promise.resolve(t.action!.onClick()).finally(() => dismiss(t.id));
                  }}
                >
                  {t.action.label}
                </button>
              )}
              <button type="button" aria-label="Dismiss" className="toast-close" onClick={() => dismiss(t.id)}>
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </Ctx.Provider>
  );
}

export function useToast(): ToastValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useToast must be used inside ToastProvider");
  return v;
}
