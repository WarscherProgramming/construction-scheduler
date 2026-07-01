import { useCallback, useMemo, useState } from "react";

import { AuthContext } from "./authContext";
import { loginUser, registerUser } from "../services/api";
import { configureAuthentication } from "../services/httpClient";


const TOKEN_STORAGE_KEY = "token";


function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}


function AuthProvider({ children }) {
  const [token, setToken] = useState(getStoredToken);
  const [sessionExpired, setSessionExpired] = useState(false);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setSessionExpired(false);
    setToken(null);
  }, []);

  // Triggered by the transport on a 401. Only treat it as an expired session
  // when a token was actually present — a failed login attempt also returns
  // 401 but must not surface a "session expired" message.
  const handleSessionExpiry = useCallback(() => {
    if (localStorage.getItem(TOKEN_STORAGE_KEY)) {
      setSessionExpired(true);
    }

    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
  }, []);

  // Configure the transport before children render so their first request
  // includes a token restored from localStorage.
  configureAuthentication({
    token,
    onUnauthorized: handleSessionExpiry,
  });

  const login = useCallback(async (email, password) => {
    const data = await loginUser(email, password);

    localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
    setSessionExpired(false);
    setToken(data.access_token);

    return data;
  }, []);

  const register = useCallback((user) => registerUser(user), []);

  const acknowledgeSessionExpiry = useCallback(() => {
    setSessionExpired(false);
  }, []);

  const value = useMemo(
    () => ({
      isAuthenticated: Boolean(token),
      sessionExpired,
      login,
      logout,
      register,
      acknowledgeSessionExpiry,
    }),
    [acknowledgeSessionExpiry, login, logout, register, sessionExpired, token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
