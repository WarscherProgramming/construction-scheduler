import AppLayout from "./AppLayout";
import Button from "./Button";
import Sidebar from "./Sidebar";

/** Single source of truth for the persistent project navigation rail. */
const NAV_ITEMS = [
  { id: "projectDashboard", label: "Dashboard" },
  { id: "scheduler", label: "Schedule" },
  { id: "dailyLogs", label: "Daily Logs" },
  { id: "inspections", label: "Inspections" },
  { id: "notesDelays", label: "Notes & Delays" },
  { id: "changeOrders", label: "Change Orders" },
  { id: "projectSettings", label: "Project Settings" },
];

/**
 * Persistent project frame shared by every project page (Dashboard, Scheduler,
 * and all field-record modules). Renders the app shell with a consistent left
 * rail — brand + project context, module navigation with an active item, an
 * optional control-panel slot (`sidebarExtras`, used by the Scheduler), and a
 * Logout footer — plus the page content as children.
 *
 * @param {string} activeId  Nav id for the current page (drives aria-current).
 * @param {(page: string) => void} onNavigate  Router navigation callback.
 */
function ProjectLayout({
  projectName = "Project",
  activeId,
  onNavigate,
  onLogout,
  sidebarExtras,
  mainClassName = "",
  children,
}) {
  const items = NAV_ITEMS.map((item) => ({
    ...item,
    onClick: () => onNavigate?.(item.id),
  }));

  const sidebar = (
    <Sidebar
      className="project-sidebar"
      ariaLabel="Project navigation"
      items={items}
      activeId={activeId}
      header={
        <>
          <div className="sidebar-brand">
            <p className="sidebar-brand__eyebrow">FieldFlow</p>
            <p className="sidebar-brand__project">{projectName}</p>
          </div>
          <Button block onClick={() => onNavigate?.("home")}>
            Back to Home
          </Button>
        </>
      }
      footer={
        onLogout && (
          <Button block onClick={onLogout}>
            Logout
          </Button>
        )
      }
    >
      {sidebarExtras}
    </Sidebar>
  );

  return (
    <AppLayout sidebar={sidebar} mainClassName={mainClassName}>
      {children}
    </AppLayout>
  );
}

export default ProjectLayout;
