
const API_URL = "http://127.0.0.1:8000";

export async function fetchProjects() {
  const res = await fetch(`${API_URL}/projects`);
  return res.json();
}

export async function createProject(project) {
  const res = await fetch(`${API_URL}/projects`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(project),
  });

  return res.json();
}

export async function fetchTasks(projectId) {
  const res = await fetch(`${API_URL}/projects/${projectId}/tasks`);
  return res.json();
}

export async function createTask(projectId, task) {
  const res = await fetch(`${API_URL}/projects/${projectId}/tasks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(task),
  });

  return res.json();
}

export async function deleteTask(projectId, id) {
  await fetch(`${API_URL}/projects/${projectId}/tasks/${id}`, {
    method: "DELETE",
  });
}

export async function updateTask(projectId, id, task) {
  const res = await fetch(`${API_URL}/projects/${projectId}/tasks/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(task),
  });

  return res.json();
}

export async function fetchTemplates() {
  const res = await fetch(`${API_URL}/templates`);
  return res.json();
}

export async function saveTemplate(projectId, template) {
  const res = await fetch(`${API_URL}/projects/${projectId}/templates`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(template),
  });

  return res.json();
}

export async function applyTemplate(projectId, templateId) {
  const res = await fetch(
    `${API_URL}/projects/${projectId}/templates/${templateId}/apply`,
    {
      method: "POST",
    }
  );

  return res.json();
}

export function exportProjectPdf(projectId) {
  window.open(
    `${API_URL}/projects/${projectId}/export/pdf`,
    "_blank"
  );
}