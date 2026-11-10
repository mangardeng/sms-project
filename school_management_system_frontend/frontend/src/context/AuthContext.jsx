import { createContext, useCallback, useContext, useEffect, useState } from "react";

import * as authApi from "../api/auth";
import { tokenStore } from "../api/client";
import { dashboardPathFor } from "../utils/roles";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);

  const loadCurrentUser = useCallback(async () => {
    if (!tokenStore.getAccess()) {
      setUser(null);
      setInitializing(false);
      return;
    }
    try {
      const me = await authApi.fetchMe();
      setUser(me);
    } catch {
      tokenStore.clear();
      setUser(null);
    } finally {
      setInitializing(false);
    }
  }, []);

  useEffect(() => {
    loadCurrentUser();

    function handleExpired() {
      setUser(null);
    }
    window.addEventListener("sms:session-expired", handleExpired);
    return () => window.removeEventListener("sms:session-expired", handleExpired);
  }, [loadCurrentUser]);

  const login = useCallback(async (identifier, password) => {
    const data = await authApi.login(identifier, password);
    setUser(data.user);
    return data.dashboard || dashboardPathFor(data.user.role);
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout().catch(() => {});
    setUser(null);
  }, []);

  const refreshProfile = useCallback(async () => {
    const me = await authApi.fetchMe();
    setUser(me);
    return me;
  }, []);

  const value = {
    user,
    isAuthenticated: !!user,
    initializing,
    login,
    logout,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider.");
  return ctx;
}
