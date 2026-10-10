import { useEffect, useState } from "react";

type Health = { status: string; service: string };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/health")
      .then((res) => res.json())
      .then(setHealth)
      .catch(() => setError("Backend not reachable"));
  }, []);

  return (
    <main style={{ padding: 32, fontFamily: "sans-serif" }}>
      <h1>PersonaFlux</h1>
      <p>
        Backend:{" "}
        {error ? error : health ? `${health.status} (${health.service})` : "checking..."}
      </p>
    </main>
  );
}