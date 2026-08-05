import { useCallback, useEffect, useRef, useState } from "react";

import {
  archiveCrew,
  archiveEquipmentResource,
  createCrew,
  createEquipmentResource,
  createResourceAvailability,
  createTaskResourceAssignment,
  deleteResourceAvailability,
  deleteTaskResourceAssignment,
  listCrews,
  listEquipmentResources,
  listResourceAvailability,
  listTaskResourceAssignments,
  updateCrew,
  updateEquipmentResource,
  updateResourceAvailability,
  updateTaskResourceAssignment,
} from "../services/api";


function initialState(projectId = null) {
  return {
    projectId,
    crews: [],
    equipment: [],
    assignments: [],
    assignmentTaskId: null,
    availability: [],
    availabilityKey: null,
    isLoading: false,
    isLoadingAssignments: false,
    isLoadingAvailability: false,
    pendingActions: [],
  };
}

function isAbortError(error) {
  return error?.name === "AbortError";
}

function useProjectResources({ projectId, enabled, showNotice, reportRequestError }) {
  const [state, setState] = useState(() => initialState(projectId));
  const projectRef = useRef(projectId);
  const mountedRef = useRef(true);
  const collectionRequestRef = useRef(null);
  const detailRequestRef = useRef(null);
  const operationsRef = useRef(new Map());
  const showNoticeRef = useRef(showNotice);
  const reportRequestErrorRef = useRef(reportRequestError);

  useEffect(() => {
    showNoticeRef.current = showNotice;
    reportRequestErrorRef.current = reportRequestError;
  }, [reportRequestError, showNotice]);

  const isCurrent = useCallback(
    (requestProjectId) => mountedRef.current && projectRef.current === requestProjectId,
    []
  );

  const loadResources = useCallback(async () => {
    const requestProjectId = projectRef.current;
    if (!enabled || !requestProjectId) return null;
    collectionRequestRef.current?.abort();
    const controller = new AbortController();
    collectionRequestRef.current = controller;
    setState((current) => ({
      ...(current.projectId === requestProjectId ? current : initialState(requestProjectId)),
      isLoading: true,
    }));
    try {
      const [crewData, equipmentData] = await Promise.all([
        listCrews(requestProjectId, { status: "all", signal: controller.signal }),
        listEquipmentResources(requestProjectId, { status: "all", signal: controller.signal }),
      ]);
      if (!isCurrent(requestProjectId) || controller.signal.aborted) return null;
      setState((current) => ({
        ...current,
        crews: crewData.crews,
        equipment: equipmentData.equipment,
        isLoading: false,
      }));
      return { crews: crewData.crews, equipment: equipmentData.equipment };
    } catch (error) {
      if (!isAbortError(error) && isCurrent(requestProjectId)) {
        setState((current) => ({ ...current, isLoading: false }));
        reportRequestErrorRef.current?.("Unable to load project resources", error);
      }
      return null;
    }
  }, [enabled, isCurrent]);

  useEffect(() => {
    mountedRef.current = true;
    projectRef.current = projectId;
    collectionRequestRef.current?.abort();
    detailRequestRef.current?.abort();
    for (const operation of operationsRef.current.values()) operation.abort();
    operationsRef.current.clear();
    if (!enabled || !projectId) return undefined;
    const timeoutId = window.setTimeout(() => void loadResources(), 0);
    return () => window.clearTimeout(timeoutId);
  }, [enabled, loadResources, projectId]);

  useEffect(() => () => {
    mountedRef.current = false;
    collectionRequestRef.current?.abort();
    detailRequestRef.current?.abort();
    for (const operation of operationsRef.current.values()) operation.abort();
  }, []);

  const runMutation = useCallback(async (key, label, operation, after) => {
    const requestProjectId = projectRef.current;
    if (!enabled || !requestProjectId || operationsRef.current.has(key)) return null;
    const controller = new AbortController();
    operationsRef.current.set(key, controller);
    setState((current) => ({ ...current, pendingActions: [...operationsRef.current.keys()] }));
    try {
      const data = await operation(requestProjectId, controller.signal);
      if (!isCurrent(requestProjectId) || controller.signal.aborted) return null;
      await after?.(data);
      showNoticeRef.current?.("success", label);
      return data;
    } catch (error) {
      if (!isAbortError(error) && isCurrent(requestProjectId)) {
        reportRequestErrorRef.current?.(label.replace(/\.$/, ""), error);
      }
      return null;
    } finally {
      if (operationsRef.current.get(key) === controller) operationsRef.current.delete(key);
      if (isCurrent(requestProjectId)) {
        setState((current) => ({ ...current, pendingActions: [...operationsRef.current.keys()] }));
      }
    }
  }, [enabled, isCurrent]);

  const mutateResource = useCallback((key, label, operation) =>
    runMutation(key, label, operation, loadResources), [loadResources, runMutation]);

  const loadAssignments = useCallback(async (taskId) => {
    const requestProjectId = projectRef.current;
    detailRequestRef.current?.abort();
    if (!enabled || !requestProjectId || !taskId) return null;
    const controller = new AbortController();
    detailRequestRef.current = controller;
    setState((current) => ({
      ...current,
      assignmentTaskId: taskId,
      assignments: [],
      isLoadingAssignments: true,
    }));
    try {
      const data = await listTaskResourceAssignments(requestProjectId, taskId, {
        signal: controller.signal,
      });
      if (!isCurrent(requestProjectId) || controller.signal.aborted) return null;
      setState((current) => ({ ...current, assignments: data.assignments, isLoadingAssignments: false }));
      return data;
    } catch (error) {
      if (!isAbortError(error) && isCurrent(requestProjectId)) {
        setState((current) => ({ ...current, isLoadingAssignments: false }));
        reportRequestErrorRef.current?.("Unable to load task resources", error);
      }
      return null;
    }
  }, [enabled, isCurrent]);

  const loadAvailability = useCallback(async (resourceType, resourceId) => {
    const requestProjectId = projectRef.current;
    detailRequestRef.current?.abort();
    if (!enabled || !requestProjectId || !resourceId) return null;
    const key = `${resourceType}:${resourceId}`;
    const controller = new AbortController();
    detailRequestRef.current = controller;
    setState((current) => ({
      ...current,
      availabilityKey: key,
      availability: [],
      isLoadingAvailability: true,
    }));
    try {
      const data = await listResourceAvailability(
        requestProjectId,
        resourceType,
        resourceId,
        { signal: controller.signal }
      );
      if (!isCurrent(requestProjectId) || controller.signal.aborted) return null;
      setState((current) => ({ ...current, availability: data.availability, isLoadingAvailability: false }));
      return data;
    } catch (error) {
      if (!isAbortError(error) && isCurrent(requestProjectId)) {
        setState((current) => ({ ...current, isLoadingAvailability: false }));
        reportRequestErrorRef.current?.("Unable to load resource availability", error);
      }
      return null;
    }
  }, [enabled, isCurrent]);

  const refreshAssignments = (taskId) => async () => loadAssignments(taskId);
  const refreshAvailability = (type, id) => async () => loadAvailability(type, id);

  const current = enabled && state.projectId === projectId
    ? state
    : initialState(projectId);
  return {
    ...current,
    loadResources,
    loadAssignments,
    loadAvailability,
    createCrew: (payload) => mutateResource("create-crew", "Crew created.", (id, signal) => createCrew(id, payload, { signal })),
    updateCrew: (id, payload) => mutateResource(`update-crew:${id}`, "Crew updated.", (project, signal) => updateCrew(project, id, payload, { signal })),
    archiveCrew: (id) => mutateResource(`archive-crew:${id}`, "Crew archived.", (project, signal) => archiveCrew(project, id, { signal })),
    createEquipment: (payload) => mutateResource("create-equipment", "Equipment created.", (id, signal) => createEquipmentResource(id, payload, { signal })),
    updateEquipment: (id, payload) => mutateResource(`update-equipment:${id}`, "Equipment updated.", (project, signal) => updateEquipmentResource(project, id, payload, { signal })),
    archiveEquipment: (id) => mutateResource(`archive-equipment:${id}`, "Equipment archived.", (project, signal) => archiveEquipmentResource(project, id, { signal })),
    createAssignment: (taskId, payload) => runMutation(`create-assignment:${taskId}`, "Resource assigned.", (project, signal) => createTaskResourceAssignment(project, taskId, payload, { signal }), refreshAssignments(taskId)),
    updateAssignment: (taskId, id, payload) => runMutation(`update-assignment:${id}`, "Assignment updated.", (project, signal) => updateTaskResourceAssignment(project, taskId, id, payload, { signal }), refreshAssignments(taskId)),
    deleteAssignment: (taskId, id) => runMutation(`delete-assignment:${id}`, "Assignment removed.", (project, signal) => deleteTaskResourceAssignment(project, taskId, id, { signal }), refreshAssignments(taskId)),
    createAvailability: (type, id, payload) => runMutation(`create-availability:${type}:${id}`, "Availability added.", (project, signal) => createResourceAvailability(project, type, id, payload, { signal }), refreshAvailability(type, id)),
    updateAvailability: (type, id, rowId, payload) => runMutation(`update-availability:${rowId}`, "Availability updated.", (project, signal) => updateResourceAvailability(project, type, id, rowId, payload, { signal }), refreshAvailability(type, id)),
    deleteAvailability: (type, id, rowId) => runMutation(`delete-availability:${rowId}`, "Availability removed.", (project, signal) => deleteResourceAvailability(project, type, id, rowId, { signal }), refreshAvailability(type, id)),
    isPending: (prefix) => current.pendingActions.some((key) => key.startsWith(prefix)),
  };
}


export default useProjectResources;
