import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  getMe,
  loginAccount,
  registerAccount,
  getToken,
  setToken,
  clearToken,
} from "../services/api";
import { useToast } from "../components/ui/Toast";

const AuthContext = createContext(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const { showError } = useToast();
  const [user, setUser] = useState(null);
  // True only while a stored token is being validated on first load, so pages
  // can show a skeleton instead of briefly flashing the logged-out state.
  const [isLoading, setIsLoading] = useState(Boolean(getToken()));

  useEffect(() => {
    if (!getToken()) return;
    getMe()
      .then(setUser)
      .catch((err) => {
        // Only a 401 means the token is bad. A network error (backend down)
        // must NOT silently log the user out — keep the token and retry later.
        if (err.status === 401) clearToken();
      })
      .finally(() => setIsLoading(false));
  }, []);

  // api.js dispatches this when a token-bearing request comes back 401.
  useEffect(() => {
    const onExpired = () => {
      clearToken();
      setUser(null);
      queryClient.clear();
      showError("Your session has expired. Please log in again.");
    };
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, [queryClient, showError]);

  const completeAuth = useCallback(
    (data) => {
      setToken(data.access_token);
      // Drop EVERYTHING cached from the previous identity before the new one
      // renders — otherwise a prior user's history could briefly appear.
      queryClient.clear();
      setUser(data.user);
      return data.user;
    },
    [queryClient]
  );

  const login = useCallback(async (email, password) => completeAuth(await loginAccount(email, password)), [completeAuth]);
  const register = useCallback(async (email, password) => completeAuth(await registerAccount(email, password)), [completeAuth]);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo(
    () => ({ user, isAuthenticated: Boolean(user), isLoading, login, register, logout }),
    [user, isLoading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
