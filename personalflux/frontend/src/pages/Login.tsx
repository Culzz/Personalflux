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
      setErr("Login failed");
    }
  }

  return (
    <form onSubmit={submit}>
      <h2>Login</h2>
      {err && <p>{err}</p>}
      <div className="row">
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
        />
        <button type="submit">Login</button>
      </div>
    </form>
  );
}
