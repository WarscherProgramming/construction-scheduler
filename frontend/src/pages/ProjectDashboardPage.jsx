import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import EmptyState from "../components/EmptyState";
import LoadingState from "../components/LoadingState";
import SkipLink from "../components/SkipLink";
import { buttonStyle } from "../styles";

function ProjectDashboardPage({
  projectName,
  tasksThisWeek,
  changeOrderTotals,
  projectDelays,
  metrics = {
    totalTasks: 0,
    scheduledTasks: 0,
    tasksThisWeek: 0,
    recordedDelays: 0,
    pendingChangeOrders: 0,
    pendingChangeOrderValue: 0,
  },
  isLoadingTasks = false,
  isLoadingChangeOrders = false,
  isLoadingDelays = false,
  formatDate,
  onNavigate,
}) {
  const currencyFormatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
  const dashboardIsLoading =
    isLoadingTasks || isLoadingChangeOrders || isLoadingDelays;

  return (
    <div className="app-shell">
      <SkipLink />
      <aside className="app-sidebar dashboard-sidebar">
        <button onClick={() => onNavigate("home")} style={buttonStyle}>
          Back to Home
        </button>

        <h2 className="sidebar-heading">Modules</h2>

        <nav className="sidebar-nav" aria-label="Project modules">
          <button onClick={() => onNavigate("scheduler")} style={buttonStyle}>
            Schedule
          </button>
          <button onClick={() => onNavigate("dailyLogs")} style={buttonStyle}>
            Daily Logs
          </button>
          <button onClick={() => onNavigate("inspections")} style={buttonStyle}>
            Inspections
          </button>
          <button onClick={() => onNavigate("notesDelays")} style={buttonStyle}>
            Notes & Delays
          </button>
          <button onClick={() => onNavigate("changeOrders")} style={buttonStyle}>
            Change Orders
          </button>
          <button
            onClick={() => onNavigate("projectSettings")}
            style={buttonStyle}
          >
            Project Settings
          </button>
        </nav>
      </aside>

      <main id="main-content" className="app-main" tabIndex={-1}>
        <h1>{projectName} Dashboard</h1>

        <section className="quick-actions" aria-labelledby="quick-actions-title">
          <div>
            <h2 id="quick-actions-title">Quick Actions</h2>
            <p>Start the field records used most often.</p>
          </div>
          <div className="quick-action-buttons">
            <button
              type="button"
              className="button-primary"
              onClick={() => onNavigate("dailyLogs")}
              style={buttonStyle}
            >
              Add Daily Log
            </button>
            <button
              type="button"
              onClick={() => onNavigate("notesDelays")}
              style={buttonStyle}
            >
              Report Delay
            </button>
            <button
              type="button"
              onClick={() => onNavigate("inspections")}
              style={buttonStyle}
            >
              Add Inspection
            </button>
            <button
              type="button"
              onClick={() => onNavigate("changeOrders")}
              style={buttonStyle}
            >
              Add Change Order
            </button>
          </div>
        </section>

        <section
          className="dashboard-metrics"
          aria-labelledby="project-overview-title"
          aria-busy={dashboardIsLoading}
        >
          <h2 id="project-overview-title" className="visually-hidden">
            Project Overview
          </h2>
          <dl className="metric-grid">
            <div className="metric-card">
              <dt>Total tasks</dt>
              <dd>{isLoadingTasks ? "—" : metrics.totalTasks}</dd>
              <span>
                {isLoadingTasks
                  ? "Loading schedule"
                  : `${metrics.scheduledTasks} scheduled`}
              </span>
            </div>
            <div className="metric-card">
              <dt>Starting this week</dt>
              <dd>{isLoadingTasks ? "—" : metrics.tasksThisWeek}</dd>
              <span>Sunday through Saturday</span>
            </div>
            <div className="metric-card metric-card-alert">
              <dt>Recorded delays</dt>
              <dd>{isLoadingDelays ? "—" : metrics.recordedDelays}</dd>
              <span>All delay entries</span>
            </div>
            <div className="metric-card metric-card-warning">
              <dt>Pending change orders</dt>
              <dd>
                {isLoadingChangeOrders ? "—" : metrics.pendingChangeOrders}
              </dd>
              <span>
                {isLoadingChangeOrders
                  ? "Loading exposure"
                  : currencyFormatter.format(metrics.pendingChangeOrderValue)}
              </span>
            </div>
          </dl>
        </section>

        <div className="dashboard-grid">
          <section className="dashboard-panel">
            <h2 style={{ marginBottom: "15px" }}>Scheduled This Week</h2>

            {isLoadingTasks ? (
              <LoadingState message="Loading schedule…" />
            ) : tasksThisWeek.length ? (
              <div
                className="table-scroll-region"
                role="region"
                aria-label="Tasks scheduled this week"
                tabIndex={0}
              >
                <table className="dashboard-table">
                <caption className="visually-hidden">
                  Tasks scheduled this week
                </caption>
                <thead>
                  <tr>
                    {["Task", "Start"].map((header) => (
                      <th
                        key={header}
                        scope="col"
                        style={{
                          padding: "6px",
                          background: "#f3f4f6",
                          border: "1px solid #ddd",
                          textAlign: "left",
                        }}
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {tasksThisWeek.map((task) => (
                    <tr key={task.id}>
                      <td
                        style={{
                          padding: "6px",
                          border: "1px solid #ddd",
                          whiteSpace: "pre",
                        }}
                      >
                        {task.name}
                      </td>
                      <td style={{ padding: "6px", border: "1px solid #ddd" }}>
                        {formatDate(task.start_date)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="No tasks scheduled this week"
                description="Tasks with start dates in the current week will appear here."
              />
            )}
          </section>

          <section className="dashboard-panel dashboard-chart-panel">
            <h2 style={{ marginBottom: "15px" }}>
              Change Orders by Company
            </h2>

            {isLoadingChangeOrders ? (
              <LoadingState message="Loading change orders…" />
            ) : changeOrderTotals.length ? (
              <div className="dashboard-chart">
                <ul className="visually-hidden">
                  {changeOrderTotals.map((entry) => (
                    <li key={entry.company}>
                      {entry.company}: ${entry.total}
                    </li>
                  ))}
                </ul>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={changeOrderTotals}
                    margin={{ top: 20, right: 20, left: 20, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="company" />
                    <YAxis />
                    <Tooltip formatter={(value) => [`$${value}`, "CO Value"]} />
                    <Bar dataKey="total" fill="#2563eb" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState
                title="No change order value to chart"
                description="Change order totals will appear after records are added."
              />
            )}
          </section>
        </div>

        <section className="dashboard-panel dashboard-delays">
          <h2 style={{ marginBottom: "15px" }}>Project Delays</h2>

          {isLoadingDelays ? (
            <LoadingState message="Loading project delays…" />
          ) : projectDelays.length ? (
            <div
              className="table-scroll-region"
              role="region"
              aria-label="Project delays"
              tabIndex={0}
            >
              <table className="dashboard-table">
              <caption className="visually-hidden">Project delays</caption>
              <thead>
                <tr>
                  {["Date", "Company", "Description"].map((header) => (
                    <th
                      key={header}
                      scope="col"
                      style={{
                        padding: "6px",
                        background: "#f3f4f6",
                        border: "1px solid #ddd",
                        textAlign: "left",
                      }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {projectDelays.map((entry) => (
                  <tr key={entry.id}>
                    <td style={{ padding: "6px", border: "1px solid #ddd" }}>
                      {formatDate(entry.date)}
                    </td>
                    <td style={{ padding: "6px", border: "1px solid #ddd" }}>
                      {entry.company}
                    </td>
                    <td style={{ padding: "6px", border: "1px solid #ddd" }}>
                      {entry.description}
                    </td>
                  </tr>
                ))}
              </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No project delays recorded"
              description="Delay entries from Notes & Delays will appear here."
            />
          )}
        </section>
      </main>
    </div>
  );
}

export default ProjectDashboardPage;
