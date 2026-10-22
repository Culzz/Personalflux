interface Props {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, totalPages, onChange }: Props) {
  if (totalPages <= 1) return null;
  return (
    <nav aria-label="Pagination" className="mt-6 flex items-center justify-center gap-3 text-sm">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="rounded-md bg-slate-800 px-3 py-1.5 enabled:hover:bg-slate-700 disabled:opacity-40"
      >
        Previous
      </button>
      <span aria-live="polite">
        Page {page} of {totalPages}
      </span>
      <button
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        className="rounded-md bg-slate-800 px-3 py-1.5 enabled:hover:bg-slate-700 disabled:opacity-40"
      >
        Next
      </button>
    </nav>
  );
}
