import { useState } from "react";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api, isLoggedIn } from "../api";
import { toast } from "../App";

export default function Auth() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  if (isLoggedIn()) {
    return (
      <div style={{ maxWidth: 420 }}>
        <h1>Account</h1>
        <p className="muted">You are signed in on this device.</p>
        <div className="row">
          <button className="ghost" onClick={() => nav("/saved")}>Saved</button>
          <button className="ghost" onClick={() => nav("/history")}>History</button>
          <button className="ghost" onClick={() => nav("/preferences")}>Preferences</button>
        </div>
        <div className="row">
          <button className="ghost" onClick={() => nav("/business")}>Business</button>
          <button className="ghost" onClick={() => { api.logout(); nav("/"); }}>
            Sign out
          </button>
        </div>
      </div>
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return setErr("Enter a valid email.");
    if (password.length < 8) return setErr("Password needs at least 8 characters.");
    setErr("");
    setBusy(true);
    try {
      if (mode === "login") await api.login(email, password);
      else await api.register(email, password);
      toast(mode === "login" ? "Welcome back" : "Account created");
      nav("/");
    } catch {
      setErr(mode === "login" ? "Login failed — check email and password." : "Could not create account — email may be taken.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} style={{ maxWidth: 420 }}>
      <h1>{mode === "login" ? "Welcome back" : "Create account"}</h1>
      <p className="muted">Sign in to sync saved items and preferences.</p>
      <div className="row">
        <button type="button" className={mode === "login" ? "" : "ghost"} onClick={() => setMode("login")}>
          Login
        </button>
        <button type="button" className={mode === "register" ? "" : "ghost"} onClick={() => setMode("register")}>
          Register
        </button>
      </div>
      {err && <p>{err}</p>}
      <div className="row" style={{ alignItems: "center" }}>
        <Mail size={18} />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" autoComplete="email" />
      </div>
      <div className="row" style={{ alignItems: "center" }}>
        <Lock size={18} />
        <input
          type={show ? "text" : "password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password (8+ characters)"
          autoComplete={mode === "login" ? "current-password" : "new-password"}
        />
        <button type="button" className="ghost" onClick={() => setShow(!show)} aria-label="show password">
          {show ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
      <div className="row">
        <button type="submit" disabled={busy}>{busy ? "Please wait..." : mode === "login" ? "Login" : "Create account"}</button>
      </div>
    </form>
  );
}
