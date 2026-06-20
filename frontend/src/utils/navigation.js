const PAGE_SEGMENTS = {
  projectDashboard: "dashboard",
  scheduler: "schedule",
  dailyLogs: "daily-logs",
  inspections: "inspections",
  notesDelays: "notes-delays",
  changeOrders: "change-orders",
  projectSettings: "settings",
};

const SEGMENT_PAGES = Object.fromEntries(
  Object.entries(PAGE_SEGMENTS).map(([page, segment]) => [segment, page])
);

export function buildAppHash(page, projectId) {
  if (page === "home" || !projectId || !PAGE_SEGMENTS[page]) return "#/";
  return `#/projects/${projectId}/${PAGE_SEGMENTS[page]}`;
}

export function parseAppHash(hash = "") {
  if (!hash || hash === "#" || hash === "#/") {
    return { page: "home", projectId: null };
  }

  const match = hash.match(/^#\/projects\/(\d+)\/([^/?#]+)$/);
  if (!match) return { page: "home", projectId: null };

  const projectId = Number(match[1]);
  const page = SEGMENT_PAGES[match[2]];

  if (!page || !Number.isSafeInteger(projectId) || projectId <= 0) {
    return { page: "home", projectId: null };
  }

  return { page, projectId };
}

export function updateBrowserRoute(page, projectId, { replace = false } = {}) {
  const method = replace ? "replaceState" : "pushState";
  window.history[method]({ page, projectId }, "", buildAppHash(page, projectId));
}
