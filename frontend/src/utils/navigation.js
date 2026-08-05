const PAGE_SEGMENTS = {
  projectDashboard: "dashboard",
  scheduler: "schedule",
  dailyLogs: "daily-logs",
  inspections: "inspections",
  notesDelays: "notes-delays",
  changeOrders: "change-orders",
  rfis: "rfis",
  submittals: "submittals",
  punchItems: "punch-items",
  projectDrawings: "drawings",
  projectDocuments: "documents",
  projectDocumentSearch: "search",
  projectPreconstruction: "preconstruction",
  projectSettings: "settings",
};

const SEGMENT_PAGES = Object.fromEntries(
  Object.entries(PAGE_SEGMENTS).map(([page, segment]) => [segment, page])
);

function isPositiveId(value) {
  return Number.isSafeInteger(Number(value)) && Number(value) > 0;
}

export function buildAppHash(page, projectId, options = {}) {
  if (
    page === "drawingViewer" &&
    isPositiveId(projectId) &&
    isPositiveId(options.sheetId) &&
    isPositiveId(options.revisionId)
  ) {
    return `#/projects/${Number(projectId)}/drawings/sheets/${Number(
      options.sheetId
    )}/revisions/${Number(options.revisionId)}/view`;
  }
  if (page === "home" || !projectId || !PAGE_SEGMENTS[page]) return "#/";
  return `#/projects/${projectId}/${PAGE_SEGMENTS[page]}`;
}

export function parseAppHash(hash = "") {
  if (!hash || hash === "#" || hash === "#/") {
    return { page: "home", projectId: null };
  }

  const viewerMatch = hash.match(
    /^#\/projects\/(\d+)\/drawings\/sheets\/(\d+)\/revisions\/(\d+)\/view$/
  );
  if (viewerMatch) {
    const projectId = Number(viewerMatch[1]);
    const sheetId = Number(viewerMatch[2]);
    const revisionId = Number(viewerMatch[3]);
    if (
      isPositiveId(projectId) &&
      isPositiveId(sheetId) &&
      isPositiveId(revisionId)
    ) {
      return { page: "drawingViewer", projectId, sheetId, revisionId };
    }
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

export function updateBrowserRoute(page, projectId, options = {}) {
  const { replace = false, sheetId = null, revisionId = null } = options;
  const method = replace ? "replaceState" : "pushState";
  const state =
    page === "drawingViewer"
      ? { page, projectId, sheetId, revisionId }
      : { page, projectId };
  window.history[method](
    state,
    "",
    buildAppHash(page, projectId, options)
  );
}
