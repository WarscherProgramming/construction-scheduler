import {
  authenticationRequest,
  authenticatedRequest,
  downloadAuthenticatedFile,
  downloadAuthenticatedResponse,
  jsonRequest,
} from "./httpClient";

export function registerUser(user) {
  return authenticationRequest("/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(user),
  });
}

export function loginUser(email, password) {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  return authenticationRequest("/auth/login", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData,
  });
}

export function fetchProjects() {
  return authenticatedRequest("/projects");
}

export function fetchProjectDashboard(projectId, asOf, options = {}) {
  const encodedProjectId = encodeURIComponent(String(projectId));
  const query = new URLSearchParams({ as_of: asOf });

  return authenticatedRequest(
    `/projects/${encodedProjectId}/dashboard?${query.toString()}`,
    { signal: options.signal }
  );
}

export function createProject(project) {
  return jsonRequest("/projects", "POST", project);
}

export function fetchTasks(projectId) {
  return authenticatedRequest(`/projects/${projectId}/tasks`);
}

export function createTask(projectId, task) {
  return jsonRequest(`/projects/${projectId}/tasks`, "POST", task);
}

export function deleteTask(projectId, id) {
  return authenticatedRequest(`/projects/${projectId}/tasks/${id}`, {
    method: "DELETE",
  });
}

export function updateTask(projectId, id, task) {
  return jsonRequest(`/projects/${projectId}/tasks/${id}`, "PUT", task);
}

export function fetchTemplates() {
  return authenticatedRequest("/templates");
}

export function saveTemplate(projectId, template) {
  return jsonRequest(`/projects/${projectId}/templates`, "POST", template);
}

export function applyTemplate(projectId, templateId) {
  return authenticatedRequest(
    `/projects/${projectId}/templates/${templateId}/apply`,
    { method: "POST" }
  );
}

export async function exportProjectPdf(projectId) {
  const blob = await downloadAuthenticatedFile(
    `/projects/${projectId}/export/pdf`
  );
  const url = window.URL.createObjectURL(blob);

  window.open(url, "_blank");
  window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
}

export function fetchDailyLogs(projectId) {
  return authenticatedRequest(`/projects/${projectId}/daily-logs`);
}

export function createDailyLog(projectId, log) {
  return jsonRequest(`/projects/${projectId}/daily-logs`, "POST", log);
}

export function fetchInspections(projectId) {
  return authenticatedRequest(`/projects/${projectId}/inspections`);
}

export function createInspection(projectId, inspection) {
  return jsonRequest(`/projects/${projectId}/inspections`, "POST", inspection);
}

export function fetchNotesDelays(projectId) {
  return authenticatedRequest(`/projects/${projectId}/notes-delays`);
}

export function createNoteDelay(projectId, entry) {
  return jsonRequest(`/projects/${projectId}/notes-delays`, "POST", entry);
}

export function fetchChangeOrders(projectId) {
  return authenticatedRequest(`/projects/${projectId}/change-orders`);
}

export function createChangeOrder(projectId, changeOrder) {
  return jsonRequest(
    `/projects/${projectId}/change-orders`,
    "POST",
    changeOrder
  );
}

export function updateChangeOrder(projectId, changeOrderId, changeOrder) {
  return jsonRequest(
    `/projects/${projectId}/change-orders/${changeOrderId}`,
    "PUT",
    changeOrder
  );
}

export function fetchProjectCompanies(projectId) {
  return authenticatedRequest(`/projects/${projectId}/companies`);
}

export function createProjectCompany(projectId, company) {
  return jsonRequest(`/projects/${projectId}/companies`, "POST", company);
}

export function deleteChangeOrder(projectId, changeOrderId) {
  return authenticatedRequest(
    `/projects/${projectId}/change-orders/${changeOrderId}`,
    { method: "DELETE" }
  );
}

export function fetchRFIs(projectId) {
  return authenticatedRequest(`/projects/${projectId}/rfis`);
}

export function createRFI(projectId, rfi) {
  return jsonRequest(`/projects/${projectId}/rfis`, "POST", rfi);
}

export function updateRFI(projectId, rfiId, rfi) {
  return jsonRequest(`/projects/${projectId}/rfis/${rfiId}`, "PUT", rfi);
}

export function deleteRFI(projectId, rfiId) {
  return authenticatedRequest(`/projects/${projectId}/rfis/${rfiId}`, {
    method: "DELETE",
  });
}

export function fetchSubmittals(projectId) {
  return authenticatedRequest(`/projects/${projectId}/submittals`);
}

export function createSubmittal(projectId, submittal) {
  return jsonRequest(`/projects/${projectId}/submittals`, "POST", submittal);
}

export function updateSubmittal(projectId, submittalId, submittal) {
  return jsonRequest(
    `/projects/${projectId}/submittals/${submittalId}`,
    "PUT",
    submittal
  );
}

export function deleteSubmittal(projectId, submittalId) {
  return authenticatedRequest(
    `/projects/${projectId}/submittals/${submittalId}`,
    { method: "DELETE" }
  );
}

export function fetchPunchItems(projectId) {
  return authenticatedRequest(`/projects/${projectId}/punch-items`);
}

export function createPunchItem(projectId, punchItem) {
  return jsonRequest(`/projects/${projectId}/punch-items`, "POST", punchItem);
}

export function updatePunchItem(projectId, punchItemId, punchItem) {
  return jsonRequest(
    `/projects/${projectId}/punch-items/${punchItemId}`,
    "PUT",
    punchItem
  );
}

export function deletePunchItem(projectId, punchItemId) {
  return authenticatedRequest(
    `/projects/${projectId}/punch-items/${punchItemId}`,
    { method: "DELETE" }
  );
}

export function reorderTasks(projectId, taskIds) {
  return jsonRequest(`/projects/${projectId}/tasks/reorder`, "PUT", {
    task_ids: taskIds,
  });
}

export function listAttachments(
  projectId,
  parentType,
  parentId,
  options = {}
) {
  const query = new URLSearchParams({
    parent_type: parentType,
    parent_id: String(parentId),
  });
  return authenticatedRequest(
    `/projects/${projectId}/attachments?${query.toString()}`,
    { signal: options.signal }
  );
}

export function uploadAttachment(
  projectId,
  parentType,
  parentId,
  file,
  options = {}
) {
  const formData = new FormData();
  formData.append("parent_type", parentType);
  formData.append("parent_id", String(parentId));
  formData.append("file", file);

  return authenticatedRequest(`/projects/${projectId}/attachments`, {
    method: "POST",
    body: formData,
    signal: options.signal,
  });
}

export function downloadAttachment(
  projectId,
  attachmentId,
  options = {}
) {
  return downloadAuthenticatedResponse(
    `/projects/${projectId}/attachments/${attachmentId}/download`,
    { signal: options.signal }
  );
}

export function deleteAttachment(
  projectId,
  attachmentId,
  options = {}
) {
  return authenticatedRequest(
    `/projects/${projectId}/attachments/${attachmentId}`,
    {
      method: "DELETE",
      signal: options.signal,
    }
  );
}

export function listDocuments(projectId, options = {}) {
  const query = new URLSearchParams();
  if (options.folderId != null) {
    query.set("folder_id", String(options.folderId));
  }
  if (options.limit != null) query.set("limit", String(options.limit));
  if (options.offset != null) query.set("offset", String(options.offset));
  const suffix = query.size ? `?${query.toString()}` : "";
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/documents${suffix}`,
    { signal: options.signal }
  );
}

export function exploreDocuments(projectId, options = {}) {
  const query = new URLSearchParams();
  const parameters = {
    folder_id: options.folderId,
    search: options.search,
    document_type: options.documentType,
    mime_type: options.mimeType,
    extension: options.extension,
    sort: options.sort,
    order: options.order,
    limit: options.limit,
    offset: options.offset,
  };
  for (const [name, value] of Object.entries(parameters)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(name, String(value));
    }
  }
  const suffix = query.size ? `?${query.toString()}` : "";
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/documents/explorer${suffix}`,
    { signal: options.signal }
  );
}

export function listRecentDocuments(projectId, options = {}) {
  const query = new URLSearchParams();
  if (options.limit != null) query.set("limit", String(options.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/documents/recent${suffix}`,
    { signal: options.signal }
  );
}

export function getDocument(documentId, options = {}) {
  return authenticatedRequest(
    `/documents/${encodeURIComponent(String(documentId))}`,
    { signal: options.signal }
  );
}

export function uploadDocument(projectId, file, options = {}) {
  const formData = new FormData();
  formData.append("project_id", String(projectId));
  if (options.folderId != null) {
    formData.append("folder_id", String(options.folderId));
  }
  if (options.displayName) {
    formData.append("display_name", options.displayName);
  }
  if (options.documentType) {
    formData.append("document_type", options.documentType);
  }
  formData.append("file", file);

  return authenticatedRequest("/documents/upload", {
    method: "POST",
    body: formData,
    signal: options.signal,
  });
}

export function downloadDocument(documentId, options = {}) {
  return downloadAuthenticatedResponse(
    `/documents/${encodeURIComponent(String(documentId))}/download`,
    { signal: options.signal }
  );
}

export function deleteDocument(documentId, options = {}) {
  return authenticatedRequest(
    `/documents/${encodeURIComponent(String(documentId))}`,
    {
      method: "DELETE",
      signal: options.signal,
    }
  );
}

export function getDocumentExtraction(projectId, documentId, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/documents/${encodeURIComponent(
      String(documentId)
    )}/extraction`,
    { signal: options.signal }
  );
}

export function reprocessDocumentExtraction(
  projectId,
  documentId,
  options = {}
) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/documents/${encodeURIComponent(
      String(documentId)
    )}/extraction/reprocess`,
    {
      method: "POST",
      body: JSON.stringify({}),
      signal: options.signal,
    }
  );
}

export function searchProjectDocuments(projectId, options = {}) {
  const query = new URLSearchParams();
  const parameters = {
    q: options.query,
    scope: options.scope,
    document_type: options.documentType,
    drawing_set_id: options.drawingSetId,
    discipline: options.discipline,
    current_revisions_only: options.currentRevisionsOnly,
    extraction_method: options.extractionMethod,
    limit: options.limit,
    offset: options.offset,
  };
  for (const [name, value] of Object.entries(parameters)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(name, String(value));
    }
  }
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/search?${query.toString()}`,
    { signal: options.signal }
  );
}

export function listFolders(projectId, options = {}) {
  const query = new URLSearchParams();
  if (options.limit != null) query.set("limit", String(options.limit));
  if (options.offset != null) query.set("offset", String(options.offset));
  const suffix = query.size ? `?${query.toString()}` : "";
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/folders${suffix}`,
    { signal: options.signal }
  );
}

export function listFolderTree(projectId, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/folders/tree`,
    { signal: options.signal }
  );
}

export function createFolder(projectId, folder, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/folders`,
    {
      method: "POST",
      body: JSON.stringify(folder),
      signal: options.signal,
    }
  );
}

function drawingQuery(options = {}) {
  const query = new URLSearchParams();
  const parameters = {
    drawing_set_id: options.drawingSetId,
    discipline: options.discipline,
    search: options.search,
    sheet_status: options.sheetStatus,
    sort: options.sort,
    order: options.order,
    limit: options.limit,
    offset: options.offset,
  };
  for (const [name, value] of Object.entries(parameters)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(name, String(value));
    }
  }
  return query.size ? `?${query.toString()}` : "";
}

export function listDrawingSets(projectId, options = {}) {
  const suffix = options.includeArchived ? "?include_archived=true" : "";
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/drawing-sets${suffix}`,
    { signal: options.signal }
  );
}

export function createDrawingSet(projectId, drawingSet, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/drawing-sets`,
    {
      method: "POST",
      body: JSON.stringify(drawingSet),
      signal: options.signal,
    }
  );
}

export function updateDrawingSet(drawingSetId, drawingSet, options = {}) {
  return authenticatedRequest(
    `/drawing-sets/${encodeURIComponent(String(drawingSetId))}`,
    {
      method: "PATCH",
      body: JSON.stringify(drawingSet),
      signal: options.signal,
    }
  );
}

export function archiveDrawingSet(drawingSetId, options = {}) {
  return authenticatedRequest(
    `/drawing-sets/${encodeURIComponent(String(drawingSetId))}`,
    { method: "DELETE", signal: options.signal }
  );
}

export function getDrawingRegister(projectId, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/drawings${drawingQuery(options)}`,
    { signal: options.signal }
  );
}

export function listDrawingSetSheets(drawingSetId, options = {}) {
  return authenticatedRequest(
    `/drawing-sets/${encodeURIComponent(String(drawingSetId))}/sheets`,
    { signal: options.signal }
  );
}

export function createDrawingSheet(
  drawingSetId,
  metadata,
  file,
  options = {}
) {
  const formData = new FormData();
  formData.append("metadata", JSON.stringify(metadata));
  formData.append("file", file);
  return authenticatedRequest(
    `/drawing-sets/${encodeURIComponent(String(drawingSetId))}/sheets`,
    {
      method: "POST",
      body: formData,
      signal: options.signal,
    }
  );
}

export function getDrawingSheet(sheetId, options = {}) {
  return authenticatedRequest(
    `/drawing-sheets/${encodeURIComponent(String(sheetId))}`,
    { signal: options.signal }
  );
}

export function updateDrawingSheet(sheetId, sheet, options = {}) {
  return authenticatedRequest(
    `/drawing-sheets/${encodeURIComponent(String(sheetId))}`,
    {
      method: "PATCH",
      body: JSON.stringify(sheet),
      signal: options.signal,
    }
  );
}

export function archiveDrawingSheet(sheetId, options = {}) {
  return authenticatedRequest(
    `/drawing-sheets/${encodeURIComponent(String(sheetId))}`,
    { method: "DELETE", signal: options.signal }
  );
}

export function listDrawingRevisions(sheetId, options = {}) {
  const query = new URLSearchParams();
  if (options.limit != null) query.set("limit", String(options.limit));
  if (options.offset != null) query.set("offset", String(options.offset));
  const suffix = query.size ? `?${query.toString()}` : "";
  return authenticatedRequest(
    `/drawing-sheets/${encodeURIComponent(String(sheetId))}/revisions${suffix}`,
    { signal: options.signal }
  );
}

export function uploadDrawingRevision(
  sheetId,
  metadata,
  file,
  options = {}
) {
  const formData = new FormData();
  formData.append("metadata", JSON.stringify(metadata));
  formData.append("file", file);
  return authenticatedRequest(
    `/drawing-sheets/${encodeURIComponent(String(sheetId))}/revisions`,
    {
      method: "POST",
      body: formData,
      signal: options.signal,
    }
  );
}

export function downloadDrawingRevision(revisionId, options = {}) {
  return downloadAuthenticatedResponse(
    `/drawing-revisions/${encodeURIComponent(String(revisionId))}/download`,
    { signal: options.signal }
  );
}

export function listDrawingIssues(drawingSetId, options = {}) {
  return authenticatedRequest(
    `/drawing-sets/${encodeURIComponent(String(drawingSetId))}/issues`,
    { signal: options.signal }
  );
}

export function createDrawingIssue(drawingSetId, issue, options = {}) {
  return authenticatedRequest(
    `/drawing-sets/${encodeURIComponent(String(drawingSetId))}/issues`,
    {
      method: "POST",
      body: JSON.stringify(issue),
      signal: options.signal,
    }
  );
}

export function updateDrawingIssue(issueId, issue, options = {}) {
  return authenticatedRequest(
    `/drawing-issues/${encodeURIComponent(String(issueId))}`,
    {
      method: "PATCH",
      body: JSON.stringify(issue),
      signal: options.signal,
    }
  );
}

export function deleteDrawingIssue(issueId, options = {}) {
  return authenticatedRequest(
    `/drawing-issues/${encodeURIComponent(String(issueId))}`,
    { method: "DELETE", signal: options.signal }
  );
}

export function addDrawingIssueRevision(
  issueId,
  revisionId,
  options = {}
) {
  return authenticatedRequest(
    `/drawing-issues/${encodeURIComponent(String(issueId))}/revisions`,
    {
      method: "POST",
      body: JSON.stringify({ revision_id: revisionId }),
      signal: options.signal,
    }
  );
}

export function removeDrawingIssueRevision(
  issueId,
  revisionId,
  options = {}
) {
  return authenticatedRequest(
    `/drawing-issues/${encodeURIComponent(String(issueId))}/revisions/${encodeURIComponent(String(revisionId))}`,
    { method: "DELETE", signal: options.signal }
  );
}

export function issueDrawingIssue(issueId, options = {}) {
  return authenticatedRequest(
    `/drawing-issues/${encodeURIComponent(String(issueId))}/issue`,
    { method: "POST", signal: options.signal }
  );
}

export function voidDrawingIssue(issueId, options = {}) {
  return authenticatedRequest(
    `/drawing-issues/${encodeURIComponent(String(issueId))}/void`,
    { method: "POST", signal: options.signal }
  );
}

function relationshipQuery(parameters) {
  const query = new URLSearchParams();
  for (const [name, value] of Object.entries(parameters)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(name, String(value));
    }
  }
  return query.toString();
}

export function listRelationships(
  projectId,
  entityType,
  entityId,
  options = {}
) {
  const query = relationshipQuery({
    entity_type: entityType,
    entity_id: entityId,
    direction: options.direction,
    relationship_type: options.relationshipType,
    related_type: options.relatedType,
    limit: options.limit,
    offset: options.offset,
  });
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/relationships?${query}`,
    { signal: options.signal }
  );
}

export function createRelationship(projectId, relationship, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/relationships`,
    {
      method: "POST",
      body: JSON.stringify(relationship),
      signal: options.signal,
    }
  );
}

export function deleteRelationship(
  projectId,
  relationshipId,
  options = {}
) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/relationships/${encodeURIComponent(String(relationshipId))}`,
    { method: "DELETE", signal: options.signal }
  );
}

export function listRelationshipCandidates(
  projectId,
  entityType,
  options = {}
) {
  const query = relationshipQuery({
    entity_type: entityType,
    search: options.search,
    limit: options.limit,
    exclude_type: options.excludeType,
    exclude_id: options.excludeId,
  });
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/relationship-candidates?${query}`,
    { signal: options.signal }
  );
}
