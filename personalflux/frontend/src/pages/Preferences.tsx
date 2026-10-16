import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RotateCcw, SlidersHorizontal } from "lucide-react";
import { api, isLoggedIn, type Prefs } from "../api";
import { toast } from "../App";

export default function Preferences() {
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [liked, setLiked] = useState("");
  const [blocked, setBlocked] = useState("");

  useEffect(() => {
    if (isLoggedIn()) api.prefs().then(setPrefs).catch(() => {});
  }, []);

  if (!isLoggedIn()) {
    return (
      <div style={{ maxWidth: 420 }}>
        <h1>Preferences</h1>
        <p className="muted">Login to manage stated preferences and reset inferred ones.</p>
        <div className="row"><Link to="/auth"><button>Login</button></Link></div>
      </div>
    );
  }
  if (!prefs) return <p className="muted">Loading preferences...</p>;

  const likedList = (prefs.explicit.liked_categories as string[] | undefined) || [];
  const blockedList = (prefs.explicit.blocked_categories as string[] | undefined) || [];

  async function save() {
    const body: Record<string, unknown> = {};
    if (liked.trim()) body.liked_categories = [...likedList, ...liked.split(",").map((s) => s.trim()).filter(Boolean)];
    if (blocked.trim()) body.blocked_categories = [...blockedList, ...blocked.split(",").map((s) => s.trim()).filter(Boolean)];
    const next = await api.updatePrefs(body);
    setPrefs(next);
    setLiked(""); setBlocked("");
    toast("Preferences saved");
  }

  async function reset() {
    const next = await api.resetPrefs();
    setPrefs(next);
    toast("Inferred profile reset");
  }

  return (
    <div style={{ maxWidth: 640 }}>
      <h1><SlidersHorizontal size={20} style={{ verticalAlign: -3 }} /> Preferences</h1>
      <p className="muted">Stated likes steer ranking. Recent browsing adapts it without erasing long-term taste.</p>
      <h3>You said you like</h3>
      <p className="muted">{likedList.length ? likedList.join(", ") : "Nothing stated yet."}</p>
      <h3>Blocked</h3>
      <p className="muted">{blockedList.length ? blockedList.join(", ") : "Nothing blocked."}</p>
      <div className="row">
        <input value={liked} onChange={(e) => setLiked(e.target.value)} placeholder="Add liked categories, comma separated" />
      </div>
      <div className="row">
        <input value={blocked} onChange={(e) => setBlocked(e.target.value)} placeholder="Add blocked categories, comma separated" />
      </div>
      <div className="row">
        <button onClick={save}>Save</button>
        <button className="ghost" onClick={reset}><RotateCcw size={15} /> Reset inferred</button>
      </div>
      <h3>What we inferred</h3>
      <p className="muted">
        Long-term: {prefs.inferred.long_term_categories.slice(0, 3).map((c) => c.category).join(", ") || "—"} ·
        Recent: {prefs.inferred.recent_categories.slice(0, 3).map((c) => c.category).join(", ") || "—"} ·
        {prefs.inferred.events_considered} events
      </p>
    </div>
  );
}
