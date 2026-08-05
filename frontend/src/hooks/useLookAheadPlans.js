import { useCallback, useEffect, useRef, useState } from "react";

import {
  archiveLookAheadPlan,
  createLookAheadPlan,
  getLookAheadPlan,
  listLookAheadPlans,
  updateLookAheadItem,
  updateLookAheadPlan,
} from "../services/api";


const DEFAULT_FILTERS = {
  search: "",
  week: "",
  readiness: "",
  progress: "",
  companyId: "",
  criticalOnly: false,
  milestonesOnly: false,
  blockedOnly: false,
  overdueOnly: false,
  outOfSequenceOnly: false,
};


function initialState(projectId = null) {
  return {
    projectId,
    plans: [],
    selectedPlanId: null,
    detail: null,
    filters: { ...DEFAULT_FILTERS },
    listError: null,
    detailError: null,
    mutationError: null,
    isLoadingList: false,
    isLoadingDetail: false,
    pendingActions: [],
  };
}


function isAbortError(error) {
  return error?.name === "AbortError";
}


function useLookAheadPlans({
  projectId,
  enabled,
  showNotice,
  reportRequestError,
}) {
  const [state, setState] = useState(() => initialState(projectId));
  const projectRef = useRef(projectId);
  const mountedRef = useRef(true);
  const selectedPlanIdRef = useRef(null);
  const listRequestRef = useRef(null);
  const detailRequestRef = useRef(null);
  const mutationControllersRef = useRef(new Map());
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

  const loadDetail = useCallback(
    async (planId) => {
      const requestProjectId = projectRef.current;
      const numericPlanId = planId ? Number(planId) : null;
      detailRequestRef.current?.controller.abort();
      if (!enabled || !requestProjectId || !numericPlanId) {
        selectedPlanIdRef.current = null;
        setState((current) => ({
          ...(current.projectId === requestProjectId
            ? current
            : initialState(requestProjectId)),
          selectedPlanId: null,
          detail: null,
          detailError: null,
          isLoadingDetail: false,
          filters: { ...DEFAULT_FILTERS },
        }));
        return null;
      }

      selectedPlanIdRef.current = numericPlanId;
      const controller = new AbortController();
      const operation = { controller, projectId: requestProjectId, planId: numericPlanId };
      detailRequestRef.current = operation;
      setState((current) => ({
        ...(current.projectId === requestProjectId
          ? current
          : initialState(requestProjectId)),
        selectedPlanId: numericPlanId,
        detail: null,
        detailError: null,
        isLoadingDetail: true,
        filters: { ...DEFAULT_FILTERS },
      }));

      try {
        const detail = await getLookAheadPlan(
          requestProjectId,
          numericPlanId,
          { signal: controller.signal }
        );
        if (
          detailRequestRef.current !== operation ||
          !isCurrentProject(requestProjectId) ||
          selectedPlanIdRef.current !== numericPlanId ||
          controller.signal.aborted
        ) {
          return null;
        }
        setState((current) => ({
          ...current,
          selectedPlanId: numericPlanId,
          detail,
          detailError: null,
          isLoadingDetail: false,
        }));
        return detail;
      } catch (error) {
        if (
          isAbortError(error) ||
          detailRequestRef.current !== operation ||
          !isCurrentProject(requestProjectId) ||
          selectedPlanIdRef.current !== numericPlanId
        ) {
          return null;
        }
        setState((current) => ({
          ...current,
          detail: null,
          detailError: error,
          isLoadingDetail: false,
        }));
        reportRequestErrorRef.current?.("Unable to load look-ahead plan", error);
        return null;
      } finally {
        if (detailRequestRef.current === operation) {
          detailRequestRef.current = null;
        }
      }
    },
    [enabled, isCurrentProject]
  );

  const loadPlans = useCallback(async () => {
    const requestProjectId = projectRef.current;
    if (!enabled || !requestProjectId) return null;
    listRequestRef.current?.controller.abort();
    detailRequestRef.current?.controller.abort();
    selectedPlanIdRef.current = null;
    const controller = new AbortController();
    const operation = { controller, projectId: requestProjectId };
    listRequestRef.current = operation;
    setState({ ...initialState(requestProjectId), isLoadingList: true });

    try {
      const data = await listLookAheadPlans(requestProjectId, {
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
      const selected = data.plans.find((plan) => plan.status === "active") || null;
      setState((current) => ({
        ...(current.projectId === requestProjectId
          ? current
          : initialState(requestProjectId)),
        plans: data.plans,
        selectedPlanId: selected?.id || null,
        listError: null,
        isLoadingList: false,
      }));
      if (selected) await loadDetail(selected.id);
      return data;
    } catch (error) {
      if (
        isAbortError(error) ||
        listRequestRef.current !== operation ||
        !isCurrentProject(requestProjectId)
      ) {
        return null;
      }
      setState({ ...initialState(requestProjectId), listError: error });
      reportRequestErrorRef.current?.("Unable to load look-ahead plans", error);
      return null;
    } finally {
      if (listRequestRef.current === operation) listRequestRef.current = null;
    }
  }, [enabled, isCurrentProject, loadDetail]);

  useEffect(() => {
    mountedRef.current = true;
    projectRef.current = projectId;
    listRequestRef.current?.controller.abort();
    detailRequestRef.current?.controller.abort();
    for (const operation of mutationControllersRef.current.values()) {
      operation.controller.abort();
    }
    mutationControllersRef.current.clear();
    selectedPlanIdRef.current = null;
    setState(initialState(projectId));

    if (!enabled || !projectId) return undefined;
    const timeoutId = window.setTimeout(() => void loadPlans(), 0);
    return () => window.clearTimeout(timeoutId);
  }, [enabled, loadPlans, projectId]);

  useEffect(
    () => () => {
      mountedRef.current = false;
      projectRef.current = null;
      listRequestRef.current?.controller.abort();
      detailRequestRef.current?.controller.abort();
      for (const operation of mutationControllersRef.current.values()) {
        operation.controller.abort();
      }
      mutationControllersRef.current.clear();
    }, []
  );

  const runMutation = useCallback(
    async (key, operation, onSuccess) => {
      const requestProjectId = projectRef.current;
      if (!enabled || !requestProjectId || mutationControllersRef.current.has(key)) {
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
          setState((current) => ({ ...current, mutationError: error }));
          reportRequestErrorRef.current?.(`Unable to ${key} look-ahead plan`, error);
        }
        return null;
      } finally {
        const active = mutationControllersRef.current.get(key);
        if (active?.token === token) {
          mutationControllersRef.current.delete(key);
          if (isCurrentProject(requestProjectId)) {
            setState((current) => ({
              ...current,
              pendingActions: Array.from(mutationControllersRef.current.keys()),
            }));
          }
        }
      }
    },
    [enabled, isCurrentProject]
  );

  const createPlan = useCallback(
    (payload) =>
      runMutation(
        "create",
        (requestProjectId, signal) =>
          createLookAheadPlan(requestProjectId, payload, { signal }),
        async (data, requestProjectId) => {
          selectedPlanIdRef.current = data.plan.id;
          setState((current) => ({
            ...current,
            plans: [
              data.plan,
              ...current.plans.filter((plan) => plan.id !== data.plan.id),
            ],
            selectedPlanId: data.plan.id,
          }));
          await loadDetail(data.plan.id);
          if (isCurrentProject(requestProjectId)) {
            showNoticeRef.current?.("success", "Look-ahead plan created.");
          }
        }
      ),
    [isCurrentProject, loadDetail, runMutation]
  );

  const updatePlan = useCallback(
    (planId, payload) =>
      runMutation(
        `update:${planId}`,
        (requestProjectId, signal) =>
          updateLookAheadPlan(requestProjectId, planId, payload, { signal }),
        async (data) => {
          setState((current) => ({
            ...current,
            plans: current.plans.map((plan) =>
              plan.id === data.plan.id ? data.plan : plan
            ),
          }));
          await loadDetail(data.plan.id);
        }
      ),
    [loadDetail, runMutation]
  );

  const archivePlan = useCallback(
    (planId) =>
      runMutation(
        `archive:${planId}`,
        (requestProjectId, signal) =>
          archiveLookAheadPlan(requestProjectId, planId, { signal }),
        async (data, requestProjectId) => {
          setState((current) => ({
            ...current,
            plans: current.plans.map((plan) =>
              plan.id === data.plan.id ? data.plan : plan
            ),
          }));
          await loadDetail(data.plan.id);
          if (isCurrentProject(requestProjectId)) {
            showNoticeRef.current?.("success", "Look-ahead plan archived.");
          }
        }
      ),
    [isCurrentProject, loadDetail, runMutation]
  );

  const updateItem = useCallback(
    (planId, taskId, payload) =>
      runMutation(
        `update-item:${planId}:${taskId}`,
        (requestProjectId, signal) =>
          updateLookAheadItem(requestProjectId, planId, taskId, payload, { signal }),
        async (detail, requestProjectId) => {
          if (selectedPlanIdRef.current === planId) {
            setState((current) => ({ ...current, detail }));
          }
          if (isCurrentProject(requestProjectId)) {
            showNoticeRef.current?.("success", "Look-ahead item updated.");
          }
        }
      ),
    [isCurrentProject, runMutation]
  );

  const updateFilters = useCallback((changes) => {
    setState((current) => ({
      ...current,
      filters: { ...current.filters, ...changes },
    }));
  }, []);

  const clearFilters = useCallback(() => {
    setState((current) => ({ ...current, filters: { ...DEFAULT_FILTERS } }));
  }, []);

  const clearMutationError = useCallback(() => {
    setState((current) => ({ ...current, mutationError: null }));
  }, []);

  const current = state.projectId === projectId ? state : initialState(projectId);
  return {
    ...current,
    selectedPlan:
      current.plans.find((plan) => plan.id === current.selectedPlanId) || null,
    loadPlans,
    retryPlans: loadPlans,
    retryDetail: () => loadDetail(selectedPlanIdRef.current),
    selectPlan: loadDetail,
    createPlan,
    updatePlan,
    archivePlan,
    updateItem,
    updateFilters,
    clearFilters,
    clearMutationError,
    isCreating: current.pendingActions.includes("create"),
    isArchiving: current.pendingActions.some((key) => key.startsWith("archive:")),
    isUpdatingItem: current.pendingActions.some((key) => key.startsWith("update-item:")),
  };
}


export { DEFAULT_FILTERS };
export default useLookAheadPlans;
