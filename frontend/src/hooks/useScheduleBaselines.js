import { useCallback, useEffect, useRef, useState } from "react";

import {
  archiveScheduleBaseline,
  createScheduleBaseline,
  fetchScheduleVariance,
  listScheduleBaselines,
  selectScheduleBaseline,
} from "../services/api";


const DEFAULT_FILTERS = {
  includeSummaries: true,
  status: "",
  criticalChange: "",
  search: "",
  sort: "wbs",
  order: "asc",
  limit: 50,
  offset: 0,
};


function initialState(projectId = null) {
  return {
    projectId,
    baselines: [],
    comparisonBaselineId: null,
    viewBaselineId: null,
    variance: null,
    filters: { ...DEFAULT_FILTERS },
    listError: null,
    varianceError: null,
    mutationError: null,
    isLoadingList: false,
    isLoadingVariance: false,
    pendingActions: [],
    requiresSelection: false,
  };
}


function isAbortError(error) {
  return error?.name === "AbortError";
}


function useScheduleBaselines({
  projectId,
  enabled,
  setScheduleSettings,
  showNotice,
  reportRequestError,
}) {
  const [state, setState] = useState(() => initialState(projectId));
  const projectRef = useRef(projectId);
  const mountedRef = useRef(true);
  const listRequestRef = useRef(null);
  const varianceRequestRef = useRef(null);
  const mutationControllersRef = useRef(new Map());
  const filtersRef = useRef({ ...DEFAULT_FILTERS });
  const viewBaselineIdRef = useRef(null);
  const comparisonBaselineIdRef = useRef(null);
  const showNoticeRef = useRef(showNotice);
  const reportRequestErrorRef = useRef(reportRequestError);

  useEffect(() => {
    showNoticeRef.current = showNotice;
    reportRequestErrorRef.current = reportRequestError;
  }, [reportRequestError, showNotice]);

  const isCurrentProject = useCallback(
    (requestProjectId) =>
      mountedRef.current && projectRef.current === requestProjectId,
    []
  );

  const executeVariance = useCallback(
    async ({ baselineId, filters } = {}) => {
      const requestProjectId = projectRef.current;
      if (!enabled || !requestProjectId) return null;

      varianceRequestRef.current?.controller.abort();
      const controller = new AbortController();
      const operation = { controller, projectId: requestProjectId };
      varianceRequestRef.current = operation;
      const requestFilters = filters || filtersRef.current;
      const requestBaselineId =
        baselineId === undefined ? viewBaselineIdRef.current : baselineId;

      setState((current) => ({
        ...(current.projectId === requestProjectId
          ? current
          : initialState(requestProjectId)),
        variance: null,
        varianceError: null,
        isLoadingVariance: true,
      }));

      try {
        const data = await fetchScheduleVariance(requestProjectId, {
          ...requestFilters,
          baselineId: requestBaselineId,
          signal: controller.signal,
        });
        if (
          varianceRequestRef.current !== operation ||
          !isCurrentProject(requestProjectId) ||
          controller.signal.aborted
        ) {
          return null;
        }
        setState((current) => ({
          ...(current.projectId === requestProjectId
            ? current
            : initialState(requestProjectId)),
          variance: data,
          varianceError: null,
          isLoadingVariance: false,
          requiresSelection: false,
        }));
        return data;
      } catch (error) {
        if (
          isAbortError(error) ||
          varianceRequestRef.current !== operation ||
          !isCurrentProject(requestProjectId)
        ) {
          return null;
        }
        setState((current) => ({
          ...(current.projectId === requestProjectId
            ? current
            : initialState(requestProjectId)),
          variance: null,
          varianceError: error,
          isLoadingVariance: false,
        }));
        reportRequestErrorRef.current?.(
          "Unable to load schedule variance",
          error
        );
        return null;
      } finally {
        if (varianceRequestRef.current === operation) {
          varianceRequestRef.current = null;
        }
      }
    },
    [enabled, isCurrentProject]
  );

  const loadBaselines = useCallback(async () => {
    const requestProjectId = projectRef.current;
    if (!enabled || !requestProjectId) return null;

    listRequestRef.current?.controller.abort();
    const controller = new AbortController();
    const operation = { controller, projectId: requestProjectId };
    listRequestRef.current = operation;
    filtersRef.current = { ...DEFAULT_FILTERS };
    viewBaselineIdRef.current = null;
    comparisonBaselineIdRef.current = null;
    setState({
      ...initialState(requestProjectId),
      isLoadingList: true,
    });

    try {
      const data = await listScheduleBaselines(requestProjectId, {
        status: "all",
        limit: 100,
        offset: 0,
        signal: controller.signal,
      });
      if (
        listRequestRef.current !== operation ||
        !isCurrentProject(requestProjectId) ||
        controller.signal.aborted
      ) {
        return null;
      }
      comparisonBaselineIdRef.current = data.comparison_baseline_id ?? null;
      viewBaselineIdRef.current = data.comparison_baseline_id ?? null;
      setState((current) => ({
        ...(current.projectId === requestProjectId
          ? current
          : initialState(requestProjectId)),
        baselines: data.baselines,
        comparisonBaselineId: data.comparison_baseline_id ?? null,
        viewBaselineId: data.comparison_baseline_id ?? null,
        listError: null,
        isLoadingList: false,
      }));
      await executeVariance({
        baselineId: data.comparison_baseline_id ?? null,
        filters: filtersRef.current,
      });
      return data;
    } catch (error) {
      if (
        isAbortError(error) ||
        listRequestRef.current !== operation ||
        !isCurrentProject(requestProjectId)
      ) {
        return null;
      }
      setState({
        ...initialState(requestProjectId),
        listError: error,
      });
      reportRequestErrorRef.current?.(
        "Unable to load schedule baselines",
        error
      );
      return null;
    } finally {
      if (listRequestRef.current === operation) listRequestRef.current = null;
    }
  }, [enabled, executeVariance, isCurrentProject]);

  useEffect(() => {
    mountedRef.current = true;
    projectRef.current = projectId;
    listRequestRef.current?.controller.abort();
    varianceRequestRef.current?.controller.abort();
    for (const operation of mutationControllersRef.current.values()) {
      operation.controller.abort();
    }
    mutationControllersRef.current.clear();
    filtersRef.current = { ...DEFAULT_FILTERS };
    viewBaselineIdRef.current = null;
    comparisonBaselineIdRef.current = null;

    if (!enabled || !projectId) return undefined;
    const timeoutId = window.setTimeout(() => void loadBaselines(), 0);
    return () => window.clearTimeout(timeoutId);
  }, [enabled, loadBaselines, projectId]);

  useEffect(
    () => () => {
      mountedRef.current = false;
      projectRef.current = null;
      listRequestRef.current?.controller.abort();
      varianceRequestRef.current?.controller.abort();
      for (const operation of mutationControllersRef.current.values()) {
        operation.controller.abort();
      }
      mutationControllersRef.current.clear();
    }, []
  );

  const runMutation = useCallback(
    async (key, operation, onSuccess) => {
      const requestProjectId = projectRef.current;
      if (
        !enabled ||
        !requestProjectId ||
        mutationControllersRef.current.has(key)
      ) {
        return null;
      }

      const controller = new AbortController();
      const token = Symbol(key);
      mutationControllersRef.current.set(key, { controller, token });
      setState((current) => ({
        ...(current.projectId === requestProjectId
          ? current
          : initialState(requestProjectId)),
        mutationError: null,
        pendingActions: Array.from(mutationControllersRef.current.keys()),
      }));

      try {
        const data = await operation(requestProjectId, controller.signal);
        if (!isCurrentProject(requestProjectId) || controller.signal.aborted) {
          return null;
        }
        await onSuccess(data, requestProjectId);
        return isCurrentProject(requestProjectId) ? data : null;
      } catch (error) {
        if (!isAbortError(error) && isCurrentProject(requestProjectId)) {
          setState((current) => ({
            ...(current.projectId === requestProjectId
              ? current
              : initialState(requestProjectId)),
            mutationError: error,
          }));
          reportRequestErrorRef.current?.(
            `Unable to ${key} schedule baseline`,
            error
          );
        }
        return null;
      } finally {
        const active = mutationControllersRef.current.get(key);
        if (active?.token === token) {
          mutationControllersRef.current.delete(key);
          if (isCurrentProject(requestProjectId)) {
            setState((current) => ({
              ...(current.projectId === requestProjectId
                ? current
                : initialState(requestProjectId)),
              pendingActions: Array.from(
                mutationControllersRef.current.keys()
              ),
            }));
          }
        }
      }
    },
    [enabled, isCurrentProject]
  );

  const createBaseline = useCallback(
    (payload) =>
      runMutation(
        "create",
        (requestProjectId, signal) =>
          createScheduleBaseline(requestProjectId, payload, { signal }),
        async (data, requestProjectId) => {
          comparisonBaselineIdRef.current = data.comparison_baseline_id;
          viewBaselineIdRef.current = data.baseline.id;
          setScheduleSettings((current) =>
            current?.project_id === requestProjectId
              ? {
                  ...current,
                  comparison_baseline_id: data.comparison_baseline_id,
                }
              : current
          );
          setState((current) => ({
            ...current,
            baselines: [
              data.baseline,
              ...current.baselines.filter(
                (baseline) => baseline.id !== data.baseline.id
              ),
            ],
            comparisonBaselineId: data.comparison_baseline_id,
            viewBaselineId: data.baseline.id,
            requiresSelection: false,
          }));
          await executeVariance({ baselineId: data.baseline.id });
          if (isCurrentProject(requestProjectId)) {
            showNoticeRef.current?.("success", "Schedule baseline captured.");
          }
        }
      ),
    [executeVariance, isCurrentProject, runMutation, setScheduleSettings]
  );

  const archiveBaseline = useCallback(
    (baselineId) =>
      runMutation(
        "archive",
        (requestProjectId, signal) =>
          archiveScheduleBaseline(requestProjectId, baselineId, { signal }),
        async (data, requestProjectId) => {
          const wasViewed = viewBaselineIdRef.current === baselineId;
          comparisonBaselineIdRef.current = data.comparison_baseline_id;
          if (wasViewed) viewBaselineIdRef.current = null;
          setScheduleSettings((current) =>
            current?.project_id === requestProjectId
              ? {
                  ...current,
                  comparison_baseline_id: data.comparison_baseline_id,
                }
              : current
          );
          setState((current) => ({
            ...current,
            baselines: current.baselines.map((baseline) =>
              baseline.id === data.baseline.id ? data.baseline : baseline
            ),
            comparisonBaselineId: data.comparison_baseline_id,
            viewBaselineId: wasViewed ? null : current.viewBaselineId,
            variance: wasViewed ? null : current.variance,
            requiresSelection: wasViewed,
          }));
          if (wasViewed) varianceRequestRef.current?.controller.abort();
          if (isCurrentProject(requestProjectId)) {
            showNoticeRef.current?.("success", "Schedule baseline archived.");
          }
        }
      ),
    [isCurrentProject, runMutation, setScheduleSettings]
  );

  const selectBaseline = useCallback(
    async (baselineId) => {
      const numericId = baselineId ? Number(baselineId) : null;
      const currentState =
        state.projectId === projectId ? state : initialState(projectId);
      const baseline = currentState.baselines.find(
        (item) => item.id === numericId
      );

      if (baseline?.status === "archived") {
        viewBaselineIdRef.current = numericId;
        setState((current) => ({
          ...current,
          viewBaselineId: numericId,
          requiresSelection: false,
        }));
        return executeVariance({ baselineId: numericId });
      }

      return runMutation(
        "select",
        (requestProjectId, signal) =>
          selectScheduleBaseline(requestProjectId, numericId, { signal }),
        async (settings, requestProjectId) => {
          comparisonBaselineIdRef.current = settings.comparison_baseline_id;
          viewBaselineIdRef.current = settings.comparison_baseline_id;
          setScheduleSettings(settings);
          setState((current) => ({
            ...current,
            comparisonBaselineId: settings.comparison_baseline_id,
            viewBaselineId: settings.comparison_baseline_id,
            requiresSelection: false,
          }));
          await executeVariance({
            baselineId: settings.comparison_baseline_id,
          });
          if (isCurrentProject(requestProjectId)) {
            showNoticeRef.current?.(
              "success",
              settings.comparison_baseline_id
                ? "Comparison baseline selected."
                : "Automatic baseline comparison selected."
            );
          }
        }
      );
    },
    [
      executeVariance,
      isCurrentProject,
      projectId,
      runMutation,
      setScheduleSettings,
      state,
    ]
  );

  const updateFilters = useCallback(
    (changes) => {
      const next = {
        ...filtersRef.current,
        ...changes,
        offset: Object.hasOwn(changes, "offset") ? changes.offset : 0,
      };
      filtersRef.current = next;
      setState((current) => ({ ...current, filters: next }));
      return executeVariance({ filters: next });
    },
    [executeVariance]
  );

  const clearMutationError = useCallback(() => {
    setState((current) => ({ ...current, mutationError: null }));
  }, []);

  const current =
    state.projectId === projectId ? state : initialState(projectId);

  return {
    ...current,
    selectedBaseline:
      current.baselines.find(
        (baseline) => baseline.id === current.viewBaselineId
      ) || current.variance?.baseline || null,
    loadBaselines,
    retryBaselines: loadBaselines,
    retryVariance: executeVariance,
    createBaseline,
    archiveBaseline,
    selectBaseline,
    updateFilters,
    clearMutationError,
    isCreating: current.pendingActions.includes("create"),
    isArchiving: current.pendingActions.includes("archive"),
    isSelecting: current.pendingActions.includes("select"),
  };
}

export { DEFAULT_FILTERS };
export default useScheduleBaselines;
