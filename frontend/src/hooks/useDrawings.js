import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  addDrawingIssueRevision,
  archiveDrawingSet,
  archiveDrawingSheet,
  createDrawingIssue,
  createDrawingSet,
  createDrawingSheet,
  deleteDrawingIssue,
  downloadDrawingRevision,
  getDrawingRegister,
  issueDrawingIssue,
  listDrawingIssues,
  listDrawingRevisions,
  listDrawingSets,
  listDrawingSetSheets,
  removeDrawingIssueRevision,
  updateDrawingIssue,
  updateDrawingSet,
  updateDrawingSheet,
  uploadDrawingRevision,
  voidDrawingIssue,
} from "../services/api";
import {
  getSafeAttachmentFilename,
  parseDownloadFilename,
} from "../utils/attachment";


const INITIAL_QUERY = {
  drawingSetId: "",
  discipline: "",
  search: "",
  sheetStatus: "",
  sort: "sheet_number",
  order: "asc",
  limit: 50,
  offset: 0,
};


function isAbortError(error) {
  return error?.name === "AbortError";
}


function triggerDownload(url, filename) {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
}


function useDrawings({ projectId, onError }) {
  const [query, setQuery] = useState(INITIAL_QUERY);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [drawingSets, setDrawingSets] = useState([]);
  const [setsProjectId, setSetsProjectId] = useState(null);
  const [register, setRegister] = useState(null);
  const [registerIdentity, setRegisterIdentity] = useState(null);
  const [selectedSetId, setSelectedSetId] = useState(null);
  const [setSheets, setSetSheets] = useState([]);
  const [issues, setIssues] = useState([]);
  const [setDetailIdentity, setSetDetailIdentity] = useState(null);
  const [revisions, setRevisions] = useState([]);
  const [revisionSheetId, setRevisionSheetId] = useState(null);
  const [isLoadingRevisions, setIsLoadingRevisions] = useState(false);
  const [operationError, setOperationError] = useState(null);
  const [activeOperations, setActiveOperations] = useState([]);

  const projectRef = useRef(projectId);
  const onErrorRef = useRef(onError);
  const requestsRef = useRef(new Map());
  const mutationControllersRef = useRef(new Map());
  const objectUrlsRef = useRef(new Map());
  const activeOperationsRef = useRef(new Set());

  const registerKey = projectId
    ? JSON.stringify([projectId, query, refreshVersion])
    : null;
  const detailKey =
    projectId && selectedSetId
      ? `${projectId}:${selectedSetId}:${refreshVersion}`
      : null;

  useEffect(() => {
    projectRef.current = projectId;
    onErrorRef.current = onError;
  }, [projectId, onError]);

  const reportError = useCallback((context, error) => {
    if (!isAbortError(error)) onErrorRef.current?.(context, error);
  }, []);

  const beginOperation = useCallback((key) => {
    if (activeOperationsRef.current.has(key)) return false;
    activeOperationsRef.current.add(key);
    setActiveOperations([...activeOperationsRef.current]);
    return true;
  }, []);

  const endOperation = useCallback((key) => {
    activeOperationsRef.current.delete(key);
    setActiveOperations([...activeOperationsRef.current]);
  }, []);

  const runMutation = useCallback(
    async (key, context, operation, { refresh = true } = {}) => {
      if (!beginOperation(key)) return null;
      const controller = new AbortController();
      mutationControllersRef.current.set(key, controller);
      setOperationError(null);
      try {
        const result = await operation(controller.signal);
        if (controller.signal.aborted) return null;
        if (refresh) setRefreshVersion((value) => value + 1);
        return result;
      } catch (error) {
        if (!isAbortError(error)) {
          setOperationError(error);
          reportError(context, error);
        }
        return null;
      } finally {
        mutationControllersRef.current.delete(key);
        endOperation(key);
      }
    },
    [beginOperation, endOperation, reportError]
  );

  useEffect(() => {
    if (!projectId) return undefined;
    let controller = null;
    const startTimer = window.setTimeout(() => {
      controller = new AbortController();
      requestsRef.current.get("sets")?.abort();
      requestsRef.current.set("sets", controller);
      void listDrawingSets(projectId, { signal: controller.signal })
        .then((response) => {
          if (
            controller.signal.aborted ||
            projectRef.current !== projectId
          ) {
            return;
          }
          const sets = response?.drawing_sets || [];
          setDrawingSets(sets);
          setSetsProjectId(projectId);
          setSelectedSetId((current) =>
            current && sets.some((item) => item.id === current)
              ? current
              : sets[0]?.id ?? null
          );
        })
        .catch((error) => {
          if (isAbortError(error)) return;
          setDrawingSets([]);
          setSetsProjectId(projectId);
          setOperationError(error);
          reportError("Unable to load drawing sets", error);
        })
        .finally(() => {
          if (requestsRef.current.get("sets") === controller) {
            requestsRef.current.delete("sets");
          }
        });
    }, 0);
    return () => {
      window.clearTimeout(startTimer);
      controller?.abort();
    };
  }, [projectId, refreshVersion, reportError]);

  useEffect(() => {
    if (!registerKey) return undefined;
    let controller = null;
    const startTimer = window.setTimeout(() => {
      controller = new AbortController();
      requestsRef.current.get("register")?.abort();
      requestsRef.current.set("register", controller);
      void getDrawingRegister(projectId, {
        ...query,
        signal: controller.signal,
      })
        .then((response) => {
          if (
            controller.signal.aborted ||
            projectRef.current !== projectId
          ) {
            return;
          }
          setRegister(response);
          setRegisterIdentity(registerKey);
        })
        .catch((error) => {
          if (isAbortError(error)) return;
          setRegister(null);
          setRegisterIdentity(registerKey);
          setOperationError(error);
          reportError("Unable to load drawing register", error);
        })
        .finally(() => {
          if (requestsRef.current.get("register") === controller) {
            requestsRef.current.delete("register");
          }
        });
    }, 0);
    return () => {
      window.clearTimeout(startTimer);
      controller?.abort();
    };
  }, [projectId, query, refreshVersion, registerKey, reportError]);

  useEffect(() => {
    if (!detailKey) return undefined;
    let controller = null;
    const startTimer = window.setTimeout(() => {
      controller = new AbortController();
      requestsRef.current.get("set-details")?.abort();
      requestsRef.current.set("set-details", controller);
      void Promise.all([
        listDrawingSetSheets(selectedSetId, {
          signal: controller.signal,
        }),
        listDrawingIssues(selectedSetId, {
          signal: controller.signal,
        }),
      ])
        .then(([sheetResponse, issueResponse]) => {
          if (
            controller.signal.aborted ||
            projectRef.current !== projectId
          ) {
            return;
          }
          setSetSheets(sheetResponse?.sheets || []);
          setIssues(issueResponse?.issues || []);
          setSetDetailIdentity(detailKey);
        })
        .catch((error) => {
          if (isAbortError(error)) return;
          setSetSheets([]);
          setIssues([]);
          setSetDetailIdentity(detailKey);
          setOperationError(error);
          reportError("Unable to load drawing set details", error);
        })
        .finally(() => {
          if (requestsRef.current.get("set-details") === controller) {
            requestsRef.current.delete("set-details");
          }
        });
    }, 0);
    return () => {
      window.clearTimeout(startTimer);
      controller?.abort();
    };
  }, [detailKey, projectId, reportError, selectedSetId]);

  useEffect(
    () => () => {
      projectRef.current = null;
      for (const controller of requestsRef.current.values()) {
        controller.abort();
      }
      for (const controller of mutationControllersRef.current.values()) {
        controller.abort();
      }
      for (const [url, timer] of objectUrlsRef.current.entries()) {
        window.clearTimeout(timer);
        window.URL.revokeObjectURL(url);
      }
    },
    []
  );

  const updateQuery = useCallback((changes) => {
    setQuery((current) => ({
      ...current,
      ...changes,
      offset: changes.offset ?? 0,
    }));
  }, []);

  const loadRevisions = useCallback(
    async (sheetId) => {
      const controller = new AbortController();
      requestsRef.current.get("revisions")?.abort();
      requestsRef.current.set("revisions", controller);
      setIsLoadingRevisions(true);
      setRevisionSheetId(sheetId);
      try {
        const response = await listDrawingRevisions(sheetId, {
          limit: 100,
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setRevisions(response?.revisions || []);
        }
        return response?.revisions || [];
      } catch (error) {
        if (!isAbortError(error)) {
          setOperationError(error);
          reportError("Unable to load revision history", error);
        }
        return [];
      } finally {
        if (requestsRef.current.get("revisions") === controller) {
          requestsRef.current.delete("revisions");
          setIsLoadingRevisions(false);
        }
      }
    },
    [reportError]
  );

  const downloadRevision = useCallback(
    (revision) =>
      runMutation(
        `download:${revision.id}`,
        `Unable to download revision ${revision.revision_code}`,
        async (signal) => {
          const response = await downloadDrawingRevision(revision.id, {
            signal,
          });
          const fallback = getSafeAttachmentFilename(
            revision.original_filename,
            "Drawing.pdf"
          );
          const filename = parseDownloadFilename(
            response.headers?.get?.("content-disposition"),
            fallback
          );
          const url = window.URL.createObjectURL(response.blob);
          triggerDownload(url, filename);
          const timer = window.setTimeout(() => {
            window.URL.revokeObjectURL(url);
            objectUrlsRef.current.delete(url);
          }, 0);
          objectUrlsRef.current.set(url, timer);
          return true;
        },
        { refresh: false }
      ),
    [runMutation]
  );

  const actions = useMemo(
    () => ({
      createSet: (payload) =>
        runMutation("create-set", "Unable to create drawing set", (signal) =>
          createDrawingSet(projectId, payload, { signal })
        ),
      updateSet: (id, payload) =>
        runMutation(`update-set:${id}`, "Unable to update drawing set", (signal) =>
          updateDrawingSet(id, payload, { signal })
        ),
      archiveSet: (id) =>
        runMutation(`archive-set:${id}`, "Unable to archive drawing set", (signal) =>
          archiveDrawingSet(id, { signal })
        ),
      createSheet: (setId, metadata, file) =>
        runMutation("create-sheet", "Unable to create drawing sheet", (signal) =>
          createDrawingSheet(setId, metadata, file, { signal })
        ),
      updateSheet: (id, payload) =>
        runMutation(`update-sheet:${id}`, "Unable to update drawing sheet", (signal) =>
          updateDrawingSheet(id, payload, { signal })
        ),
      archiveSheet: (id) =>
        runMutation(`archive-sheet:${id}`, "Unable to archive drawing sheet", (signal) =>
          archiveDrawingSheet(id, { signal })
        ),
      uploadRevision: (sheetId, metadata, file) =>
        runMutation(
          `upload-revision:${sheetId}`,
          "Unable to upload drawing revision",
          (signal) =>
            uploadDrawingRevision(sheetId, metadata, file, { signal })
        ),
      createIssue: (setId, payload) =>
        runMutation("create-issue", "Unable to create drawing issue", (signal) =>
          createDrawingIssue(setId, payload, { signal })
        ),
      updateIssue: (id, payload) =>
        runMutation(`update-issue:${id}`, "Unable to update drawing issue", (signal) =>
          updateDrawingIssue(id, payload, { signal })
        ),
      deleteIssue: (id) =>
        runMutation(`delete-issue:${id}`, "Unable to delete drawing issue", (signal) =>
          deleteDrawingIssue(id, { signal })
        ),
      addIssueRevision: (issueId, revisionId) =>
        runMutation(
          `issue-add:${issueId}`,
          "Unable to add drawing revision to issue",
          (signal) =>
            addDrawingIssueRevision(issueId, revisionId, { signal })
        ),
      removeIssueRevision: (issueId, revisionId) =>
        runMutation(
          `issue-remove:${issueId}:${revisionId}`,
          "Unable to remove drawing revision from issue",
          (signal) =>
            removeDrawingIssueRevision(issueId, revisionId, { signal })
        ),
      issueIssue: (id) =>
        runMutation(`issue:${id}`, "Unable to issue drawing set", (signal) =>
          issueDrawingIssue(id, { signal })
        ),
      voidIssue: (id) =>
        runMutation(`void:${id}`, "Unable to void drawing issue", (signal) =>
          voidDrawingIssue(id, { signal })
        ),
    }),
    [projectId, runMutation]
  );

  return {
    query,
    drawingSets: setsProjectId === projectId ? drawingSets : [],
    register: registerIdentity === registerKey ? register : null,
    selectedSetId,
    setSheets: setDetailIdentity === detailKey ? setSheets : [],
    issues: setDetailIdentity === detailKey ? issues : [],
    revisions,
    revisionSheetId,
    isLoadingSets: Boolean(projectId && setsProjectId !== projectId),
    isLoadingRegister: Boolean(
      registerKey && registerIdentity !== registerKey
    ),
    isLoadingSetDetails: Boolean(
      detailKey && setDetailIdentity !== detailKey
    ),
    isLoadingRevisions,
    operationError,
    activeOperations,
    updateQuery,
    setSelectedSetId,
    loadRevisions,
    downloadRevision,
    refresh: () => setRefreshVersion((value) => value + 1),
    clearOperationError: () => setOperationError(null),
    ...actions,
  };
}

export default useDrawings;
