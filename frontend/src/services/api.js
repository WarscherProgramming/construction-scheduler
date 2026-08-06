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

export function fetchTasks(projectId, options = {}) {
  const path = `/projects/${projectId}/tasks`;
  return options.signal
    ? authenticatedRequest(path, { signal: options.signal })
    : authenticatedRequest(path);
}

export function fetchScheduleHealth(projectId, options = {}) {
  const query = new URLSearchParams();
  if (options.baselineId) {
    query.set("baseline_id", String(options.baselineId));
  }
  const suffix = query.size ? `?${query}` : "";
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/schedule-health${suffix}`,
    { signal: options.signal }
  );
}

export function createTask(projectId, task, options = {}) {
  return jsonRequest(`/projects/${projectId}/tasks`, "POST", task, options);
}

export function deleteTask(projectId, id, options = {}) {
  return authenticatedRequest(`/projects/${projectId}/tasks/${id}`, {
    method: "DELETE",
    signal: options.signal,
  });
}

export function updateTask(projectId, id, task, options = {}) {
  return jsonRequest(
    `/projects/${projectId}/tasks/${id}`,
    "PUT",
    task,
    options
  );
}

export function updateTaskProgress(projectId, id, progress, options = {}) {
  return jsonRequest(
    `/projects/${projectId}/tasks/${id}/progress`,
    "PUT",
    progress,
    options
  );
}

export function fetchScheduleSettings(projectId) {
  return authenticatedRequest(`/projects/${projectId}/schedule-settings`);
}

export function updateScheduleSettings(projectId, settings, options = {}) {
  return jsonRequest(
    `/projects/${projectId}/schedule-settings`,
    "PUT",
    settings,
    options
  );
}

export function listScheduleBaselines(projectId, options = {}) {
  const query = new URLSearchParams({
    status: options.status || "all",
    limit: String(options.limit || 100),
    offset: String(options.offset || 0),
  });
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/schedule-baselines?${query}`,
    { signal: options.signal }
  );
}

export function createScheduleBaseline(
  projectId,
  baseline,
  options = {}
) {
  return jsonRequest(
    `/projects/${encodeURIComponent(String(projectId))}/schedule-baselines`,
    "POST",
    baseline,
    options
  );
}

export function getScheduleBaseline(projectId, baselineId, options = {}) {
  const query = new URLSearchParams({
    limit: String(options.limit || 100),
    offset: String(options.offset || 0),
  });
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/schedule-baselines/${encodeURIComponent(String(baselineId))}?${query}`,
    { signal: options.signal }
  );
}

export function archiveScheduleBaseline(projectId, baselineId, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/schedule-baselines/${encodeURIComponent(String(baselineId))}/archive`,
    { method: "POST", signal: options.signal }
  );
}

export function selectScheduleBaseline(projectId, baselineId, options = {}) {
  return jsonRequest(
    `/projects/${encodeURIComponent(String(projectId))}/schedule-baseline-comparison`,
    "PUT",
    { baseline_id: baselineId },
    options
  );
}

export function fetchScheduleVariance(projectId, options = {}) {
  const query = new URLSearchParams();
  if (options.baselineId) query.set("baseline_id", String(options.baselineId));
  query.set("include_summaries", String(options.includeSummaries !== false));
  if (options.status) query.set("status", options.status);
  if (options.criticalChange) {
    query.set("critical_change", options.criticalChange);
  }
  if (options.search) query.set("search", options.search);
  query.set("sort", options.sort || "wbs");
  query.set("order", options.order || "asc");
  query.set("limit", String(options.limit || 50));
  query.set("offset", String(options.offset || 0));
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/schedule-variance?${query}`,
    { signal: options.signal }
  );
}

export function listLookAheadPlans(projectId, options = {}) {
  const query = new URLSearchParams({
    status: options.status || "all",
    limit: String(options.limit || 100),
    offset: String(options.offset || 0),
  });
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/look-ahead-plans?${query}`,
    { signal: options.signal }
  );
}

export function createLookAheadPlan(projectId, plan, options = {}) {
  return jsonRequest(
    `/projects/${encodeURIComponent(String(projectId))}/look-ahead-plans`,
    "POST",
    plan,
    options
  );
}

export function getLookAheadPlan(projectId, planId, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/look-ahead-plans/${encodeURIComponent(String(planId))}`,
    { signal: options.signal }
  );
}

export function updateLookAheadPlan(
  projectId,
  planId,
  plan,
  options = {}
) {
  return jsonRequest(
    `/projects/${encodeURIComponent(String(projectId))}/look-ahead-plans/${encodeURIComponent(String(planId))}`,
    "PUT",
    plan,
    options
  );
}

export function archiveLookAheadPlan(projectId, planId, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/look-ahead-plans/${encodeURIComponent(String(planId))}/archive`,
    { method: "POST", signal: options.signal }
  );
}

export function updateLookAheadItem(
  projectId,
  planId,
  taskId,
  item,
  options = {}
) {
  return jsonRequest(
    `/projects/${encodeURIComponent(String(projectId))}/look-ahead-plans/${encodeURIComponent(String(planId))}/items/${encodeURIComponent(String(taskId))}`,
    "PUT",
    item,
    options
  );
}

function resourceCollectionQuery(options = {}) {
  return new URLSearchParams({
    status: options.status || "all",
    limit: String(options.limit || 200),
    offset: String(options.offset || 0),
  });
}

export function listCrews(projectId, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/crews?${resourceCollectionQuery(options)}`,
    { signal: options.signal }
  );
}

export function createCrew(projectId, crew, options = {}) {
  return jsonRequest(`/projects/${projectId}/crews`, "POST", crew, options);
}

export function updateCrew(projectId, crewId, crew, options = {}) {
  return jsonRequest(
    `/projects/${projectId}/crews/${crewId}`,
    "PUT",
    crew,
    options
  );
}

export function archiveCrew(projectId, crewId, options = {}) {
  return authenticatedRequest(`/projects/${projectId}/crews/${crewId}/archive`, {
    method: "POST",
    signal: options.signal,
  });
}

export function listEquipmentResources(projectId, options = {}) {
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/equipment-resources?${resourceCollectionQuery(options)}`,
    { signal: options.signal }
  );
}

export function createEquipmentResource(projectId, equipment, options = {}) {
  return jsonRequest(
    `/projects/${projectId}/equipment-resources`,
    "POST",
    equipment,
    options
  );
}

export function updateEquipmentResource(
  projectId,
  equipmentId,
  equipment,
  options = {}
) {
  return jsonRequest(
    `/projects/${projectId}/equipment-resources/${equipmentId}`,
    "PUT",
    equipment,
    options
  );
}

export function archiveEquipmentResource(projectId, equipmentId, options = {}) {
  return authenticatedRequest(
    `/projects/${projectId}/equipment-resources/${equipmentId}/archive`,
    { method: "POST", signal: options.signal }
  );
}

export function listTaskResourceAssignments(projectId, taskId, options = {}) {
  return authenticatedRequest(
    `/projects/${projectId}/tasks/${taskId}/resource-assignments`,
    { signal: options.signal }
  );
}

export function createTaskResourceAssignment(
  projectId,
  taskId,
  assignment,
  options = {}
) {
  return jsonRequest(
    `/projects/${projectId}/tasks/${taskId}/resource-assignments`,
    "POST",
    assignment,
    options
  );
}

export function updateTaskResourceAssignment(
  projectId,
  taskId,
  assignmentId,
  assignment,
  options = {}
) {
  return jsonRequest(
    `/projects/${projectId}/tasks/${taskId}/resource-assignments/${assignmentId}`,
    "PUT",
    assignment,
    options
  );
}

export function deleteTaskResourceAssignment(
  projectId,
  taskId,
  assignmentId,
  options = {}
) {
  return authenticatedRequest(
    `/projects/${projectId}/tasks/${taskId}/resource-assignments/${assignmentId}`,
    { method: "DELETE", signal: options.signal }
  );
}

export function listResourceAvailability(
  projectId,
  resourceType,
  resourceId,
  options = {}
) {
  const query = new URLSearchParams({
    limit: String(options.limit || 200),
    offset: String(options.offset || 0),
  });
  return authenticatedRequest(
    `/projects/${projectId}/resources/${resourceType}/${resourceId}/availability?${query}`,
    { signal: options.signal }
  );
}

export function createResourceAvailability(
  projectId,
  resourceType,
  resourceId,
  availability,
  options = {}
) {
  return jsonRequest(
    `/projects/${projectId}/resources/${resourceType}/${resourceId}/availability`,
    "POST",
    availability,
    options
  );
}

export function updateResourceAvailability(
  projectId,
  resourceType,
  resourceId,
  availabilityId,
  availability,
  options = {}
) {
  return jsonRequest(
    `/projects/${projectId}/resources/${resourceType}/${resourceId}/availability/${availabilityId}`,
    "PUT",
    availability,
    options
  );
}

export function deleteResourceAvailability(
  projectId,
  resourceType,
  resourceId,
  availabilityId,
  options = {}
) {
  return authenticatedRequest(
    `/projects/${projectId}/resources/${resourceType}/${resourceId}/availability/${availabilityId}`,
    { method: "DELETE", signal: options.signal }
  );
}

export function fetchResourceLoading(projectId, filters = {}, options = {}) {
  const query = new URLSearchParams();
  if (filters.startDate) query.set("start_date", filters.startDate);
  if (filters.endDate) query.set("end_date", filters.endDate);
  if (filters.resourceType) query.set("resource_type", filters.resourceType);
  if (filters.resourceId) query.set("resource_id", String(filters.resourceId));
  if (filters.companyId) query.set("company_id", String(filters.companyId));
  if (filters.trade) query.set("trade", filters.trade);
  query.set("over_allocated_only", String(Boolean(filters.overAllocatedOnly)));
  query.set("include_unassigned", String(filters.includeUnassigned !== false));
  query.set("limit", String(filters.limit || 200));
  query.set("offset", String(filters.offset || 0));
  return authenticatedRequest(
    `/projects/${encodeURIComponent(String(projectId))}/resource-loading?${query}`,
    { signal: options.signal }
  );
}

export function fetchTemplates() {
  return authenticatedRequest("/templates");
}

export function saveTemplate(projectId, template) {
  return jsonRequest(`/projects/${projectId}/templates`, "POST", template);
}

export function applyTemplate(projectId, templateId, options = {}) {
  return authenticatedRequest(
    `/projects/${projectId}/templates/${templateId}/apply`,
    { method: "POST", signal: options.signal }
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

export function reorderTasks(projectId, taskIds, options = {}) {
  return jsonRequest(`/projects/${projectId}/tasks/reorder`, "PUT", {
    task_ids: taskIds,
  }, options);
}

export async function exportScheduleExecutivePdf(projectId, options = {}) {
  const query = new URLSearchParams();
  if (options.baselineId) {
    query.set("baseline_id", String(options.baselineId));
  }
  const suffix = query.size ? `?${query}` : "";
  const blob = await downloadAuthenticatedFile(
    `/projects/${encodeURIComponent(String(projectId))}/reports/schedule-executive.pdf${suffix}`
  );
  const url = window.URL.createObjectURL(blob);
  window.open(url, "_blank");
  window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
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

function preconstructionPath(projectId, suffix = "") {
  return `/projects/${encodeURIComponent(String(projectId))}/preconstruction${suffix}`;
}

function preconstructionQuery(values) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }
  return query.size ? `?${query.toString()}` : "";
}

export function listPreconstructionReviewSets(projectId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/review-sets${preconstructionQuery({
        state: options.state,
        limit: options.limit,
        offset: options.offset,
      })}`
    ),
    { signal: options.signal }
  );
}

export function createPreconstructionReviewSet(projectId, reviewSet, options = {}) {
  return authenticatedRequest(preconstructionPath(projectId, "/review-sets"), {
    method: "POST",
    body: JSON.stringify(reviewSet),
    signal: options.signal,
  });
}

export function getPreconstructionReviewSet(projectId, reviewSetId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/review-sets/${encodeURIComponent(String(reviewSetId))}`),
    { signal: options.signal }
  );
}

export function updatePreconstructionReviewSet(projectId, reviewSetId, reviewSet, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/review-sets/${encodeURIComponent(String(reviewSetId))}`),
    { method: "PUT", body: JSON.stringify(reviewSet), signal: options.signal }
  );
}

export function archivePreconstructionReviewSet(projectId, reviewSetId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/review-sets/${encodeURIComponent(String(reviewSetId))}/archive`),
    { method: "POST", signal: options.signal }
  );
}

export function listPreconstructionReviewSources(projectId, reviewSetId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/review-sets/${encodeURIComponent(String(reviewSetId))}/sources`),
    { signal: options.signal }
  );
}

export function addPreconstructionReviewSource(projectId, reviewSetId, source, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/review-sets/${encodeURIComponent(String(reviewSetId))}/sources`),
    { method: "POST", body: JSON.stringify(source), signal: options.signal }
  );
}

export function updatePreconstructionReviewSource(projectId, reviewSetId, sourceId, source, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/review-sets/${encodeURIComponent(String(reviewSetId))}/sources/${encodeURIComponent(String(sourceId))}`
    ),
    { method: "PUT", body: JSON.stringify(source), signal: options.signal }
  );
}

export function removePreconstructionReviewSource(projectId, reviewSetId, sourceId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/review-sets/${encodeURIComponent(String(reviewSetId))}/sources/${encodeURIComponent(String(sourceId))}`
    ),
    { method: "DELETE", signal: options.signal }
  );
}

export function listPreconstructionSourceCandidates(projectId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/source-candidates${preconstructionQuery({
        source_type: options.sourceType,
        search: options.search,
        limit: options.limit,
      })}`
    ),
    { signal: options.signal }
  );
}

export function getPreconstructionReadiness(projectId, reviewSetId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/review-sets/${encodeURIComponent(String(reviewSetId))}/readiness${preconstructionQuery({
        analysis_type: options.analysisType,
      })}`
    ),
    { signal: options.signal }
  );
}

export function listPreconstructionRuns(projectId, reviewSetId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/review-sets/${encodeURIComponent(String(reviewSetId))}/runs${preconstructionQuery({
        limit: options.limit,
        offset: options.offset,
      })}`
    ),
    { signal: options.signal }
  );
}

export function createPreconstructionRun(projectId, reviewSetId, run, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/review-sets/${encodeURIComponent(String(reviewSetId))}/runs`),
    { method: "POST", body: JSON.stringify(run), signal: options.signal }
  );
}

export function getPreconstructionRun(projectId, runId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/runs/${encodeURIComponent(String(runId))}`),
    { signal: options.signal }
  );
}

export function cancelPreconstructionRun(projectId, runId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/runs/${encodeURIComponent(String(runId))}/cancel`),
    { method: "POST", signal: options.signal }
  );
}

export function retryPreconstructionRun(projectId, runId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/runs/${encodeURIComponent(String(runId))}/retry`),
    { method: "POST", signal: options.signal }
  );
}

export function preparePreconstructionSource(projectId, reviewSetId, sourceId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/review-sets/${encodeURIComponent(String(reviewSetId))}/sources/${encodeURIComponent(String(sourceId))}/prepare`
    ),
    { method: "POST", signal: options.signal }
  );
}

export function getPreconstructionPreparationRun(projectId, runId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/preparation-runs/${encodeURIComponent(String(runId))}`),
    { signal: options.signal }
  );
}

export function cancelPreconstructionPreparationRun(projectId, runId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/preparation-runs/${encodeURIComponent(String(runId))}/cancel`),
    { method: "POST", signal: options.signal }
  );
}

export function retryPreconstructionPreparationRun(projectId, runId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(projectId, `/preparation-runs/${encodeURIComponent(String(runId))}/retry`),
    { method: "POST", signal: options.signal }
  );
}

export function getPreconstructionSourceContent(
  projectId,
  reviewSetId,
  sourceId,
  options = {}
) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/review-sets/${encodeURIComponent(String(reviewSetId))}/sources/${encodeURIComponent(String(sourceId))}/content${preconstructionQuery({
        snapshot_id: options.snapshotId,
        page: options.page,
        segment_offset: options.segmentOffset,
        segment_limit: options.segmentLimit,
        search: options.search,
      })}`
    ),
    { signal: options.signal }
  );
}

export function getPreconstructionScopeTaxonomy(projectId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/scope-taxonomy${preconstructionQuery({
        category: options.category,
        scope_kind: options.scopeKind,
        search: options.search,
        include_deprecated: options.includeDeprecated,
      })}`
    ),
    { signal: options.signal }
  );
}

export function listPreconstructionAssertionSets(projectId, reviewSetId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/review-sets/${encodeURIComponent(String(reviewSetId))}/assertion-sets${preconstructionQuery({
        limit: options.limit,
        offset: options.offset,
      })}`
    ),
    { signal: options.signal }
  );
}

export function getPreconstructionAssertionSet(projectId, assertionSetId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/assertion-sets/${encodeURIComponent(String(assertionSetId))}`
    ),
    { signal: options.signal }
  );
}

export function listPreconstructionAssertions(projectId, reviewSetId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/review-sets/${encodeURIComponent(String(reviewSetId))}/assertions${preconstructionQuery({
        review_status: options.reviewStatus,
        concept_code: options.conceptCode,
        category: options.category,
        assertion_type: options.assertionType,
        source_id: options.sourceId,
        document_role: options.documentRole,
        discipline: options.discipline,
        trade: options.trade,
        inclusion_state: options.inclusionState,
        origin: options.origin,
        confidence_min: options.confidenceMin,
        confidence_max: options.confidenceMax,
        search: options.search,
        assertion_set_id: options.assertionSetId,
        current_assertion_set_only: options.currentAssertionSetOnly,
        limit: options.limit,
        offset: options.offset,
      })}`
    ),
    { signal: options.signal }
  );
}

export function getPreconstructionAssertion(projectId, assertionId, options = {}) {
  return authenticatedRequest(
    preconstructionPath(
      projectId,
      `/assertions/${encodeURIComponent(String(assertionId))}`
    ),
    { signal: options.signal }
  );
}

export function createPreconstructionManualAssertion(
  projectId,
  reviewSetId,
  assertion,
  options = {}
) {
  return jsonRequest(
    preconstructionPath(
      projectId,
      `/review-sets/${encodeURIComponent(String(reviewSetId))}/assertions/manual`
    ),
    "POST",
    assertion,
    { signal: options.signal }
  );
}

export function reviewPreconstructionAssertion(
  projectId,
  assertionId,
  review,
  options = {}
) {
  return jsonRequest(
    preconstructionPath(
      projectId,
      `/assertions/${encodeURIComponent(String(assertionId))}/reviews`
    ),
    "POST",
    review,
    { signal: options.signal }
  );
}

export function supersedePreconstructionAssertion(
  projectId,
  assertionId,
  payload,
  options = {}
) {
  return jsonRequest(
    preconstructionPath(
      projectId,
      `/assertions/${encodeURIComponent(String(assertionId))}/supersede`
    ),
    "POST",
    payload,
    { signal: options.signal }
  );
}
