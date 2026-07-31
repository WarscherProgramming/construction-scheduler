import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createFolder,
  deleteDocument,
  downloadDocument,
  exploreDocuments,
  listFolderTree,
  listRecentDocuments,
  uploadDocument,
} from "../services/api";
import {
  getSafeAttachmentFilename,
  parseDownloadFilename,
  validateAttachmentFile,
} from "../utils/attachment";


const INITIAL_QUERY = {
  folderId: null,
  search: "",
  documentType: "",
  mimeType: "",
  extension: "",
  sort: "name",
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


function useDocumentExplorer({ projectId, onError }) {
  const [query, setQuery] = useState(INITIAL_QUERY);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [explorerState, setExplorerState] = useState({
    data: null,
    identity: null,
    error: null,
    errorIdentity: null,
    isLoading: false,
  });
  const [auxiliaryState, setAuxiliaryState] = useState({
    folderTree: [],
    recentDocuments: [],
    projectId: null,
    isLoading: false,
  });
  const [operationError, setOperationError] = useState(null);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState([]);
  const [deletingIds, setDeletingIds] = useState([]);
  const [downloadingIds, setDownloadingIds] = useState([]);

  const identityKey = projectId
    ? JSON.stringify([projectId, query, refreshVersion])
    : null;
  const identityRef = useRef(identityKey);
  const projectRef = useRef(projectId);
  const onErrorRef = useRef(onError);
  const explorerRequestRef = useRef(null);
  const explorerAbortTimerRef = useRef(null);
  const auxiliaryRequestRef = useRef(null);
  const auxiliaryAbortTimerRef = useRef(null);
  const uploadPromiseRef = useRef(null);
  const uploadControllerRef = useRef(null);
  const mutationControllersRef = useRef(new Map());
  const objectUrlsRef = useRef(new Map());

  useEffect(() => {
    identityRef.current = identityKey;
    projectRef.current = projectId;
  }, [identityKey, projectId]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const reportError = useCallback((context, error) => {
    onErrorRef.current?.(context, error);
  }, []);

  const startExplorerRequest = useCallback(() => {
    if (!identityKey) return Promise.resolve(null);
    const existing = explorerRequestRef.current;
    if (
      existing?.identityKey === identityKey &&
      !existing.settled
    ) {
      return existing.promise;
    }
    if (existing && !existing.settled) existing.controller.abort();

    const controller = new AbortController();
    const record = {
      controller,
      identityKey,
      promise: null,
      settled: false,
    };
    setExplorerState((current) => ({
      ...current,
      data: null,
      identity: null,
      error: null,
      errorIdentity: null,
      isLoading: true,
    }));

    const promise = exploreDocuments(projectId, {
      ...query,
      signal: controller.signal,
    })
      .then((data) => {
        if (
          identityRef.current !== identityKey ||
          explorerRequestRef.current !== record
        ) {
          return null;
        }
        setExplorerState({
          data,
          identity: identityKey,
          error: null,
          errorIdentity: null,
          isLoading: false,
        });
        return data;
      })
      .catch((error) => {
        if (
          isAbortError(error) ||
          identityRef.current !== identityKey ||
          explorerRequestRef.current !== record
        ) {
          return null;
        }
        setExplorerState({
          data: null,
          identity: null,
          error,
          errorIdentity: identityKey,
          isLoading: false,
        });
        reportError("Unable to load project documents", error);
        return null;
      })
      .finally(() => {
        record.settled = true;
        if (explorerRequestRef.current === record) {
          explorerRequestRef.current = null;
        }
      });
    record.promise = promise;
    explorerRequestRef.current = record;
    return promise;
  }, [identityKey, projectId, query, reportError]);

  useEffect(() => {
    if (explorerAbortTimerRef.current) {
      window.clearTimeout(explorerAbortTimerRef.current);
      explorerAbortTimerRef.current = null;
    }
    if (!identityKey) return undefined;

    let requestAtSetup = null;
    const startTimer = window.setTimeout(() => {
      void startExplorerRequest();
      requestAtSetup = explorerRequestRef.current;
    }, 0);

    return () => {
      window.clearTimeout(startTimer);
      explorerAbortTimerRef.current = window.setTimeout(() => {
        if (
          requestAtSetup &&
          explorerRequestRef.current === requestAtSetup &&
          !requestAtSetup.settled
        ) {
          requestAtSetup.controller.abort();
        }
      }, 0);
    };
  }, [identityKey, startExplorerRequest]);

  const startAuxiliaryRequest = useCallback(
    ({ force = false } = {}) => {
      if (!projectId) return Promise.resolve(null);
      const existing = auxiliaryRequestRef.current;
      if (
        !force &&
        existing?.projectId === projectId &&
        !existing.settled
      ) {
        return existing.promise;
      }
      if (existing && !existing.settled) existing.controller.abort();

      const controller = new AbortController();
      const record = {
        controller,
        projectId,
        promise: null,
        settled: false,
      };
      setAuxiliaryState((current) => ({
        ...current,
        folderTree: current.projectId === projectId
          ? current.folderTree
          : [],
        recentDocuments: current.projectId === projectId
          ? current.recentDocuments
          : [],
        projectId: null,
        isLoading: true,
      }));

      const promise = Promise.all([
        listFolderTree(projectId, { signal: controller.signal }),
        listRecentDocuments(projectId, {
          limit: 8,
          signal: controller.signal,
        }),
      ])
        .then(([treeResponse, recentResponse]) => {
          if (
            projectRef.current !== projectId ||
            auxiliaryRequestRef.current !== record
          ) {
            return null;
          }
          setAuxiliaryState({
            folderTree: treeResponse?.folders || [],
            recentDocuments: recentResponse?.documents || [],
            projectId,
            isLoading: false,
          });
          return { treeResponse, recentResponse };
        })
        .catch((error) => {
          if (
            isAbortError(error) ||
            projectRef.current !== projectId ||
            auxiliaryRequestRef.current !== record
          ) {
            return null;
          }
          setAuxiliaryState({
            folderTree: [],
            recentDocuments: [],
            projectId,
            isLoading: false,
          });
          setOperationError(error);
          reportError("Unable to load document navigation", error);
          return null;
        })
        .finally(() => {
          record.settled = true;
          if (auxiliaryRequestRef.current === record) {
            auxiliaryRequestRef.current = null;
          }
        });
      record.promise = promise;
      auxiliaryRequestRef.current = record;
      return promise;
    },
    [projectId, reportError]
  );

  useEffect(() => {
    if (auxiliaryAbortTimerRef.current) {
      window.clearTimeout(auxiliaryAbortTimerRef.current);
      auxiliaryAbortTimerRef.current = null;
    }
    if (!projectId) return undefined;

    let requestAtSetup = null;
    const startTimer = window.setTimeout(() => {
      void startAuxiliaryRequest();
      requestAtSetup = auxiliaryRequestRef.current;
    }, 0);

    return () => {
      window.clearTimeout(startTimer);
      auxiliaryAbortTimerRef.current = window.setTimeout(() => {
        if (
          requestAtSetup &&
          auxiliaryRequestRef.current === requestAtSetup &&
          !requestAtSetup.settled
        ) {
          requestAtSetup.controller.abort();
        }
      }, 0);
    };
  }, [projectId, startAuxiliaryRequest]);

  useEffect(() => {
    uploadControllerRef.current?.abort();
    uploadPromiseRef.current = null;
    for (const controller of mutationControllersRef.current.values()) {
      controller.abort();
    }
    mutationControllersRef.current.clear();
  }, [projectId]);

  useEffect(
    () => () => {
      identityRef.current = null;
      projectRef.current = null;
      if (explorerAbortTimerRef.current) {
        window.clearTimeout(explorerAbortTimerRef.current);
      }
      if (auxiliaryAbortTimerRef.current) {
        window.clearTimeout(auxiliaryAbortTimerRef.current);
      }
      explorerRequestRef.current?.controller.abort();
      auxiliaryRequestRef.current?.controller.abort();
      uploadControllerRef.current?.abort();
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
    setOperationError(null);
  }, []);

  const refresh = useCallback(async () => {
    setRefreshVersion((version) => version + 1);
    await startAuxiliaryRequest({ force: true });
  }, [startAuxiliaryRequest]);

  const uploadFiles = useCallback(
    (selectedFiles) => {
      if (!projectId) return Promise.resolve([]);
      if (uploadPromiseRef.current) return uploadPromiseRef.current;

      const files = Array.from(selectedFiles || []);
      const operationProject = projectId;
      const operationFolder = query.folderId;
      const controller = new AbortController();
      uploadControllerRef.current = controller;

      const operation = (async () => {
        const results = files.map((file) => ({
          file,
          filename: getSafeAttachmentFilename(file?.name, "Document"),
          status: "pending",
          message: "Waiting",
        }));
        let successfulUploads = 0;
        setIsUploading(true);
        setUploadResults(results);
        setOperationError(null);

        for (let index = 0; index < results.length; index += 1) {
          if (
            projectRef.current !== operationProject ||
            controller.signal.aborted
          ) {
            break;
          }
          const result = results[index];
          const validationMessage = validateAttachmentFile(result.file);
          if (validationMessage) {
            results[index] = {
              ...result,
              status: "error",
              message: validationMessage,
            };
            setUploadResults([...results]);
            continue;
          }

          results[index] = {
            ...result,
            status: "uploading",
            message: "Uploading",
          };
          setUploadResults([...results]);
          try {
            await uploadDocument(operationProject, result.file, {
              folderId: operationFolder,
              signal: controller.signal,
            });
            successfulUploads += 1;
            results[index] = {
              ...result,
              status: "success",
              message: "Uploaded",
            };
          } catch (error) {
            if (isAbortError(error)) break;
            results[index] = {
              ...result,
              status: "error",
              message: error?.message || "Upload failed",
            };
            setOperationError(error);
            reportError(`Unable to upload ${result.filename}`, error);
          }
          if (projectRef.current === operationProject) {
            setUploadResults([...results]);
          }
        }

        if (
          successfulUploads > 0 &&
          projectRef.current === operationProject
        ) {
          await refresh();
        }
        return results;
      })().finally(() => {
        if (projectRef.current === operationProject) {
          setIsUploading(false);
        }
        if (uploadControllerRef.current === controller) {
          uploadControllerRef.current = null;
        }
        if (uploadPromiseRef.current === operation) {
          uploadPromiseRef.current = null;
        }
      });
      uploadPromiseRef.current = operation;
      return operation;
    },
    [projectId, query.folderId, refresh, reportError]
  );

  const retryFailedUploads = useCallback(() => {
    const failedFiles = uploadResults
      .filter((result) => result.status === "error")
      .map((result) => result.file);
    return uploadFiles(failedFiles);
  }, [uploadFiles, uploadResults]);

  const createCurrentFolder = useCallback(
    async (name) => {
      if (!projectId || isCreatingFolder) return false;
      const controller = new AbortController();
      const key = `create-folder:${projectId}`;
      mutationControllersRef.current.set(key, controller);
      setIsCreatingFolder(true);
      setOperationError(null);
      try {
        await createFolder(
          projectId,
          {
            name: name.trim(),
            parent_folder_id: query.folderId,
          },
          { signal: controller.signal }
        );
        if (
          controller.signal.aborted ||
          projectRef.current !== projectId
        ) {
          return false;
        }
        await refresh();
        return true;
      } catch (error) {
        if (!isAbortError(error)) {
          setOperationError(error);
          reportError("Unable to create folder", error);
        }
        return false;
      } finally {
        mutationControllersRef.current.delete(key);
        if (projectRef.current === projectId) setIsCreatingFolder(false);
      }
    },
    [isCreatingFolder, projectId, query.folderId, refresh, reportError]
  );

  const removeDocument = useCallback(
    async (documentRecord) => {
      if (!documentRecord?.id || deletingIds.includes(documentRecord.id)) {
        return false;
      }
      const controller = new AbortController();
      const key = `delete:${documentRecord.id}`;
      mutationControllersRef.current.set(key, controller);
      setDeletingIds((current) => [...current, documentRecord.id]);
      setOperationError(null);
      try {
        await deleteDocument(documentRecord.id, {
          signal: controller.signal,
        });
        setExplorerState((current) => {
          if (!current.data) return current;
          const documents = current.data.documents.filter(
            (item) => item.id !== documentRecord.id
          );
          return {
            ...current,
            data: {
              ...current.data,
              documents,
              pagination: {
                ...current.data.pagination,
                total: Math.max(0, current.data.pagination.total - 1),
                has_more:
                  current.data.pagination.offset + documents.length <
                  Math.max(0, current.data.pagination.total - 1),
              },
            },
          };
        });
        await refresh();
        return true;
      } catch (error) {
        if (!isAbortError(error)) {
          setOperationError(error);
          reportError(
            `Unable to delete ${documentRecord.display_name}`,
            error
          );
        }
        return false;
      } finally {
        mutationControllersRef.current.delete(key);
        setDeletingIds((current) =>
          current.filter((id) => id !== documentRecord.id)
        );
      }
    },
    [deletingIds, refresh, reportError]
  );

  const download = useCallback(
    async (documentRecord) => {
      if (!documentRecord?.id || downloadingIds.includes(documentRecord.id)) {
        return false;
      }
      const controller = new AbortController();
      const key = `download:${documentRecord.id}`;
      mutationControllersRef.current.set(key, controller);
      setDownloadingIds((current) => [...current, documentRecord.id]);
      setOperationError(null);
      let objectUrl = null;
      try {
        const response = await downloadDocument(documentRecord.id, {
          signal: controller.signal,
        });
        const fallback = getSafeAttachmentFilename(
          documentRecord.original_filename,
          "Document"
        );
        const filename = parseDownloadFilename(
          response.headers?.get?.("content-disposition"),
          fallback
        );
        objectUrl = window.URL.createObjectURL(response.blob);
        triggerDownload(objectUrl, filename);
        const timer = window.setTimeout(() => {
          window.URL.revokeObjectURL(objectUrl);
          objectUrlsRef.current.delete(objectUrl);
        }, 0);
        objectUrlsRef.current.set(objectUrl, timer);
        objectUrl = null;
        return true;
      } catch (error) {
        if (objectUrl) window.URL.revokeObjectURL(objectUrl);
        if (!isAbortError(error)) {
          setOperationError(error);
          reportError(
            `Unable to download ${documentRecord.display_name}`,
            error
          );
        }
        return false;
      } finally {
        mutationControllersRef.current.delete(key);
        setDownloadingIds((current) =>
          current.filter((id) => id !== documentRecord.id)
        );
      }
    },
    [downloadingIds, reportError]
  );

  const explorer =
    explorerState.identity === identityKey ? explorerState.data : null;
  const error =
    explorerState.errorIdentity === identityKey
      ? explorerState.error
      : null;
  const auxiliary =
    auxiliaryState.projectId === projectId
      ? auxiliaryState
      : { folderTree: [], recentDocuments: [], isLoading: true };
  const failedUploadCount = useMemo(
    () =>
      uploadResults.filter((result) => result.status === "error").length,
    [uploadResults]
  );

  return {
    explorer,
    folderTree: auxiliary.folderTree,
    recentDocuments: auxiliary.recentDocuments,
    query,
    isLoading: Boolean(
      identityKey &&
        !error &&
        (explorerState.isLoading || explorerState.identity !== identityKey)
    ),
    isNavigationLoading: auxiliary.isLoading,
    error,
    operationError,
    isCreatingFolder,
    isUploading,
    uploadResults,
    failedUploadCount,
    deletingIds,
    downloadingIds,
    updateQuery,
    refresh,
    uploadFiles,
    retryFailedUploads,
    createCurrentFolder,
    removeDocument,
    download,
    clearOperationError: () => setOperationError(null),
  };
}

export default useDocumentExplorer;
