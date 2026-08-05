import { useCallback, useEffect, useRef, useState } from "react";

import { fetchScheduleHealth } from "../services/api";


function emptyState(projectId = null) {
  return { projectId, health: null, error: null, isLoading: false };
}


function useScheduleHealth({ projectId, enabled, onError }) {
  const [state, setState] = useState(() => emptyState(projectId));
  const projectRef = useRef(projectId);
  const requestRef = useRef(null);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const load = useCallback(async () => {
    const requestProjectId = projectRef.current;
    if (!enabled || !requestProjectId) return null;
    if (requestRef.current?.projectId === requestProjectId) {
      return requestRef.current.promise;
    }
    requestRef.current?.controller.abort();
    const controller = new AbortController();
    setState({ ...emptyState(requestProjectId), isLoading: true });
    const request = { projectId: requestProjectId, controller, promise: null };
    const promise = fetchScheduleHealth(requestProjectId, {
      signal: controller.signal,
    }).then((health) => {
      if (
        projectRef.current === requestProjectId &&
        requestRef.current === request &&
        !controller.signal.aborted
      ) {
        setState({ projectId: requestProjectId, health, error: null, isLoading: false });
      }
      return health;
    }).catch((error) => {
      if (
        error?.name !== "AbortError" &&
        projectRef.current === requestProjectId &&
        requestRef.current === request
      ) {
        setState({ projectId: requestProjectId, health: null, error, isLoading: false });
        onErrorRef.current?.("Unable to load schedule health", error);
      }
      return null;
    }).finally(() => {
      if (requestRef.current === request) requestRef.current = null;
    });
    request.promise = promise;
    requestRef.current = request;
    return promise;
  }, [enabled]);

  useEffect(() => {
    projectRef.current = projectId;
    requestRef.current?.controller.abort();
    requestRef.current = null;
    if (!enabled || !projectId) return undefined;
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [enabled, load, projectId]);

  useEffect(() => () => requestRef.current?.controller.abort(), []);

  const current = enabled && state.projectId === projectId
    ? state
    : emptyState(projectId);
  return { ...current, retry: load };
}


export default useScheduleHealth;
