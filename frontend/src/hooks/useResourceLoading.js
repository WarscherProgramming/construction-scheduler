import { useCallback, useEffect, useRef, useState } from "react";

import { fetchResourceLoading } from "../services/api";


function initialState(projectId = null) {
  return { projectId, data: null, error: null, isLoading: false, filters: {} };
}

function useResourceLoading({ projectId, enabled, reportRequestError }) {
  const [state, setState] = useState(() => initialState(projectId));
  const projectRef = useRef(projectId);
  const mountedRef = useRef(true);
  const requestRef = useRef(null);
  const reportRef = useRef(reportRequestError);

  useEffect(() => { reportRef.current = reportRequestError; }, [reportRequestError]);

  const load = useCallback(async (filters = {}) => {
    const requestProjectId = projectRef.current;
    if (!enabled || !requestProjectId) return null;
    const key = JSON.stringify(filters);
    if (requestRef.current?.key === key) return requestRef.current.promise;
    requestRef.current?.controller.abort();
    const controller = new AbortController();
    setState({ ...initialState(requestProjectId), filters, isLoading: true });
    const promise = fetchResourceLoading(requestProjectId, filters, {
      signal: controller.signal,
    }).then((data) => {
      if (mountedRef.current && projectRef.current === requestProjectId && !controller.signal.aborted) {
        setState({ projectId: requestProjectId, data, filters, error: null, isLoading: false });
      }
      return data;
    }).catch((error) => {
      if (error?.name !== "AbortError" && mountedRef.current && projectRef.current === requestProjectId) {
        setState({ projectId: requestProjectId, data: null, filters, error, isLoading: false });
        reportRef.current?.("Unable to load resource loading", error);
      }
      return null;
    }).finally(() => {
      if (requestRef.current?.controller === controller) requestRef.current = null;
    });
    requestRef.current = { controller, key, promise };
    return promise;
  }, [enabled]);

  useEffect(() => {
    mountedRef.current = true;
    projectRef.current = projectId;
    requestRef.current?.controller.abort();
    requestRef.current = null;
  }, [enabled, projectId]);

  useEffect(() => () => {
    mountedRef.current = false;
    requestRef.current?.controller.abort();
  }, []);

  const current = enabled && state.projectId === projectId
    ? state
    : initialState(projectId);
  return { ...current, load, retry: () => load(current.filters) };
}


export default useResourceLoading;
