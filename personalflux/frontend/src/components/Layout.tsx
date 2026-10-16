import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { useCart } from "../features/cart/CartContext";
import { ConsentBanner } from "./ConsentBanner";
import { PageLoading } from "./States";

const link = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm ${isActive ? "bg-slate-800 text-white" : "text-slate-300 hover:text-white"}`;

export function Layout() {
  const { status, user, logout } = useAuth();
  const { items } = useCart();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-violet-600 focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header className="border-b border-slate-800 bg-slate-950/90">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to="/" className="text-lg font-bold tracking-tight">
            Persona<span className="text-violet-400">Flux</span>
          </Link>
          <nav aria-label="Main" className="flex flex-wrap items-center gap-1">
            <NavLink to="/" end className={link}>Home</NavLink>
            <NavLink to="/discover" className={link}>Discover</NavLink>
            <NavLink to="/saved" className={link}>Saved</NavLink>
            <NavLink to="/cart" className={link}>
              Cart{items.length > 0 && <span className="ml-1 rounded-full bg-violet-600 px-1.5 text-xs">{items.length}</span>}
            </NavLink>
          </nav>
          <div className="flex items-center gap-2 text-sm">
            {status === "authenticated" && user ? (
              <details className="relative">
                <summary className="cursor-pointer rounded-md px-3 py-1.5 hover:bg-slate-800">{user.email}</summary>
                <div className="absolute right-0 z-40 mt-1 flex w-48 flex-col rounded-lg border border-slate-700 bg-slate-900 p-1">
                  <Link className="rounded px-3 py-2 hover:bg-slate-800" to="/preferences">Preferences</Link>
                  <Link className="rounded px-3 py-2 hover:bg-slate-800" to="/history">History</Link>
                  <Link className="rounded px-3 py-2 hover:bg-slate-800" to="/settings">Settings</Link>
                  <button
                    className="rounded px-3 py-2 text-left hover:bg-slate-800"
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
                <Link to="/login" className="rounded-md px-3 py-1.5 hover:bg-slate-800">Sign in</Link>
                <Link to="/register" className="rounded-md bg-violet-600 px-3 py-1.5 font-medium text-white hover:bg-violet-500">
                  Create account
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        {status === "loading" ? <PageLoading /> : <Outlet />}
      </main>
      <footer className="border-t border-slate-800 px-4 py-4 text-center text-xs text-slate-500">
        PersonaFlux is a portfolio project using the public Retailrocket dataset. There are no real products,
        prices or payments.
      </footer>
      <ConsentBanner />
    </div>
  );
}
