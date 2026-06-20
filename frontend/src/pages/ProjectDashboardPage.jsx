import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { buttonStyle } from "../styles";

function ProjectDashboardPage({
  projectName,
  tasksThisWeek,
  changeOrderTotals,
  projectDelays,
  formatDate,
  onNavigate,
}) {
  return (
    <div className="app-shell">
      <aside className="app-sidebar dashboard-sidebar">
        <button onClick={() => onNavigate("home")} style={buttonStyle}>
          Back to Home
        </button>

        <h3>Modules</h3>

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

      <main className="app-main">
        <h1>{projectName} Dashboard</h1>

        <div className="dashboard-grid">
          <section className="dashboard-panel">
            <h2 style={{ marginBottom: "15px" }}>Scheduled This Week</h2>

            <div
              className="table-scroll-region"
              role="region"
              aria-label="Tasks scheduled this week"
              tabIndex={0}
            >
              <table className="dashboard-table">
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
          </section>

          <section className="dashboard-panel dashboard-chart-panel">
            <h2 style={{ marginBottom: "15px" }}>
              Change Orders by Company
            </h2>

            <div className="dashboard-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={changeOrderTotals}
                  margin={{ top: 20, right: 20, left: 20, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="company" />
                  <YAxis />
                  <Tooltip formatter={(value) => [`$${value}`, "CO Value"]} />
                  <Bar dataKey="total" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        </div>

        <section className="dashboard-panel dashboard-delays">
          <h2 style={{ marginBottom: "15px" }}>Project Delays</h2>

          <div
            className="table-scroll-region"
            role="region"
            aria-label="Project delays"
            tabIndex={0}
          >
            <table className="dashboard-table">
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
        </section>
      </main>
    </div>
  );
}

export default ProjectDashboardPage;
