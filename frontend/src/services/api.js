import {
  authenticatedRequest,
  downloadAuthenticatedFile,
  jsonRequest,
  request,
} from "./httpClient";

export function registerUser(user) {
  return request("/auth/register", {
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

  return request("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData,
  });
}

export function fetchProjects() {
  return authenticatedRequest("/projects");
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

export function reorderTasks(projectId, taskIds) {
  return jsonRequest(`/projects/${projectId}/tasks/reorder`, "PUT", {
    task_ids: taskIds,
  });
}
