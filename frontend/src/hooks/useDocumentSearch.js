import { useCallback, useEffect, useRef, useState } from "react";

import { searchProjectDocuments } from "../services/api";
import { DOCUMENT_SEARCH_LIMIT } from "../utils/documentSearch";


function isAbortError(error) {
  return error?.name === "AbortError";
}


function useDocumentSearch({ projectId, onError }) {
  const [state, setState] = useState({
    projectId: null,
    data: null,
    error: null,
    isLoading: false,
    request: null,
  });
  const projectRef = useRef(projectId);
  const requestRef = useRef(null);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    projectRef.current = projectId;
    requestRef.current?.controller.abort();
    requestRef.current = null;
  }, [projectId]);

  useEffect(
    () => () => {
      projectRef.current = null;
      requestRef.current?.controller.abort();
      requestRef.current = null;
    }, []
  );

  const execute = useCallback(
    (request) => {
      if (!projectId || !request?.query?.trim()) return Promise.resolve(null);
      requestRef.current?.controller.abort();
      const controller = new AbortController();
      const operation = {
        controller,
        projectId,
        request,
      };
      requestRef.current = operation;
      setState((current) => ({
        ...current,
        projectId,
        data: null,
        error: null,
        isLoading: true,
        request,
      }));

      return searchProjectDocuments(projectId, {
        ...request.filters,
        query: request.query.trim(),
        limit: DOCUMENT_SEARCH_LIMIT,
        offset: request.offset || 0,
        signal: controller.signal,
      })
        .then((data) => {
          if (
            requestRef.current !== operation ||
            projectRef.current !== projectId ||
            controller.signal.aborted
          ) {
            return null;
          }
          setState({
            projectId,
            data,
            error: null,
            isLoading: false,
            request,
          });
          return data;
        })
        .catch((error) => {
          if (
            isAbortError(error) ||
            requestRef.current !== operation ||
            projectRef.current !== projectId
          ) {
            return null;
          }
          setState({
            projectId,
            data: null,
            error,
            isLoading: false,
            request,
          });
          onErrorRef.current?.("Unable to search project documents", error);
          return null;
        })
        .finally(() => {
          if (requestRef.current === operation) requestRef.current = null;
        });
    },
    [projectId]
  );

  const submit = useCallback(
    (query, filters) =>
      execute({ query: query.trim(), filters: { ...filters }, offset: 0 }),
    [execute]
  );

  const goToOffset = useCallback(
    (offset) => {
      const request = state.projectId === projectId ? state.request : null;
      if (!request) return Promise.resolve(null);
      return execute({ ...request, offset: Math.max(0, offset) });
    },
    [execute, projectId, state.projectId, state.request]
  );

  const retry = useCallback(
    () => {
      const request = state.projectId === projectId ? state.request : null;
      return request ? execute(request) : Promise.resolve(null);
    },
    [execute, projectId, state.projectId, state.request]
  );

  const clear = useCallback(() => {
    requestRef.current?.controller.abort();
    requestRef.current = null;
    setState({
      projectId,
      data: null,
      error: null,
      isLoading: false,
      request: null,
    });
  }, [projectId]);

  const current = state.projectId === projectId
    ? state
    : {
        projectId,
        data: null,
        error: null,
        isLoading: false,
        request: null,
      };

  return {
    ...current,
    submit,
    goToOffset,
    retry,
    clear,
  };
}

export default useDocumentSearch;
