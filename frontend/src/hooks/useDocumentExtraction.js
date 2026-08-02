import { useCallback, useEffect, useRef, useState } from "react";

import {
  getDocumentExtraction,
  reprocessDocumentExtraction,
} from "../services/api";


function isAbortError(error) {
  return error?.name === "AbortError";
}


function useDocumentExtraction({
  projectId,
  documentId,
  initialExtraction = null,
  load = true,
  onError,
  onUpdate,
}) {
  const identity = projectId && documentId ? `${projectId}:${documentId}` : null;
  const [state, setState] = useState({
    identity: null,
    extraction: null,
    error: null,
    isLoading: false,
    isReprocessing: false,
  });
  const identityRef = useRef(identity);
  const requestRef = useRef(null);
  const onErrorRef = useRef(onError);
  const onUpdateRef = useRef(onUpdate);

  useEffect(() => {
    identityRef.current = identity;
    onErrorRef.current = onError;
    onUpdateRef.current = onUpdate;
  }, [identity, onError, onUpdate]);

  useEffect(() => {
    requestRef.current?.abort();
    requestRef.current = null;
    setState({
      identity,
      extraction: identity ? initialExtraction : null,
      error: null,
      isLoading: Boolean(identity && load),
      isReprocessing: false,
    });
    if (!identity || !load) return undefined;
    const controller = new AbortController();
    requestRef.current = controller;
    const timer = window.setTimeout(() => {
      getDocumentExtraction(projectId, documentId, {
        signal: controller.signal,
      })
        .then((response) => {
          if (
            identityRef.current !== identity ||
            controller.signal.aborted ||
            requestRef.current !== controller
          ) {
            return;
          }
          setState({
            identity,
            extraction: response.extraction,
            error: null,
            isLoading: false,
            isReprocessing: false,
          });
        })
        .catch((error) => {
          if (isAbortError(error) || identityRef.current !== identity) return;
          setState((current) => ({
            ...current,
            error,
            isLoading: false,
          }));
          onErrorRef.current?.("Unable to load document extraction status", error);
        });
    }, 0);
    return () => {
      window.clearTimeout(timer);
      window.setTimeout(() => {
        if (requestRef.current === controller) controller.abort();
      }, 0);
    };
  }, [documentId, identity, initialExtraction, load, projectId]);

  useEffect(
    () => () => {
      identityRef.current = null;
      requestRef.current?.abort();
      requestRef.current = null;
    }, []
  );

  const reprocess = useCallback(async () => {
    if (!identity || state.isReprocessing) return false;
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setState((current) => ({
      ...current,
      error: null,
      isReprocessing: true,
    }));
    try {
      const response = await reprocessDocumentExtraction(
        projectId,
        documentId,
        { signal: controller.signal }
      );
      if (
        identityRef.current !== identity ||
        controller.signal.aborted ||
        requestRef.current !== controller
      ) {
        return false;
      }
      setState({
        identity,
        extraction: response.extraction,
        error: null,
        isLoading: false,
        isReprocessing: false,
      });
      onUpdateRef.current?.(response.extraction);
      return true;
    } catch (error) {
      if (!isAbortError(error) && identityRef.current === identity) {
        setState((current) => ({
          ...current,
          error,
          isReprocessing: false,
        }));
        onErrorRef.current?.("Unable to reprocess document text", error);
      }
      return false;
    } finally {
      if (requestRef.current === controller) requestRef.current = null;
    }
  }, [documentId, identity, projectId, state.isReprocessing]);

  const current = state.identity === identity ? state : {
    extraction: null,
    error: null,
    isLoading: Boolean(identity && load),
    isReprocessing: false,
  };
  return { ...current, reprocess };
}

export default useDocumentExtraction;
