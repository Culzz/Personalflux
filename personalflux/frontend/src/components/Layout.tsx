import { Bookmark, Compass, Home, ShoppingCart, User } from "lucide-react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { useCart } from "../features/cart/CartContext";
import { CompareBar } from "./CompareBar";
import { ConsentBanner } from "./ConsentBanner";
import { PageLoading } from "./States";

const link = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm ${isActive ? "bg-ink text-paper" : "text-slate-500 hover:text-slate-100"}`;

const tab = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : "");

export function Layout() {
  const { status, user, logout } = useAuth();
  const { items } = useCart();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-violet-600 focus:px-3 focus:py-2 focus:text-white">
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to="/" className="font-display text-xl tracking-tight">
            Persona<span className="text-brass">Flux</span>
          </Link>
          <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
            <NavLink to="/" end className={link}>Home</NavLink>
            <NavLink to="/discover" className={link}>Discover</NavLink>
            <NavLink to="/saved" className={link}>Saved</NavLink>
            <NavLink to="/cart" className={link}>
              Cart{items.length > 0 && <span className="ml-1 rounded-full bg-violet-600 px-1.5 text-xs text-white">{items.length}</span>}
            </NavLink>
            <NavLink to="/business" className={link}>Business</NavLink>
            {user && ["analyst", "ml_engineer", "admin"].includes(user.role) && (
              <NavLink to="/ml" className={link}>ML</NavLink>
            )}
            {user?.role === "admin" && (
              <NavLink to="/admin" className={link}>Admin</NavLink>
            )}
          </nav>
          <div className="flex items-center gap-2 text-sm">
            {status === "authenticated" && user ? (
              <details className="relative">
                <summary className="cursor-pointer rounded-md px-3 py-2 hover:bg-slate-800">{user.email}</summary>
                <div className="absolute right-0 z-40 mt-1 flex w-48 flex-col rounded-lg border border-slate-700 bg-slate-900 p-1 shadow-lg">
                  <Link className="rounded px-3 py-2.5 hover:bg-slate-800" to="/preferences">Preferences</Link>
                  <Link className="rounded px-3 py-2.5 hover:bg-slate-800" to="/history">History</Link>
                  <Link className="rounded px-3 py-2.5 hover:bg-slate-800" to="/settings">Settings</Link>
                  <Link className="rounded px-3 py-2.5 hover:bg-slate-800" to="/business">Business</Link>
                  {["analyst", "ml_engineer", "admin"].includes(user.role) && (
                    <Link className="rounded px-3 py-2.5 hover:bg-slate-800" to="/ml">ML console</Link>
                  )}
                  {user.role === "admin" && (
                    <Link className="rounded px-3 py-2.5 hover:bg-slate-800" to="/admin">Admin</Link>
                  )}
                  <button
                    className="rounded px-3 py-2.5 text-left hover:bg-slate-800"
                    onClick={async () => {
                      await logout();
                      navigate("/");
                    }}
                  >
                    Sign out
                  </button>
                </div>
              </details>
            ) : (
              <>
                <Link to="/login" className="rounded-md px-3 py-2 hover:bg-slate-800">Sign in</Link>
                <Link to="/register" className="rounded-md bg-violet-600 px-3 py-2 font-medium text-white hover:bg-violet-500">
                  Create account
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 pb-28 md:pb-6">
        {status === "loading" ? <PageLoading /> : <Outlet />}
      </main>
      <nav aria-label="Sections" className="tabbar md:hidden">
        <NavLink to="/" end className={tab}><Home size={22} />Home</NavLink>
        <NavLink to="/discover" className={tab}><Compass size={22} />Discover</NavLink>
        <NavLink to="/saved" className={tab}><Bookmark size={22} />Saved</NavLink>
        <NavLink to="/cart" className={tab}><ShoppingCart size={22} />Cart</NavLink>
        <NavLink to="/login" className={tab}><User size={22} />Account</NavLink>
      </nav>
      <footer className="border-t border-slate-800 px-4 py-4 text-center text-xs text-slate-500">
        <Link to="/about" className="underline hover:text-slate-300">About PersonaFlux</Link>
        {" · "}A portfolio project with a demo catalog. There are no real products, prices or payments.
      </footer>
      <CompareBar />
      <ConsentBanner />
    </div>
  );
}
