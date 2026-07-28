import { Suspense, useCallback, useEffect, useState } from "react";

import AppRouter from "./AppRouter";
import { useAuth } from "./auth/authContext";
import FeedbackBanner from "./components/FeedbackBanner";
import LoadingState from "./components/LoadingState";
import ConfirmDialog from "./components/ui/ConfirmDialog";
import ErrorBoundary from "./components/ui/ErrorBoundary";
import useAppNavigation from "./hooks/useAppNavigation";
import useNotifications from "./hooks/useNotifications";
import useProjectResource from "./hooks/useProjectResource";
import useRecordForms from "./hooks/useRecordForms";
import useScheduleActions from "./hooks/useScheduleActions";
import AuthPage from "./pages/AuthPage";
import { seedDemoProject } from "./services/demoSeeder";

const ONBOARDING_FLAG = "fieldflow.onboardingDismissed";

const PAGE_TITLES = {
  home: "Projects",
  projectDashboard: "Dashboard",
  scheduler: "Schedule",
  dailyLogs: "Daily Logs",
  inspections: "Inspections",
  notesDelays: "Notes & Delays",
  changeOrders: "Change Orders",
  rfis: "RFIs",
  submittals: "Submittals",
  punchItems: "Punch List",
  projectSettings: "Settings",
};

function App() {
  const {
    isAuthenticated,
    login,
    logout,
    register,
    sessionExpired,
    acknowledgeSessionExpiry,
  } = useAuth();

  const {
    currentPage,
    selectedProjectId,
    selectedProjectIdRef,
    selectProject,
    navigateTo,
    resetRoute,
  } = useAppNavigation();

  const {
    notice,
    setNotice,
    showNotice,
    reportRequestError,
    reportValidationError,
  } = useNotifications({ sessionExpired, acknowledgeSessionExpiry });

  const data = useProjectResource({
    isAuthenticated,
    currentPage,
    selectedProjectId,
    selectedProjectIdRef,
    selectProject,
    navigateTo,
    reportRequestError,
  });

  const { projects, loadProjects, clearAllData, runOperation } = data;

  const schedule = useScheduleActions({
    selectedProjectId,
    tasks: data.tasks,
    setTasks: data.setTasks,
    setTemplates: data.setTemplates,
    loadTasks: data.loadTasks,
    runOperation,
    showNotice,
    reportRequestError,
    reportValidationError,
  });

  const forms = useRecordForms({
    selectedProjectId,
    runOperation,
    showNotice,
    reportRequestError,
    reportValidationError,
    setProjects: data.setProjects,
    navigateTo,
    loadDailyLogs: data.loadDailyLogs,
    loadInspections: data.loadInspections,
    loadNotesDelays: data.loadNotesDelays,
    loadChangeOrders: data.loadChangeOrders,
    loadRFIs: data.loadRFIs,
    loadSubmittals: data.loadSubmittals,
    loadPunchItems: data.loadPunchItems,
    loadProjectCompanies: data.loadProjectCompanies,
    clearNotice: () => setNotice(null),
  });

  // Authentication form state and onboarding remain app-level concerns.
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authMode, setAuthMode] = useState("login");
  const [onboardingDismissed, setOnboardingDismissed] = useState(
    () => localStorage.getItem(ONBOARDING_FLAG) === "1"
  );
  const [seedProgress, setSeedProgress] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);

  const resetApplicationState = useCallback(() => {
    clearAllData();
    resetRoute();
  }, [clearAllData, resetRoute]);

  const handleLogout = useCallback(() => {
    logout();
    resetApplicationState();
    setNotice(null);
  }, [logout, resetApplicationState, setNotice]);

  useEffect(() => {
    if (isAuthenticated) return undefined;

    const timeoutId = window.setTimeout(resetApplicationState, 0);
    return () => window.clearTimeout(timeoutId);
  }, [isAuthenticated, resetApplicationState]);

  useEffect(() => {
    const selectedProject = projects.find(
      (project) => project.id === selectedProjectId
    );
    const context =
      currentPage === "home"
        ? PAGE_TITLES[currentPage]
        : `${selectedProject?.name || "Project"} · ${PAGE_TITLES[currentPage]}`;

    document.title = `${context} | FieldFlow`;
  }, [currentPage, projects, selectedProjectId]);

  const handleRegister = async () => {
    return runOperation("auth", async () => {
      try {
        await register({
          email,
          password,
        });
        setAuthMode("login");
        setPassword("");
        showNotice("success", "Account created. Log in to continue.");
      } catch (error) {
        reportRequestError("Unable to register", error);
      }
    });
  };

  const handleLogin = async () => {
    return runOperation("auth", async () => {
      try {
        await login(email, password);
        setEmail("");
        setPassword("");
      } catch (error) {
        reportRequestError("Unable to log in", error);
      }
    });
  };

  const handleDemoAccess = useCallback(() => {
    setEmail(`demo+${Date.now()}@fieldflow.app`);
    setPassword("FieldFlowDemo123!");
    setAuthMode("register");
    showNotice(
      "info",
      "Demo account ready — select Create account to explore FieldFlow with a sample project."
    );
  }, [showNotice]);

  const dismissOnboarding = useCallback(() => {
    localStorage.setItem(ONBOARDING_FLAG, "1");
    setOnboardingDismissed(true);
  }, []);

  const handleLoadSampleProject = useCallback(() => {
    return runOperation("seedDemo", async () => {
      setSeedProgress({ step: 0, total: 0, label: "Preparing sample data…" });

      try {
        const project = await seedDemoProject({ onProgress: setSeedProgress });

        dismissOnboarding();
        await loadProjects();
        navigateTo("projectDashboard", project.id);
        showNotice(
          "success",
          "Sample project loaded — explore Riverside Medical Center — Phase 2."
        );
      } catch (error) {
        reportRequestError("Unable to load the sample project", error);
      } finally {
        setSeedProgress(null);
      }
    });
  }, [
    dismissOnboarding,
    loadProjects,
    navigateTo,
    reportRequestError,
    runOperation,
    showNotice,
  ]);

  // Destructive actions stage a request here; ConfirmDialog dispatches it.
  const handleDeleteTask = (id) => {
    setPendingDelete({
      kind: "task",
      id,
      title: "Delete this task?",
      message:
        "The task will be permanently removed from the schedule. This action cannot be undone.",
    });
  };

  const handleDeleteChangeOrder = (id, number) => {
    setPendingDelete({
      kind: "changeOrder",
      id,
      title: `Delete ${number}?`,
      message:
        "The change order will be permanently removed. This action cannot be undone.",
    });
  };

  const handleDeleteRFI = (id, number) => {
    setPendingDelete({
      kind: "rfi",
      id,
      title: `Delete ${number}?`,
      message:
        "The RFI will be permanently removed. This action cannot be undone.",
    });
  };

  const handleDeleteSubmittal = (id, number) => {
    setPendingDelete({
      kind: "submittal",
      id,
      title: `Delete ${number}?`,
      message:
        "The submittal will be permanently removed. This action cannot be undone.",
    });
  };

  const handleDeletePunchItem = (id, number) => {
    setPendingDelete({
      kind: "punchItem",
      id,
      title: `Delete ${number}?`,
      message:
        "The punch item will be permanently removed. This action cannot be undone.",
    });
  };

  const handleConfirmDelete = async () => {
    const pending = pendingDelete;
    setPendingDelete(null);
    if (!pending) return;

    if (pending.kind === "task") {
      await schedule.performTaskDelete(pending.id);
      return;
    }

    if (pending.kind === "changeOrder") {
      await forms.performChangeOrderDelete(pending.id);
      return;
    }

    if (pending.kind === "rfi") {
      await forms.performRFIDelete(pending.id);
      return;
    }

    if (pending.kind === "submittal") {
      await forms.performSubmittalDelete(pending.id);
      return;
    }

    await forms.performPunchItemDelete(pending.id);
  };

  return (
    <>
      <FeedbackBanner
        notice={notice}
        onDismiss={() => setNotice(null)}
      />
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        destructive
        title={pendingDelete?.title}
        message={pendingDelete?.message}
        confirmLabel="Delete"
        onConfirm={handleConfirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
      <ErrorBoundary
        title="This page failed to display"
        description="Your project data is safe. Try again, or use the navigation to switch pages."
      >
        <Suspense fallback={<LoadingState message="Loading module…" />}>
          {isAuthenticated ? (
            <AppRouter
              currentPage={currentPage}
              selectedProjectId={selectedProjectId}
              navigateTo={navigateTo}
              onLogout={handleLogout}
              data={data}
              schedule={schedule}
              forms={forms}
              onboarding={{
                dismissed: onboardingDismissed,
                seedProgress,
                onLoadSample: handleLoadSampleProject,
                onStartEmpty: dismissOnboarding,
              }}
              onDeleteTask={handleDeleteTask}
              onDeleteChangeOrder={handleDeleteChangeOrder}
              onDeleteRFI={handleDeleteRFI}
              onDeleteSubmittal={handleDeleteSubmittal}
              onDeletePunchItem={handleDeletePunchItem}
              onAttachmentError={reportRequestError}
              onDashboardError={reportRequestError}
            />
          ) : (
            <AuthPage
              authMode={authMode}
              email={email}
              password={password}
              onEmailChange={setEmail}
              onPasswordChange={setPassword}
              onLogin={handleLogin}
              onRegister={handleRegister}
              onDemo={handleDemoAccess}
              isSubmitting={data.isOperationActive("auth")}
              onToggleMode={() =>
                setAuthMode(authMode === "login" ? "register" : "login")
              }
            />
          )}
        </Suspense>
      </ErrorBoundary>
    </>
  );
}

export default App;
