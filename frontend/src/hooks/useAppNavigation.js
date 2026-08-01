import { useCallback, useEffect, useRef, useState } from "react";

import { parseAppHash, updateBrowserRoute } from "../utils/navigation";

/**
 * Owns the hash-based routing state: current page, selected project (state +
 * ref for stale-response guards), programmatic navigation, and the browser
 * back/forward listeners.
 */
function useAppNavigation() {
  const [initialRoute] = useState(() => parseAppHash(window.location.hash));
  const [selectedProjectId, setSelectedProjectId] = useState(
    () => initialRoute.projectId
  );
  const [currentPage, setCurrentPage] = useState(
    () => initialRoute.page
  );
  const [routeParams, setRouteParams] = useState(() => ({
    sheetId: initialRoute.sheetId || null,
    revisionId: initialRoute.revisionId || null,
  }));
  const selectedProjectIdRef = useRef(selectedProjectId);

  useEffect(() => {
    selectedProjectIdRef.current = selectedProjectId;
  }, [selectedProjectId]);

  const selectProject = useCallback((projectId) => {
    selectedProjectIdRef.current = projectId;
    setSelectedProjectId(projectId);
  }, []);

  const navigateTo = useCallback(
    (page, projectId = selectedProjectIdRef.current, options) => {
      if (page === "home") {
        selectProject(null);
        setCurrentPage("home");
        setRouteParams({ sheetId: null, revisionId: null });
        updateBrowserRoute("home", null, options);
        return;
      }

      if (page !== "home" && !projectId) {
        setCurrentPage("home");
        setRouteParams({ sheetId: null, revisionId: null });
        updateBrowserRoute("home", null, options);
        return;
      }

      if (projectId) selectProject(projectId);
      setCurrentPage(page);
      setRouteParams({
        sheetId: page === "drawingViewer" ? options?.sheetId || null : null,
        revisionId:
          page === "drawingViewer" ? options?.revisionId || null : null,
      });
      updateBrowserRoute(page, projectId, options);
    },
    [selectProject]
  );

  /** Return to a clean home route (used by logout/reset). */
  const resetRoute = useCallback(() => {
    selectedProjectIdRef.current = null;
    setSelectedProjectId(null);
    setCurrentPage("home");
    setRouteParams({ sheetId: null, revisionId: null });
    updateBrowserRoute("home", null, { replace: true });
  }, []);

  useEffect(() => {
    const handleBrowserNavigation = () => {
      const route = parseAppHash(window.location.hash);

      selectProject(route.projectId);
      setCurrentPage(route.page);
      setRouteParams({
        sheetId: route.sheetId || null,
        revisionId: route.revisionId || null,
      });
    };

    window.addEventListener("popstate", handleBrowserNavigation);
    window.addEventListener("hashchange", handleBrowserNavigation);

    return () => {
      window.removeEventListener("popstate", handleBrowserNavigation);
      window.removeEventListener("hashchange", handleBrowserNavigation);
    };
  }, [selectProject]);

  useEffect(() => {
    const route = parseAppHash(window.location.hash);
    updateBrowserRoute(route.page, route.projectId, {
      replace: true,
      sheetId: route.sheetId,
      revisionId: route.revisionId,
    });
  }, []);

  return {
    currentPage,
    routeParams,
    selectedProjectId,
    selectedProjectIdRef,
    selectProject,
    navigateTo,
    resetRoute,
  };
}

export default useAppNavigation;
