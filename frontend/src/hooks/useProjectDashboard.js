import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchProjectDashboard } from "../services/api";
import { formatLocalDateForApi } from "../utils/date";


function currentDate() {
  return new Date();
}


function isAbortError(error) {
  return error?.name === "AbortError";
}


function useProjectDashboard({
  projectId,
  onError,
  dateFactory = currentDate,
}) {
  const [retryVersion, setRetryVersion] = useState(0);
  const [state, setState] = useState({
    dashboard: null,
    loadedIdentity: null,
    error: null,
    errorIdentity: null,
    isLoading: false,
  });
  const asOf = useMemo(
    () => {
      const requestIdentity = `${projectId ?? "none"}:${retryVersion}`;
      return requestIdentity && formatLocalDateForApi(dateFactory());
    },
    [dateFactory, projectId, retryVersion]
  );
  const identityKey = projectId ? `${projectId}:${asOf}` : null;

  const identityRef = useRef(identityKey);
  const onErrorRef = useRef(onError);
  const requestRef = useRef(null);
  const abortTimerRef = useRef(null);

  useEffect(() => {
    identityRef.current = identityKey;
  }, [identityKey]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const startRequest = useCallback(() => {
    if (!identityKey) return Promise.resolve(null);

    const existingRequest = requestRef.current;
    if (
      existingRequest?.identityKey === identityKey &&
      !existingRequest.settled
    ) {
      return existingRequest.promise;
    }

    if (existingRequest && !existingRequest.settled) {
      existingRequest.controller.abort();
    }

    const controller = new AbortController();
    const requestRecord = {
      controller,
      identityKey,
      promise: null,
      settled: false,
    };

    setState({
      dashboard: null,
      loadedIdentity: null,
      error: null,
      errorIdentity: null,
      isLoading: true,
    });

    const promise = fetchProjectDashboard(projectId, asOf, {
      signal: controller.signal,
    })
      .then((dashboard) => {
        if (identityRef.current !== identityKey) return null;

        setState({
          dashboard,
          loadedIdentity: identityKey,
          error: null,
          errorIdentity: null,
          isLoading: false,
        });
        return dashboard;
      })
      .catch((error) => {
        if (isAbortError(error) || identityRef.current !== identityKey) {
          return null;
        }

        setState({
          dashboard: null,
          loadedIdentity: null,
          error,
          errorIdentity: identityKey,
          isLoading: false,
        });
        onErrorRef.current?.("Unable to load project dashboard", error);
        return null;
      })
      .finally(() => {
        requestRecord.settled = true;
      });

    requestRecord.promise = promise;
    requestRef.current = requestRecord;
    return promise;
  }, [asOf, identityKey, projectId]);

  useEffect(() => {
    if (abortTimerRef.current) {
      window.clearTimeout(abortTimerRef.current);
      abortTimerRef.current = null;
    }

    const currentRequest = requestRef.current;
    if (
      currentRequest &&
      !currentRequest.settled &&
      currentRequest.identityKey !== identityKey
    ) {
      currentRequest.controller.abort();
    }

    if (!identityKey) return undefined;

    let requestAtSetup = null;
    const startTimer = window.setTimeout(() => {
      void startRequest();
      requestAtSetup = requestRef.current;
    }, 0);

    return () => {
      window.clearTimeout(startTimer);
      abortTimerRef.current = window.setTimeout(() => {
        if (
          requestAtSetup &&
          requestRef.current === requestAtSetup &&
          !requestAtSetup.settled
        ) {
          requestAtSetup.controller.abort();
        }
      }, 0);
    };
  }, [identityKey, retryVersion, startRequest]);

  useEffect(
    () => () => {
      requestRef.current?.controller.abort();
    },
    []
  );

  const retry = useCallback(() => {
    setRetryVersion((version) => version + 1);
  }, []);

  return {
    dashboard:
      state.loadedIdentity === identityKey ? state.dashboard : null,
    isLoading: Boolean(
      identityKey &&
        state.errorIdentity !== identityKey &&
        (state.isLoading || state.loadedIdentity !== identityKey)
    ),
    error: state.errorIdentity === identityKey ? state.error : null,
    retry,
    asOf,
  };
}

export default useProjectDashboard;
