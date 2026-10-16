import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { refreshSession, setAccessToken, setAuthLostHandler } from "../../lib/api";
import { authApi } from "../../lib/endpoints";
import { hasSessionFlag, readConsent, setSessionFlag } from "../../lib/storage";
import type { TokenResponse, User } from "../../lib/types";
import { useConsent } from "../consent/ConsentContext";

export type AuthStatus = "loading" | "anonymous" | "authenticated";

interface AuthValue {
  status: AuthStatus;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
}

const Ctx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { setConsent } = useConsent();
  const [state, setState] = useState<{ status: AuthStatus; user: User | null }>({
    status: hasSessionFlag() ? "loading" : "anonymous",
    user: null,
  });

  const adopt = useCallback(
    (res: TokenResponse) => {
      setAccessToken(res.access_token);
      setSessionFlag(true);
      if (res.user.tracking_consent) setConsent("granted");
      setState({ status: "authenticated", user: res.user });
    },
    [setConsent],
  );

  const drop = useCallback(() => {
    setAccessToken(null);
    setSessionFlag(false);
    setState({ status: "anonymous", user: null });
  }, []);

  useEffect(() => {
    setAuthLostHandler(drop);
    if (!hasSessionFlag()) return () => setAuthLostHandler(null);
    let alive = true;
    refreshSession().then((res) => {
      if (!alive) return;
      if (res) adopt(res);
      else drop();
    });
    return () => {
      alive = false;
      setAuthLostHandler(null);
    };
  }, [adopt, drop]);

  const login = useCallback(
    async (email: string, password: string) => adopt(await authApi.login(email, password)),
    [adopt],
  );

  const register = useCallback(
    async (email: string, password: string) =>
      adopt(await authApi.register(email, password, readConsent() === "granted")),
    [adopt],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      /* the local session is cleared either way */
    }
    drop();
  }, [drop]);

  const updateUser = useCallback((user: User) => setState((s) => ({ ...s, user })), []);

  const value = useMemo(
    () => ({ ...state, login, register, logout, updateUser }),
    [state, login, register, logout, updateUser],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
