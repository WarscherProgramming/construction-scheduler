import { useCallback, useEffect, useRef, useState } from "react";

import {
  addPreconstructionReviewSource,
  archivePreconstructionReviewSet,
  cancelPreconstructionRun,
  createPreconstructionReviewSet,
  createPreconstructionRun,
  getPreconstructionReadiness,
  getPreconstructionReviewSet,
  listPreconstructionReviewSets,
  listPreconstructionReviewSources,
  listPreconstructionRuns,
  listPreconstructionSourceCandidates,
  removePreconstructionReviewSource,
  retryPreconstructionRun,
  updatePreconstructionReviewSet,
  updatePreconstructionReviewSource,
} from "../services/api";


function isAbortError(error) {
  return error?.name === "AbortError";
}


const EMPTY_DETAIL = {
  reviewSet: null,
  sources: [],
  roles: [],
  readiness: null,
  runs: [],
};


function usePreconstruction({ projectId, onError }) {
  const [filter, setFilter] = useState("active");
  const [reviewSets, setReviewSets] = useState([]);
  const [selectedReviewSetId, setSelectedReviewSetId] = useState(null);
  const [detail, setDetail] = useState(EMPTY_DETAIL);
  const [isListLoading, setIsListLoading] = useState(true);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [listError, setListError] = useState(null);
  const [detailError, setDetailError] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [isCandidateLoading, setIsCandidateLoading] = useState(false);
  const projectRef = useRef(projectId);
  const selectedReviewSetRef = useRef(null);
  const onErrorRef = useRef(onError);
  const listRequestRef = useRef(null);
  const detailRequestRef = useRef(null);
  const candidateRequestRef = useRef(null);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    projectRef.current = projectId;
    listRequestRef.current?.abort();
    detailRequestRef.current?.abort();
    candidateRequestRef.current?.abort();
    selectedReviewSetRef.current = null;
    const resetTimer = window.setTimeout(() => {
      setReviewSets([]);
      setSelectedReviewSetId(null);
      setDetail(EMPTY_DETAIL);
      setCandidates([]);
      setListError(null);
      setDetailError(null);
    }, 0);
    return () => window.clearTimeout(resetTimer);
  }, [projectId]);

  useEffect(() => () => {
    projectRef.current = null;
    listRequestRef.current?.abort();
    detailRequestRef.current?.abort();
    candidateRequestRef.current?.abort();
  }, []);

  const loadReviewSets = useCallback(() => {
    if (!projectId) return Promise.resolve(null);
    listRequestRef.current?.abort();
    const controller = new AbortController();
    listRequestRef.current = controller;
    setIsListLoading(true);
    setListError(null);
    return listPreconstructionReviewSets(projectId, {
      state: filter,
      limit: 100,
      signal: controller.signal,
    })
      .then((response) => {
        if (projectRef.current !== projectId || controller.signal.aborted) return null;
        setReviewSets(response.items);
        setSelectedReviewSetId((current) => {
          const next = response.items.some((item) => item.id === current)
            ? current
            : null;
          selectedReviewSetRef.current = next;
          return next;
        });
        return response;
      })
      .catch((error) => {
        if (isAbortError(error) || projectRef.current !== projectId) return null;
        setListError(error);
        onErrorRef.current?.("Unable to load preconstruction review sets", error);
        return null;
      })
      .finally(() => {
        if (listRequestRef.current === controller) {
          listRequestRef.current = null;
          setIsListLoading(false);
        }
      });
  }, [filter, projectId]);

  useEffect(() => {
    const startTimer = window.setTimeout(() => void loadReviewSets(), 0);
    return () => window.clearTimeout(startTimer);
  }, [loadReviewSets]);

  const loadDetail = useCallback((reviewSetId = selectedReviewSetId) => {
    if (!projectId || !reviewSetId) {
      setDetail(EMPTY_DETAIL);
      return Promise.resolve(null);
    }
    detailRequestRef.current?.abort();
    const controller = new AbortController();
    const identity = { controller, projectId, reviewSetId };
    detailRequestRef.current = controller;
    setDetail(EMPTY_DETAIL);
    setIsDetailLoading(true);
    setDetailError(null);
    return Promise.all([
      getPreconstructionReviewSet(projectId, reviewSetId, { signal: controller.signal }),
      listPreconstructionReviewSources(projectId, reviewSetId, { signal: controller.signal }),
      getPreconstructionReadiness(projectId, reviewSetId, { signal: controller.signal }),
      listPreconstructionRuns(projectId, reviewSetId, { limit: 100, signal: controller.signal }),
    ])
      .then(([reviewSet, sources, readiness, runs]) => {
        if (
          projectRef.current !== identity.projectId ||
          selectedReviewSetRef.current !== identity.reviewSetId ||
          controller.signal.aborted
        ) return null;
        const next = {
          reviewSet,
          sources: sources.items,
          roles: sources.roles,
          readiness,
          runs: runs.items,
        };
        setDetail(next);
        return next;
      })
      .catch((error) => {
        if (isAbortError(error) || projectRef.current !== projectId) return null;
        setDetailError(error);
        onErrorRef.current?.("Unable to load preconstruction review details", error);
        return null;
      })
      .finally(() => {
        if (detailRequestRef.current === controller) {
          detailRequestRef.current = null;
          setIsDetailLoading(false);
        }
      });
  }, [projectId, selectedReviewSetId]);

  useEffect(() => {
    const startTimer = window.setTimeout(
      () => void loadDetail(selectedReviewSetId),
      0
    );
    return () => window.clearTimeout(startTimer);
  }, [loadDetail, selectedReviewSetId]);

  const runMutation = useCallback(async (message, operation, refresh = "detail") => {
    setIsSaving(true);
    try {
      const value = await operation();
      if (projectRef.current !== projectId) return null;
      if (refresh === "list") await loadReviewSets();
      if (refresh === "detail") await loadDetail();
      return value;
    } catch (error) {
      if (!isAbortError(error) && projectRef.current === projectId) {
        onErrorRef.current?.(message, error);
      }
      throw error;
    } finally {
      if (projectRef.current === projectId) setIsSaving(false);
    }
  }, [loadDetail, loadReviewSets, projectId]);

  const createReviewSet = useCallback((values) =>
    runMutation(
      "Unable to create preconstruction review set",
      () => createPreconstructionReviewSet(projectId, values),
      "none"
    ).then(async (created) => {
      if (created) {
        await loadReviewSets();
        selectedReviewSetRef.current = created.id;
        setSelectedReviewSetId(created.id);
      }
      return created;
    }), [loadReviewSets, projectId, runMutation]);

  const updateReviewSet = useCallback((values) => runMutation(
    "Unable to update preconstruction review set",
    () => updatePreconstructionReviewSet(projectId, selectedReviewSetId, values),
    "detail"
  ).then(async (updated) => {
    if (updated) await loadReviewSets();
    return updated;
  }), [loadReviewSets, projectId, runMutation, selectedReviewSetId]);

  const archiveReviewSet = useCallback(() => runMutation(
    "Unable to archive preconstruction review set",
    () => archivePreconstructionReviewSet(projectId, selectedReviewSetId),
    "none"
  ).then(async (archived) => {
    if (archived) {
      selectedReviewSetRef.current = null;
      setSelectedReviewSetId(null);
      await loadReviewSets();
    }
    return archived;
  }), [loadReviewSets, projectId, runMutation, selectedReviewSetId]);

  const addSource = useCallback((source) => runMutation(
    "Unable to add preconstruction review source",
    () => addPreconstructionReviewSource(projectId, selectedReviewSetId, source)
  ), [projectId, runMutation, selectedReviewSetId]);

  const updateSource = useCallback((sourceId, source) => runMutation(
    "Unable to update preconstruction review source",
    () => updatePreconstructionReviewSource(projectId, selectedReviewSetId, sourceId, source)
  ), [projectId, runMutation, selectedReviewSetId]);

  const removeSource = useCallback((sourceId) => runMutation(
    "Unable to remove preconstruction review source",
    () => removePreconstructionReviewSource(projectId, selectedReviewSetId, sourceId)
  ), [projectId, runMutation, selectedReviewSetId]);

  const requestRun = useCallback(() => runMutation(
    "Unable to request preconstruction analysis run",
    () => createPreconstructionRun(projectId, selectedReviewSetId, {
      analysis_type: "provider_contract_validation",
    })
  ).then(async (run) => {
    if (run) await loadReviewSets();
    return run;
  }), [loadReviewSets, projectId, runMutation, selectedReviewSetId]);

  const cancelRun = useCallback((runId) => runMutation(
    "Unable to cancel preconstruction analysis run",
    () => cancelPreconstructionRun(projectId, runId)
  ), [projectId, runMutation]);

  const retryRun = useCallback((runId) => runMutation(
    "Unable to retry preconstruction analysis run",
    () => retryPreconstructionRun(projectId, runId)
  ), [projectId, runMutation]);

  const searchCandidates = useCallback((sourceType, search) => {
    candidateRequestRef.current?.abort();
    const controller = new AbortController();
    candidateRequestRef.current = controller;
    setIsCandidateLoading(true);
    setCandidates([]);
    return listPreconstructionSourceCandidates(projectId, {
      sourceType,
      search,
      limit: 20,
      signal: controller.signal,
    }).then((response) => {
      if (projectRef.current !== projectId || controller.signal.aborted) return null;
      setCandidates(response.items);
      return response.items;
    }).catch((error) => {
      if (isAbortError(error) || projectRef.current !== projectId) return null;
      onErrorRef.current?.("Unable to search preconstruction source candidates", error);
      return null;
    }).finally(() => {
      if (candidateRequestRef.current === controller) {
        candidateRequestRef.current = null;
        setIsCandidateLoading(false);
      }
    });
  }, [projectId]);

  const selectReviewSet = useCallback((reviewSetId) => {
    selectedReviewSetRef.current = reviewSetId;
    setSelectedReviewSetId(reviewSetId);
  }, []);

  return {
    filter,
    setFilter,
    reviewSets,
    selectedReviewSetId,
    selectReviewSet,
    detail,
    isListLoading,
    isDetailLoading,
    isSaving,
    listError,
    detailError,
    candidates,
    isCandidateLoading,
    refreshList: loadReviewSets,
    refreshDetail: loadDetail,
    createReviewSet,
    updateReviewSet,
    archiveReviewSet,
    addSource,
    updateSource,
    removeSource,
    requestRun,
    cancelRun,
    retryRun,
    searchCandidates,
  };
}

export default usePreconstruction;
