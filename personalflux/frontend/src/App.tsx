import { Suspense, lazy, useEffect, useState } from "react";
import { Bookmark, Compass, Home as HomeIcon, User } from "lucide-react";
import { Link, BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { SkeletonGrid } from "./components/ProductCard";

const Home = lazy(() => import("./pages/Home"));
const Discover = lazy(() => import("./pages/Discover"));
const ProductPage = lazy(() => import("./pages/ProductPage"));
const Auth = lazy(() => import("./pages/Auth"));
const Saved = lazy(() => import("./pages/Saved"));
const Prefs = lazy(() => import("./pages/Preferences"));
const HistoryPage = lazy(() => import("./pages/History"));
const Business = lazy(() => import("./pages/Business"));

export function toast(msg: string) {
  window.dispatchEvent(new CustomEvent("toast", { detail: msg }));
}

export default function App() {
  const [msg, setMsg] = useState("");

  useEffect(() => {
    const fn = (e: Event) => {
      setMsg((e as CustomEvent).detail);
      setTimeout(() => setMsg(""), 2200);
    };
    window.addEventListener("toast", fn);
    return () => window.removeEventListener("toast", fn);
  }, []);

  return (
    <BrowserRouter>
      <div className="topbar">
        <Link to="/" className="brand">
          PersonaFlux<small>ADAPTIVE SHOP</small>
        </Link>
        <div className="links">
          <NavLink to="/">For you</NavLink>
          <NavLink to="/discover">Discover</NavLink>
          <NavLink to="/saved">Saved</NavLink>
          <NavLink to="/business">Business</NavLink>
          <NavLink to="/auth">Account</NavLink>
        </div>
      </div>
      <main>
        <Suspense fallback={<SkeletonGrid />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/discover" element={<Discover />} />
            <Route path="/products/:id" element={<ProductPage />} />
            <Route path="/auth" element={<Auth />} />
            <Route path="/login" element={<Auth />} />
            <Route path="/saved" element={<Saved />} />
            <Route path="/preferences" element={<Prefs />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/business" element={<Business />} />
          </Routes>
        </Suspense>
      </main>
      <nav className="tabbar">
        <NavLink to="/" className={({ isActive }) => (isActive ? "active" : "")}>
          <HomeIcon size={22} />For you
        </NavLink>
        <NavLink to="/discover" className={({ isActive }) => (isActive ? "active" : "")}>
          <Compass size={22} />Discover
        </NavLink>
        <NavLink to="/saved" className={({ isActive }) => (isActive ? "active" : "")}>
          <Bookmark size={22} />Saved
        </NavLink>
        <NavLink to="/auth" className={({ isActive }) => (isActive ? "active" : "")}>
          <User size={22} />Account
        </NavLink>
      </nav>
      {msg && <div className="toast">{msg}</div>}
    </BrowserRouter>
  );
}
