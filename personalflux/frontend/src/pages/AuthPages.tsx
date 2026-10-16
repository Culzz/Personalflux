import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { useConsent } from "../features/consent/ConsentContext";
import { ApiError } from "../lib/api";

function useRedirect() {
  const location = useLocation();
  const navigate = useNavigate();
  const from = (location.state as { from?: string } | null)?.from ?? "/";
  return () => navigate(from, { replace: true });
}

function message(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "validation_error") return "Please check the email and password (at least 10 characters).";
    return err.message;
  }
  return "Something went wrong. Please try again.";
}

const input = "w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2";

export function LoginPage() {
  const { login } = useAuth();
  const done = useRedirect();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      done();
    } catch (err) {
      setError(message(err));
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm space-y-4">
      <h1 className="text-2xl font-bold">Sign in</h1>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label htmlFor="email" className="mb-1 block text-sm">Email</label>
          <input id="email" type="email" autoComplete="email" required className={input} value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label htmlFor="password" className="mb-1 block text-sm">Password</label>
          <input id="password" type="password" autoComplete="current-password" required className={input} value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
        <button disabled={busy} className="w-full rounded-md bg-violet-600 px-4 py-2 font-medium text-white hover:bg-violet-500 disabled:opacity-60">
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="text-sm text-slate-400">
        New here? <Link to="/register" className="text-violet-300 underline">Create an account</Link>
      </p>
    </div>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const { consent, setConsent } = useConsent();
  const done = useRedirect();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [allow, setAllow] = useState(consent === "granted");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setConsent(allow ? "granted" : "denied"); // stored first: registration reads it
    try {
      await register(email, password);
      done();
    } catch (err) {
      setError(message(err));
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm space-y-4">
      <h1 className="text-2xl font-bold">Create your account</h1>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label htmlFor="email" className="mb-1 block text-sm">Email</label>
          <input id="email" type="email" autoComplete="email" required className={input} value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label htmlFor="password" className="mb-1 block text-sm">Password</label>
          <input id="password" type="password" autoComplete="new-password" required minLength={10} className={input} value={password} onChange={(e) => setPassword(e.target.value)} aria-describedby="pw-hint" />
          <p id="pw-hint" className="mt-1 text-xs text-slate-400">At least 10 characters.</p>
        </div>
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" checked={allow} onChange={(e) => setAllow(e.target.checked)} className="mt-1" />
          <span>Let PersonaFlux remember what I look at so recommendations can adapt to me. I can turn this off in Settings.</span>
        </label>
        {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
        <button disabled={busy} className="w-full rounded-md bg-violet-600 px-4 py-2 font-medium text-white hover:bg-violet-500 disabled:opacity-60">
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="text-sm text-slate-400">
        Already have an account? <Link to="/login" className="text-violet-300 underline">Sign in</Link>
      </p>
    </div>
  );
}
