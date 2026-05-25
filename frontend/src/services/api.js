
const API_URL = "http://127.0.0.1:8000";

function getAuthHeaders() {
  const token = localStorage.getItem("token");

  return {
    "Content-Type": "application/json",
    Authorization: token ? `Bearer ${token}` : "",
  };
}

export async function registerUser(user) {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(user),
  });

  return res.json();
}

export async function loginUser(email, password) {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData,
  });

  return res.json();
}

export async function fetchProjects() {
  const res = await fetch(`${API_URL}/projects`, {
    headers: getAuthHeaders(),
  });

  return res.json();
}

export async function createProject(project) {
  const res = await fetch(`${API_URL}/projects`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(project),
  });

  return res.json();
}

export async function fetchTasks(projectId) {
  const res = await fetch(`${API_URL}/projects/${projectId}/tasks`, {
    headers: getAuthHeaders(),
  });

  return res.json();
}

export async function createTask(projectId, task) {
  const res = await fetch(`${API_URL}/projects/${projectId}/tasks`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(task),
  });

  return res.json();
}

export async function deleteTask(projectId, id) {
  await fetch(`${API_URL}/projects/${projectId}/tasks/${id}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
}

export async function updateTask(projectId, id, task) {
  const res = await fetch(`${API_URL}/projects/${projectId}/tasks/${id}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(task),
  });

  return res.json();
}

export async function fetchTemplates() {
  const res = await fetch(`${API_URL}/templates`, {
    headers: getAuthHeaders(),
  });

  return res.json();
}

export async function saveTemplate(projectId, template) {
  const res = await fetch(`${API_URL}/projects/${projectId}/templates`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(template),
  });

  return res.json();
}

export async function applyTemplate(projectId, templateId) {
  const res = await fetch(
    `${API_URL}/projects/${projectId}/templates/${templateId}/apply`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    }
  );

  return res.json();
}

export async function exportProjectPdf(projectId) {
  const res = await fetch(`${API_URL}/projects/${projectId}/export/pdf`, {
    headers: getAuthHeaders(),
  });

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);

  window.open(url, "_blank");
}

export async function fetchDailyLogs(projectId) {
  const res = await fetch(
    `${API_URL}/projects/${projectId}/daily-logs`,
    {
      headers: getAuthHeaders(),
    }
  );

  return res.json();
}

export async function createDailyLog(projectId, log) {
  const res = await fetch(
    `${API_URL}/projects/${projectId}/daily-logs`,
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(log),
    }
  );

  return res.json();
}

//fetch and create inspections
export async function fetchInspections(projectId) {
  const res = await fetch(`${API_URL}/projects/${projectId}/inspections`, {
    headers: getAuthHeaders(),
  });

  return res.json();
}

export async function createInspection(projectId, inspection) {
  const res = await fetch(`${API_URL}/projects/${projectId}/inspections`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(inspection),
  });

  return res.json();
}