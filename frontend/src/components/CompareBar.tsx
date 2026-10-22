import { X } from "lucide-react";
import { Link } from "react-router-dom";
import { COMPARE_MAX, useCompare } from "../features/compare/CompareContext";

/** A slim bar above the mobile tab bar, shown while anything is queued to compare. */
export function CompareBar() {
  const { entries, remove, clear } = useCompare();
  if (entries.length === 0) return null;

  return (
    <div className="fixed inset-x-0 bottom-14 z-30 border-t border-slate-800 bg-slate-900/95 px-3 py-2 md:bottom-0">
      <div className="mx-auto flex max-w-6xl items-center gap-3">
        <ul className="flex flex-1 gap-2 overflow-x-auto">
          {entries.map((e) => (
            <li key={e.id} className="flex shrink-0 items-center gap-2 rounded-lg border border-slate-700 px-2 py-1 text-xs">
              {e.image_url && <img src={e.image_url} alt="" className="h-8 w-8 rounded object-cover" />}
              <span className="max-w-[9rem] truncate">{e.title}</span>
              <button type="button" aria-label={`Remove ${e.title} from comparison`} onClick={() => remove(e.id)}
                      className="text-slate-400 hover:text-slate-100">
                <X size={14} />
              </button>
            </li>
          ))}
        </ul>
        <span className="hidden text-xs text-slate-500 sm:inline">{entries.length}/{COMPARE_MAX}</span>
        <button type="button" onClick={clear} className="text-xs text-slate-400 hover:text-slate-100">Clear</button>
        {entries.length >= 2 ? (
          <Link to={`/compare?ids=${entries.map((e) => e.id).join(",")}`}
                className="rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500">
            Compare ({entries.length})
          </Link>
        ) : (
          <span className="text-xs text-slate-500">Pick one more</span>
        )}
      </div>
    </div>
  );
}
