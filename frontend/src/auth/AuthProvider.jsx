import { useCallback, useEffect, useMemo, useState } from "react";

import { AuthContext } from "./authContext";
import { loginUser, registerUser } from "../services/api";
import { configureAuthentication } from "../services/httpClient";


const TOKEN_STORAGE_KEY = "token";


function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}


function AuthProvider({ children }) {
  const [token, setToken] = useState(getStoredToken);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
  }, []);

  useEffect(() => {
    configureAuthentication({
      token,
      onUnauthorized: logout,
    });

    return () => {
      configureAuthentication({
        token: null,
        onUnauthorized: null,
      });
    };
  }, [logout, token]);

  const login = useCallback(async (email, password) => {
    const data = await loginUser(email, password);

    localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
    setToken(data.access_token);

    return data;
  }, []);

  const register = useCallback((user) => registerUser(user), []);

  const value = useMemo(
    () => ({
      isAuthenticated: Boolean(token),
      login,
      logout,
      register,
    }),
    [login, logout, register, token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
