import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { useConsent } from "../features/consent/ConsentContext";
import { useConsentActions } from "../features/tracking/useConsentActions";
import { ApiError } from "../lib/api";
import { customerApi } from "../lib/endpoints";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const { consent } = useConsent();
  const { allow, deny } = useConsentActions();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!user) return null;
  const on = consent === "granted" && user.tracking_consent;

  async function download() {
    const data = await customerApi.exportData();
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "personaflux-my-data.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function remove() {
    if (!window.confirm("Delete your account and everything linked to it? This cannot be undone.")) return;
    setBusy(true);
    setError(null);
    try {
      await customerApi.deleteAccount(password);
      await logout();
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete the account.");
      setBusy(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-10">
      <h1 className="text-2xl font-bold">Account and privacy</h1>
      <section aria-labelledby="acct" className="space-y-1">
        <h2 id="acct" className="text-lg font-semibold">Account</h2>
        <p className="text-sm text-slate-300">Signed in as {user.email}</p>
      </section>

      <section aria-labelledby="track" className="space-y-3">
        <h2 id="track" className="text-lg font-semibold">Personalisation</h2>
        <p className="text-sm text-slate-300">
          Personalisation is <strong>{on ? "on" : "off"}</strong>.{" "}
          {on
            ? "PersonaFlux records which products you view, click, save, and buy, so recommendations can adapt. It never records what you type in search."
            : "Nothing about your browsing is recorded, and recommendations are generic popular picks."}
        </p>
        <button
          onClick={() => void (on ? deny() : allow())}
          className="rounded-md bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700"
        >
          {on ? "Turn personalisation off" : "Turn personalisation on"}
        </button>
      </section>

      <section aria-labelledby="data" className="space-y-3">
        <h2 id="data" className="text-lg font-semibold">Your data</h2>
        <button onClick={() => void download()} className="rounded-md bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700">
          Download my data
        </button>
      </section>

      <section aria-labelledby="danger" className="space-y-3 rounded-xl border border-red-900 p-4">
        <h2 id="danger" className="text-lg font-semibold text-red-200">Delete account</h2>
        <p className="text-sm text-slate-300">
          This permanently removes your account, history, saved items, preferences and sessions.
        </p>
        <label htmlFor="pw" className="block text-sm">Confirm with your password</label>
        <input id="pw" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full max-w-xs rounded-md border border-slate-700 bg-slate-900 px-3 py-2" />
        {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
        <button disabled={!password || busy} onClick={() => void remove()} className="rounded-md bg-red-700 px-4 py-2 text-sm font-medium text-white enabled:hover:bg-red-600 disabled:opacity-50">
          Delete my account
        </button>
      </section>
    </div>
  );
}
