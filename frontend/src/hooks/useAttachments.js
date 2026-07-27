import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  deleteAttachment as deleteAttachmentRequest,
  downloadAttachment as downloadAttachmentRequest,
  listAttachments,
  uploadAttachment,
} from "../services/api";
import {
  getSafeAttachmentFilename,
  isAttachmentPreviewEligible,
  parseDownloadFilename,
  validateAttachmentFile,
} from "../utils/attachment";


function isAbortError(error) {
  return error?.name === "AbortError";
}


function operationError(operation, error, filename) {
  return {
    operation,
    filename,
    message: error?.message || "The attachment request could not be completed.",
  };
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


function useAttachments({
  projectId,
  parentType,
  parentId,
  enabled = true,
  onError,
}) {
  const isActive = Boolean(enabled && projectId && parentType && parentId);
  const identityKey = isActive
    ? `${projectId}:${parentType}:${parentId}`
    : null;

  const [storedAttachments, setStoredAttachments] = useState([]);
  const [loadedIdentity, setLoadedIdentity] = useState(null);
  const [isListLoading, setIsListLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadingFilename, setUploadingFilename] = useState("");
  const [uploadResults, setUploadResults] = useState([]);
  const [deletingIds, setDeletingIds] = useState([]);
  const [downloadingIds, setDownloadingIds] = useState([]);
  const [error, setError] = useState(null);

  const identityRef = useRef(identityKey);
  const onErrorRef = useRef(onError);
  const listVersionRef = useRef(0);
  const listRequestRef = useRef(null);
  const listAbortTimerRef = useRef(null);
  const uploadPromiseRef = useRef(null);
  const uploadControllerRef = useRef(null);
  const deleteControllersRef = useRef(new Map());
  const downloadControllersRef = useRef(new Map());
  const objectUrlsRef = useRef(new Map());

  useEffect(() => {
    identityRef.current = identityKey;
  }, [identityKey]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const reportError = useCallback((context, requestError) => {
    onErrorRef.current?.(context, requestError);
  }, []);

  const startListRequest = useCallback(
    ({ clear = false, force = false, preserveError = false } = {}) => {
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
      const requestRecord = {
        controller,
        identityKey,
        promise: null,
        settled: false,
      };

      if (clear) {
        setStoredAttachments([]);
        setLoadedIdentity(null);
      }
      setIsListLoading(true);
      if (!preserveError) {
        setError(null);
      }

      const promise = listAttachments(projectId, parentType, parentId, {
        signal: controller.signal,
      })
        .then((response) => {
          if (
            version !== listVersionRef.current ||
            identityRef.current !== identityKey
          ) {
            return [];
          }

          const nextAttachments = Array.isArray(response)
            ? response
            : response?.attachments || [];
          setStoredAttachments(nextAttachments);
          setLoadedIdentity(identityKey);
          return nextAttachments;
        })
        .catch((requestError) => {
          if (
            isAbortError(requestError) ||
            version !== listVersionRef.current ||
            identityRef.current !== identityKey
          ) {
            return [];
          }

          setStoredAttachments([]);
          setLoadedIdentity(identityKey);
          setError(operationError("list", requestError));
          reportError("Unable to load attachments", requestError);
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
    [identityKey, parentId, parentType, projectId, reportError]
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

    const resetTimer = window.setTimeout(() => {
      if (!identityKey) {
        setStoredAttachments([]);
        setLoadedIdentity(null);
        setError(null);
      }
      setUploadResults([]);
      setIsUploading(false);
      setUploadingFilename("");
      setDeletingIds([]);
      setDownloadingIds([]);
    }, 0);

    uploadControllerRef.current?.abort();
    uploadPromiseRef.current = null;
    for (const controller of deleteControllersRef.current.values()) {
      controller.abort();
    }
    for (const controller of downloadControllersRef.current.values()) {
      controller.abort();
    }
    deleteControllersRef.current.clear();
    downloadControllersRef.current.clear();

    if (!identityKey) {
      return () => window.clearTimeout(resetTimer);
    }

    let requestAtSetup = null;
    const listStartTimer = window.setTimeout(() => {
      startListRequest({ clear: true });
      requestAtSetup = listRequestRef.current;
    }, 0);

    return () => {
      window.clearTimeout(resetTimer);
      window.clearTimeout(listStartTimer);
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

  useEffect(() => {
    const urls = objectUrlsRef.current;
    return () => {
      for (const [url, timeoutId] of urls.entries()) {
        window.clearTimeout(timeoutId);
        window.URL.revokeObjectURL(url);
      }
      urls.clear();
    };
  }, []);

  useEffect(
    () => () => {
      listRequestRef.current?.controller.abort();
      uploadControllerRef.current?.abort();
      for (const controller of deleteControllersRef.current.values()) {
        controller.abort();
      }
      for (const controller of downloadControllersRef.current.values()) {
        controller.abort();
      }
    },
    []
  );

  const scheduleObjectUrlRevoke = useCallback((url, delay) => {
    const timeoutId = window.setTimeout(() => {
      window.URL.revokeObjectURL(url);
      objectUrlsRef.current.delete(url);
    }, delay);
    objectUrlsRef.current.set(url, timeoutId);
  }, []);

  const refresh = useCallback(
    () => startListRequest({ force: true }),
    [startListRequest]
  );

  const uploadFiles = useCallback(
    (selectedFiles) => {
      if (!identityKey) return Promise.resolve([]);
      if (uploadPromiseRef.current) return uploadPromiseRef.current;

      const files = Array.from(selectedFiles || []);
      const operationIdentity = identityKey;
      const controller = new AbortController();
      uploadControllerRef.current?.abort();
      uploadControllerRef.current = controller;

      const operation = (async () => {
        const results = [];
        let successfulUploads = 0;
        setIsUploading(true);
        setUploadResults([]);
        setError(null);

        for (const file of files) {
          if (identityRef.current !== operationIdentity) break;

          const validationMessage = validateAttachmentFile(file);
          if (validationMessage) {
            results.push({
              filename: getSafeAttachmentFilename(file?.name),
              status: "error",
              message: validationMessage,
            });
            setUploadResults([...results]);
            continue;
          }

          const filename = getSafeAttachmentFilename(file.name);
          setUploadingFilename(filename);

          try {
            await uploadAttachment(
              projectId,
              parentType,
              parentId,
              file,
              { signal: controller.signal }
            );
            successfulUploads += 1;
            results.push({
              filename,
              status: "success",
              message: "Uploaded",
            });
          } catch (requestError) {
            if (isAbortError(requestError)) break;
            const nextError = operationError(
              "upload",
              requestError,
              filename
            );
            results.push({
              filename,
              status: "error",
              message: nextError.message,
            });
            setError(nextError);
            reportError(`Unable to upload ${filename}`, requestError);
          }

          if (identityRef.current === operationIdentity) {
            setUploadResults([...results]);
          }
        }

        if (
          successfulUploads > 0 &&
          identityRef.current === operationIdentity
        ) {
          await startListRequest({
            force: true,
            preserveError: results.some(
              (result) => result.status === "error"
            ),
          });
        }

        return results;
      })().finally(() => {
        if (identityRef.current === operationIdentity) {
          setIsUploading(false);
          setUploadingFilename("");
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
    [
      identityKey,
      parentId,
      parentType,
      projectId,
      reportError,
      startListRequest,
    ]
  );

  const deleteAttachment = useCallback(
    async (attachment) => {
      if (!identityKey || !attachment?.id) return false;
      if (deleteControllersRef.current.has(attachment.id)) return false;

      const operationIdentity = identityKey;
      const controller = new AbortController();
      deleteControllersRef.current.set(attachment.id, controller);
      setDeletingIds((current) => [...current, attachment.id]);
      setError(null);

      try {
        await deleteAttachmentRequest(projectId, attachment.id, {
          signal: controller.signal,
        });
        if (identityRef.current === operationIdentity) {
          await startListRequest({ force: true });
        }
        return true;
      } catch (requestError) {
        if (isAbortError(requestError)) return false;
        const filename = getSafeAttachmentFilename(
          attachment.original_filename
        );
        setError(operationError("delete", requestError, filename));
        reportError(`Unable to delete ${filename}`, requestError);
        return false;
      } finally {
        if (
          deleteControllersRef.current.get(attachment.id) === controller
        ) {
          deleteControllersRef.current.delete(attachment.id);
          setDeletingIds((current) =>
            current.filter((id) => id !== attachment.id)
          );
        }
      }
    },
    [identityKey, projectId, reportError, startListRequest]
  );

  const downloadAttachment = useCallback(
    async (attachment) => {
      if (!identityKey || !attachment?.id) return null;
      if (downloadControllersRef.current.has(attachment.id)) return null;

      const controller = new AbortController();
      downloadControllersRef.current.set(attachment.id, controller);
      setDownloadingIds((current) => [...current, attachment.id]);
      setError(null);
      let pendingObjectUrl = null;

      try {
        const { blob, headers } = await downloadAttachmentRequest(
          projectId,
          attachment.id,
          { signal: controller.signal }
        );
        const fallbackName = getSafeAttachmentFilename(
          attachment.original_filename
        );
        const filename = parseDownloadFilename(
          headers?.get?.("content-disposition"),
          fallbackName
        );
        const objectUrl = window.URL.createObjectURL(blob);
        pendingObjectUrl = objectUrl;
        const mimeType = blob.type || attachment.mime_type;

        if (
          isAttachmentPreviewEligible(
            attachment.original_filename,
            mimeType
          )
        ) {
          let previewWindow = null;
          try {
            previewWindow = window.open(
              objectUrl,
              "_blank",
              "noopener,noreferrer"
            );
          } catch {
            previewWindow = null;
          }

          if (previewWindow) {
            scheduleObjectUrlRevoke(objectUrl, 60_000);
            pendingObjectUrl = null;
            return { filename, mode: "preview" };
          }
        }

        triggerDownload(objectUrl, filename);
        scheduleObjectUrlRevoke(objectUrl, 0);
        pendingObjectUrl = null;
        return { filename, mode: "download" };
      } catch (requestError) {
        if (pendingObjectUrl) {
          window.URL.revokeObjectURL(pendingObjectUrl);
        }
        if (isAbortError(requestError)) return null;
        const filename = getSafeAttachmentFilename(
          attachment.original_filename
        );
        setError(operationError("download", requestError, filename));
        reportError(`Unable to download ${filename}`, requestError);
        return null;
      } finally {
        if (
          downloadControllersRef.current.get(attachment.id) === controller
        ) {
          downloadControllersRef.current.delete(attachment.id);
          setDownloadingIds((current) =>
            current.filter((id) => id !== attachment.id)
          );
        }
      }
    },
    [identityKey, projectId, reportError, scheduleObjectUrlRevoke]
  );

  const attachments = useMemo(
    () =>
      identityKey && loadedIdentity === identityKey
        ? storedAttachments
        : [],
    [identityKey, loadedIdentity, storedAttachments]
  );
  const clearError = useCallback(() => setError(null), []);

  return {
    attachments,
    isLoading: Boolean(
      identityKey &&
        (isListLoading || loadedIdentity !== identityKey)
    ),
    isUploading,
    uploadingFilename,
    uploadResults,
    deletingIds,
    downloadingIds,
    error,
    refresh,
    uploadFiles,
    downloadAttachment,
    deleteAttachment,
    clearError,
  };
}

export default useAttachments;
