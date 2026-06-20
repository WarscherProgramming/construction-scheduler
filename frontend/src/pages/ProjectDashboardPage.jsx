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
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <aside
        style={{
          width: "220px",
          minWidth: "220px",
          padding: "20px",
          borderRight: "1px solid #ddd",
          boxSizing: "border-box",
        }}
      >
        <button onClick={() => onNavigate("home")} style={buttonStyle}>
          Back to Home
        </button>

        <h3>Modules</h3>

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
      </aside>

      <main style={{ flex: 1, padding: "24px" }}>
        <h1>{projectName} Dashboard</h1>

        <div
          style={{
            display: "flex",
            gap: "30px",
            alignItems: "flex-start",
            marginTop: "30px",
            flexWrap: "wrap",
          }}
        >
          <div>
            <h2 style={{ marginBottom: "15px" }}>Scheduled This Week</h2>

            <table
              style={{
                width: "450px",
                borderCollapse: "collapse",
                fontSize: "14px",
              }}
            >
              <thead>
                <tr>
                  {["Task", "Start"].map((header) => (
                    <th
                      key={header}
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

          <div>
            <h2 style={{ marginBottom: "15px" }}>
              Change Orders by Company
            </h2>

            <div
              style={{
                width: "700px",
                height: "350px",
                border: "1px solid #ddd",
                borderRadius: "8px",
                padding: "15px",
                background: "#fff",
              }}
            >
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
          </div>
        </div>

        <div style={{ marginTop: "30px" }}>
          <h2 style={{ marginBottom: "15px" }}>Project Delays</h2>

          <table
            style={{
              width: "450px",
              borderCollapse: "collapse",
              fontSize: "14px",
            }}
          >
            <thead>
              <tr>
                {["Date", "Company", "Description"].map((header) => (
                  <th
                    key={header}
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
      </main>
    </div>
  );
}

export default ProjectDashboardPage;
