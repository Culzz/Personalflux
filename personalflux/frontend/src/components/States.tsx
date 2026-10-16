import type { ReactNode } from "react";
import { ApiError } from "../lib/api";

export function CardSkeletons({ count = 8 }: { count?: number }) {
  return (
    <div role="status" aria-label="Loading" className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="animate-pulse rounded-xl border border-slate-800 bg-slate-900/60 p-3">
          <div className="aspect-square rounded-lg bg-slate-800" />
          <div className="mt-3 h-3 w-1/3 rounded bg-slate-800" />
          <div className="mt-2 h-4 w-3/4 rounded bg-slate-800" />
          <div className="mt-2 h-3 w-1/2 rounded bg-slate-800" />
        </div>
      ))}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  const api = error instanceof ApiError ? error : null;
  return (
    <div role="alert" className="rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm">
      <p className="font-medium text-red-200">{api?.message ?? "Something went wrong."}</p>
      {api?.requestId && <p className="mt-1 text-xs text-red-300/70">Reference: {api.requestId}</p>}
      {onRetry && (
        <button onClick={onRetry} className="mt-3 rounded-md bg-slate-800 px-3 py-1.5 hover:bg-slate-700">
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-700 p-8 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-2 text-sm text-slate-400">{children}</div>}
    </div>
  );
}

export function PageLoading() {
  return (
    <div role="status" aria-label="Loading" className="p-10 text-center text-slate-400">
      Loading…
    </div>
  );
}
