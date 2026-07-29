import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { AuthContext } from "./authContext";
import { createSessionChannel } from "./sessionChannel";
import { loginUser, registerUser } from "../services/api";
import {
  adoptAuthentication,
  clearAuthentication,
  configureAuthentication,
  logoutAuthentication,
  prepareForLogin,
  restoreAuthentication,
} from "../services/httpClient";


const LEGACY_TOKEN_STORAGE_KEY = "token";


function removeLegacyTokens() {
  localStorage.removeItem(LEGACY_TOKEN_STORAGE_KEY);
  sessionStorage.removeItem(LEGACY_TOKEN_STORAGE_KEY);
}


function AuthProvider({ children }) {
  const [authStatus, setAuthStatus] = useState("initializing");
  const [user, setUser] = useState(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const statusRef = useRef(authStatus);
  const channelRef = useRef(null);

  useEffect(() => {
    statusRef.current = authStatus;
  }, [authStatus]);

  const becomeSignedOut = useCallback((expired = false) => {
    clearAuthentication();
    setUser(null);
    setSessionExpired(expired);
    setAuthStatus("unauthenticated");
  }, []);

  const handleSessionExpiry = useCallback(() => {
    const hadActiveSession = statusRef.current === "authenticated";
    becomeSignedOut(hadActiveSession);
    if (hadActiveSession) channelRef.current?.broadcast("session_expired");
  }, [becomeSignedOut]);

  useEffect(() => {
    configureAuthentication({
      onUnauthorized: handleSessionExpiry,
    });
    return () => configureAuthentication({ onUnauthorized: null });
  }, [handleSessionExpiry]);

  const restore = useCallback(async () => {
    setAuthStatus("initializing");
    try {
      const data = await restoreAuthentication();
      setUser(data.user);
      setSessionExpired(false);
      setAuthStatus("authenticated");
      return true;
    } catch (error) {
      clearAuthentication();
      setUser(null);
      if (error?.status === 0) {
        setAuthStatus("error");
      } else {
        setSessionExpired(false);
        setAuthStatus("unauthenticated");
      }
      return false;
    }
  }, []);

  useEffect(() => {
    removeLegacyTokens();
    const timeoutId = window.setTimeout(restore, 0);
    return () => window.clearTimeout(timeoutId);
  }, [restore]);

  useEffect(() => {
    const sessionChannel = createSessionChannel((event) => {
      if (event?.type === "logout") {
        becomeSignedOut(false);
      } else if (event?.type === "session_expired") {
        becomeSignedOut(true);
      } else if (
        event?.type === "session_restored" &&
        statusRef.current !== "authenticated"
      ) {
        restore();
      }
    });
    channelRef.current = sessionChannel;
    return () => {
      channelRef.current = null;
      sessionChannel.close();
    };
  }, [becomeSignedOut, restore]);

  const login = useCallback(async (email, password) => {
    await prepareForLogin();
    const data = adoptAuthentication(await loginUser(email, password));
    setUser(data.user);
    setSessionExpired(false);
    setAuthStatus("authenticated");
    channelRef.current?.broadcast("session_restored");
    return data;
  }, []);

  const logout = useCallback(async () => {
    clearAuthentication();
    setUser(null);
    setSessionExpired(false);
    setAuthStatus("signing_out");
    channelRef.current?.broadcast("logout");
    try {
      await logoutAuthentication();
    } catch {
      // Local logout remains authoritative when the API is unavailable.
    } finally {
      setAuthStatus("unauthenticated");
    }
  }, []);

  const register = useCallback((newUser) => registerUser(newUser), []);
  const acknowledgeSessionExpiry = useCallback(() => {
    setSessionExpired(false);
  }, []);

  const value = useMemo(
    () => ({
      authStatus,
      isAuthenticated: authStatus === "authenticated",
      user,
      sessionExpired,
      login,
      logout,
      register,
      retryStartup: restore,
      acknowledgeSessionExpiry,
    }),
    [
      acknowledgeSessionExpiry,
      authStatus,
      login,
      logout,
      register,
      restore,
      sessionExpired,
      user,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
