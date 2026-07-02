import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../services/httpClient";

/**
 * Owns the toast/notice state and the reporting helpers, including the
 * session-expiry notice and 401 suppression (the auth flow shows a single
 * "session expired" message instead of stale per-request errors).
 */
function useNotifications({ sessionExpired, acknowledgeSessionExpiry }) {
  const [notice, setNotice] = useState(null);

  const showNotice = useCallback((type, message) => {
    setNotice({
      id: Date.now(),
      type,
      message,
    });
  }, []);

  const reportRequestError = useCallback(
    (context, error) => {
      const message =
        error instanceof ApiError
          ? error.message
          : "Unexpected application error";

      console.error(`${context}: ${message}`, error);

      // A 401 means the session ended; the auth flow surfaces a single
      // "session expired" message, so suppress these stale request errors.
      if (error instanceof ApiError && error.status === 401) {
        return;
      }

      showNotice("error", `${context}. ${message}`);
    },
    [showNotice]
  );

  const reportValidationError = useCallback(
    (message) => {
      showNotice("error", message);
    },
    [showNotice]
  );

  useEffect(() => {
    if (!sessionExpired) return undefined;

    const timeoutId = window.setTimeout(() => {
      // Replace any stale request errors with a single session-expiry notice.
      setNotice({
        id: Date.now(),
        type: "info",
        title: "Session expired",
        message: "Your session has expired. Please sign in again.",
      });
      acknowledgeSessionExpiry();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [sessionExpired, acknowledgeSessionExpiry]);

  return {
    notice,
    setNotice,
    showNotice,
    reportRequestError,
    reportValidationError,
  };
}

export default useNotifications;
