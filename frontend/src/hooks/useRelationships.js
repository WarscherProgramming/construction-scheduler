import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createRelationship as createRelationshipRequest,
  deleteRelationship as deleteRelationshipRequest,
  listRelationships,
} from "../services/api";


function isAbortError(error) {
  return error?.name === "AbortError";
}


function operationError(operation, error) {
  return {
    operation,
    status: error?.status,
    message: error?.message || "The relationship request could not be completed.",
  };
}


function useRelationships({
  projectId,
  entityType,
  entityId,
  enabled = true,
  onError,
}) {
  const isActive = Boolean(enabled && projectId && entityType && entityId);
  const identityKey = isActive
    ? `${projectId}:${entityType}:${entityId}`
    : null;
  const [storedRelationships, setStoredRelationships] = useState([]);
  const [pagination, setPagination] = useState({
    limit: 50,
    offset: 0,
    total: 0,
    has_more: false,
  });
  const [loadedIdentity, setLoadedIdentity] = useState(null);
  const [isListLoading, setIsListLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [deletingIds, setDeletingIds] = useState([]);
  const [error, setError] = useState(null);
  const identityRef = useRef(identityKey);
  const onErrorRef = useRef(onError);
  const listVersionRef = useRef(0);
  const listRequestRef = useRef(null);
  const listAbortTimerRef = useRef(null);
  const relationshipsRef = useRef([]);
  const createControllerRef = useRef(null);
  const deleteControllersRef = useRef(new Map());

  useEffect(() => {
    identityRef.current = identityKey;
  }, [identityKey]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    relationshipsRef.current = storedRelationships;
  }, [storedRelationships]);

  const reportError = useCallback((context, requestError) => {
    onErrorRef.current?.(context, requestError);
  }, []);

  const startListRequest = useCallback(
    ({ clear = false, force = false, append = false } = {}) => {
      if (!identityKey) return Promise.resolve([]);
      const existingRequest = listRequestRef.current;
      if (
        !force &&
        existingRequest?.identityKey === identityKey &&
        !existingRequest.settled
      ) {
        return existingRequest.promise;
      }
      if (existingRequest && !existingRequest.settled) {
        existingRequest.controller.abort();
      }

      const controller = new AbortController();
      const version = ++listVersionRef.current;
      const offset = append ? relationshipsRef.current.length : 0;
      const requestRecord = {
        controller,
        identityKey,
        promise: null,
        settled: false,
      };
      if (clear) {
        setStoredRelationships([]);
        setLoadedIdentity(null);
      }
      setIsListLoading(true);
      setError(null);

      const promise = listRelationships(projectId, entityType, entityId, {
        limit: 50,
        offset,
        signal: controller.signal,
      })
        .then((response) => {
          if (
            version !== listVersionRef.current ||
            identityRef.current !== identityKey
          ) {
            return [];
          }
          const next = response?.relationships || [];
          setStoredRelationships((current) =>
            append ? [...current, ...next] : next
          );
          setPagination(
            response?.pagination || {
              limit: 50,
              offset,
              total: next.length,
              has_more: false,
            }
          );
          setLoadedIdentity(identityKey);
          return next;
        })
        .catch((requestError) => {
          if (
            isAbortError(requestError) ||
            version !== listVersionRef.current ||
            identityRef.current !== identityKey
          ) {
            return [];
          }
          if (!append) setStoredRelationships([]);
          setLoadedIdentity(identityKey);
          setError(operationError("list", requestError));
          reportError("Unable to load relationships", requestError);
          return [];
        })
        .finally(() => {
          requestRecord.settled = true;
          if (
            version === listVersionRef.current &&
            identityRef.current === identityKey
          ) {
            setIsListLoading(false);
          }
        });
      requestRecord.promise = promise;
      listRequestRef.current = requestRecord;
      return promise;
    },
    [
      entityId,
      entityType,
      identityKey,
      projectId,
      reportError,
    ]
  );

  useEffect(() => {
    if (listAbortTimerRef.current) {
      window.clearTimeout(listAbortTimerRef.current);
      listAbortTimerRef.current = null;
    }
    const currentRequest = listRequestRef.current;
    if (
      currentRequest &&
      !currentRequest.settled &&
      currentRequest.identityKey !== identityKey
    ) {
      currentRequest.controller.abort();
    }
    createControllerRef.current?.abort();
    for (const controller of deleteControllersRef.current.values()) {
      controller.abort();
    }
    deleteControllersRef.current.clear();

    const resetTimer = window.setTimeout(() => {
      if (!identityKey) {
        setStoredRelationships([]);
        setLoadedIdentity(null);
        setPagination({ limit: 50, offset: 0, total: 0, has_more: false });
        setError(null);
      }
      setIsCreating(false);
      setDeletingIds([]);
    }, 0);
    if (!identityKey) return () => window.clearTimeout(resetTimer);

    let requestAtSetup = null;
    const startTimer = window.setTimeout(() => {
      startListRequest({ clear: true });
      requestAtSetup = listRequestRef.current;
    }, 0);
    return () => {
      window.clearTimeout(resetTimer);
      window.clearTimeout(startTimer);
      listAbortTimerRef.current = window.setTimeout(() => {
        if (
          requestAtSetup &&
          listRequestRef.current === requestAtSetup &&
          !requestAtSetup.settled
        ) {
          requestAtSetup.controller.abort();
        }
      }, 0);
    };
  }, [identityKey, startListRequest]);

  useEffect(
    () => () => {
      listRequestRef.current?.controller.abort();
      createControllerRef.current?.abort();
      for (const controller of deleteControllersRef.current.values()) {
        controller.abort();
      }
    },
    []
  );

  const refresh = useCallback(
    () => startListRequest({ force: true }),
    [startListRequest]
  );
  const loadMore = useCallback(
    () => startListRequest({ force: true, append: true }),
    [startListRequest]
  );

  const createRelationship = useCallback(
    async (payload) => {
      if (!identityKey || isCreating || createControllerRef.current) {
        return false;
      }
      const operationIdentity = identityKey;
      const controller = new AbortController();
      createControllerRef.current?.abort();
      createControllerRef.current = controller;
      setIsCreating(true);
      setError(null);
      try {
        await createRelationshipRequest(projectId, payload, {
          signal: controller.signal,
        });
        if (identityRef.current !== operationIdentity) return false;
        await startListRequest({ force: true });
        return true;
      } catch (requestError) {
        if (isAbortError(requestError)) return false;
        if (identityRef.current === operationIdentity) {
          setError(operationError("create", requestError));
          reportError("Unable to create relationship", requestError);
        }
        return false;
      } finally {
        if (createControllerRef.current === controller) {
          createControllerRef.current = null;
          if (identityRef.current === operationIdentity) {
            setIsCreating(false);
          }
        }
      }
    }, [identityKey, isCreating, projectId, reportError, startListRequest]
  );

  const deleteRelationship = useCallback(
    async (relationship) => {
      if (!identityKey || !relationship?.id) return false;
      if (deleteControllersRef.current.has(relationship.id)) return false;
      const operationIdentity = identityKey;
      const controller = new AbortController();
      deleteControllersRef.current.set(relationship.id, controller);
      setDeletingIds((current) => [...current, relationship.id]);
      setError(null);
      try {
        await deleteRelationshipRequest(projectId, relationship.id, {
          signal: controller.signal,
        });
        if (identityRef.current === operationIdentity) {
          await startListRequest({ force: true });
        }
        return true;
      } catch (requestError) {
        if (isAbortError(requestError)) return false;
        if (identityRef.current === operationIdentity) {
          setError(operationError("delete", requestError));
          reportError("Unable to remove relationship", requestError);
        }
        return false;
      } finally {
        if (deleteControllersRef.current.get(relationship.id) === controller) {
          deleteControllersRef.current.delete(relationship.id);
          setDeletingIds((current) =>
            current.filter((id) => id !== relationship.id)
          );
        }
      }
    }, [identityKey, projectId, reportError, startListRequest]
  );

  const relationships = useMemo(
    () =>
      identityKey && loadedIdentity === identityKey
        ? storedRelationships
        : [],
    [identityKey, loadedIdentity, storedRelationships]
  );

  return {
    relationships,
    total: identityKey && loadedIdentity === identityKey ? pagination.total : 0,
    hasMore: Boolean(pagination.has_more),
    isLoading: Boolean(
      identityKey && (isListLoading || loadedIdentity !== identityKey)
    ),
    isCreating,
    deletingIds,
    error,
    refresh,
    loadMore,
    createRelationship,
    deleteRelationship,
    clearError: useCallback(() => setError(null), []),
  };
}

export default useRelationships;
