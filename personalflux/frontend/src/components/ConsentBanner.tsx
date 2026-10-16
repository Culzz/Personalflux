import { Link } from "react-router-dom";
import { useConsent } from "../features/consent/ConsentContext";
import { useConsentActions } from "../features/tracking/useConsentActions";

export function ConsentBanner() {
  const { consent } = useConsent();
  const { allow, deny } = useConsentActions();
  if (consent !== null) return null;
  return (
    <section
      aria-label="Privacy choices"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-slate-700 bg-slate-900 p-4 shadow-xl"
    >
      <div className="mx-auto flex max-w-5xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-200">
          Allow PersonaFlux to remember what you look at, so recommendations can adapt? We store product
          views and clicks, never what you type in search. You can change this any time in{" "}
          <Link to="/settings" className="text-violet-300 underline">
            Settings
          </Link>
          .
        </p>
        <div className="flex shrink-0 gap-2">
          <button onClick={() => void deny()} className="rounded-md bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700">
            No thanks
          </button>
          <button onClick={() => void allow()} className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500">
            Allow
          </button>
        </div>
      </div>
    </section>
  );
}
