import { useCallback, useEffect, useRef, useState } from "react";

import { parseAppHash, updateBrowserRoute } from "../utils/navigation";

/**
 * Owns the hash-based routing state: current page, selected project (state +
 * ref for stale-response guards), programmatic navigation, and the browser
 * back/forward listeners.
 */
function useAppNavigation() {
  const [selectedProjectId, setSelectedProjectId] = useState(
    () => parseAppHash(window.location.hash).projectId
  );
  const [currentPage, setCurrentPage] = useState(
    () => parseAppHash(window.location.hash).page
  );
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
        updateBrowserRoute("home", null, options);
        return;
      }

      if (page !== "home" && !projectId) {
        setCurrentPage("home");
        updateBrowserRoute("home", null, options);
        return;
      }

      if (projectId) selectProject(projectId);
      setCurrentPage(page);
      updateBrowserRoute(page, projectId, options);
    },
    [selectProject]
  );

  /** Return to a clean home route (used by logout/reset). */
  const resetRoute = useCallback(() => {
    selectedProjectIdRef.current = null;
    setSelectedProjectId(null);
    setCurrentPage("home");
    updateBrowserRoute("home", null, { replace: true });
  }, []);

  useEffect(() => {
    const handleBrowserNavigation = () => {
      const route = parseAppHash(window.location.hash);

      selectProject(route.projectId);
      setCurrentPage(route.page);
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
    updateBrowserRoute(route.page, route.projectId, { replace: true });
  }, []);

  return {
    currentPage,
    selectedProjectId,
    selectedProjectIdRef,
    selectProject,
    navigateTo,
    resetRoute,
  };
}

export default useAppNavigation;
