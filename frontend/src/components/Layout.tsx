import { NavLink, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";

function navClass({ isActive }: { isActive: boolean }) {
  return [
    "px-3 py-2 rounded-lg text-sm font-medium transition-colors",
    isActive ? "bg-accent/15 text-accent" : "text-slate-300 hover:bg-white/5",
  ].join(" ");
}

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-edge bg-ink/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">🛡️</span>
            <span className="font-semibold tracking-tight">
              ATO<span className="text-accent">Shield</span>
            </span>
          </div>
          <nav className="flex items-center gap-1">
            <NavLink to="/dashboard" className={navClass}>
              Dashboard
            </NavLink>
            <NavLink to="/simulation" className={navClass}>
              Simulation
            </NavLink>
            <NavLink to="/about" className={navClass}>
              About
            </NavLink>
          </nav>
          <div className="flex items-center gap-3 text-sm">
            {user ? (
              <>
                <span className="text-slate-400">
                  {user.username}
                  <span className="ml-1 rounded bg-white/5 px-1.5 py-0.5 text-xs text-slate-500">
                    {user.role}
                  </span>
                </span>
                <button
                  onClick={async () => {
                    await logout();
                    navigate("/login");
                  }}
                  className="rounded-lg border border-edge px-3 py-1.5 text-slate-300 hover:bg-white/5"
                >
                  Logout
                </button>
              </>
            ) : (
              <NavLink to="/login" className={navClass}>
                Login
              </NavLink>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}
