import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.login(email, password);
      nav("/");
    } catch {
      setErr("Login failed — check email and password.");
    }
  }

  return (
    <form onSubmit={submit} style={{ maxWidth: 420 }}>
      <h1>Welcome back</h1>
      <p className="muted">Log in to sync your preferences across sessions.</p>
      {err && <p>{err}</p>}
      <div className="row">
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      </div>
      <div className="row">
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
        />
      </div>
      <div className="row">
        <button type="submit">Login</button>
      </div>
    </form>
  );
}
