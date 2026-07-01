import { useMemo } from "react";
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
import StatusBadge from "../components/StatusBadge";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import ProjectLayout from "../components/ui/ProjectLayout";
import {
  getAttentionActivities,
  getChangeOrderTotalsByCompany,
  getDashboardMetrics,
  getInspectionIssueCount,
  getProjectHealthScore,
  getRecentActivity,
  getScheduleHealth,
  getThisWeekProgress,
  getTodaysFocus,
  getUpcomingInspections,
  getUpcomingTasks,
} from "../utils/dashboard";

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const BAND_LABEL = {
  healthy: "Healthy",
  "at-risk": "At Risk",
  critical: "Critical",
};

const GAUGE_ARC = "M 10 60 A 50 50 0 0 1 110 60";

function HealthGauge({ score, band }) {
  return (
    <div className={`health-gauge health-gauge--${band}`}>
      <svg
        className="health-gauge__svg"
        viewBox="0 0 120 72"
        role="img"
        aria-label={`Project health score ${score} of 100, ${BAND_LABEL[band]}`}
      >
        <path className="health-gauge__track" d={GAUGE_ARC} pathLength="100" />
        <path
          className="health-gauge__value"
          d={GAUGE_ARC}
          pathLength="100"
          strokeDasharray={`${score} 100`}
        />
      </svg>
      <div className="health-gauge__readout">
        <span className="health-gauge__score">{score}</span>
        <span className="health-gauge__band">{BAND_LABEL[band]}</span>
      </div>
    </div>
  );
}

function KpiTile({ label, value, sub, tone }) {
  return (
    <div className={`kpi-tile${tone ? ` kpi-tile--${tone}` : ""}`}>
      <span className="kpi-tile__label">{label}</span>
      <span className="kpi-tile__value">{value}</span>
      {sub && <span className="kpi-tile__sub">{sub}</span>}
    </div>
  );
}

function Panel({ title, action, children }) {
  return (
    <section className="insight-panel">
      <div className="insight-panel__head">
        <h2 className="insight-panel__title">{title}</h2>
        {action}
      </div>
      <div className="insight-panel__body">{children}</div>
    </section>
  );
}

function ProjectDashboardPage({
  projectName,
  tasks = [],
  changeOrders = [],
  notesDelays = [],
  inspections = [],
  dailyLogs = [],
  referenceDate,
  isLoadingTasks = false,
  isLoadingChangeOrders = false,
  isLoadingDelays = false,
  isLoadingInspections = false,
  isLoadingDailyLogs = false,
  formatDate,
  onNavigate,
  onLogout,
}) {
  const now = useMemo(
    () => referenceDate || new Date(),
    [referenceDate]
  );

  const insights = useMemo(() => {
    const projectDelays = notesDelays.filter(
      (entry) => entry.entry_type === "Delay"
    );
    const schedule = getScheduleHealth(tasks, now);
    const metrics = getDashboardMetrics({
      tasks,
      tasksThisWeek: [],
      projectDelays,
      changeOrders,
    });
    const health = getProjectHealthScore({
      activeDelays: projectDelays.length,
      pendingChangeOrders: metrics.pendingChangeOrders,
      inspectionIssues: getInspectionIssueCount(inspections),
      pastDueActivities: schedule.pastDueCount,
    });

    return {
      projectDelays,
      schedule,
      metrics,
      health,
      focus: getTodaysFocus({
        tasks,
        inspections,
        notesDelays,
        changeOrders,
        referenceDate: now,
      }),
      thisWeek: getThisWeekProgress(tasks, now),
      upcomingTasks: getUpcomingTasks(tasks, now, { limit: 5 }),
      attention: getAttentionActivities(tasks, now, { limit: 5 }),
      upcomingInspections: getUpcomingInspections(inspections, now, {
        limit: 5,
      }),
      recentDailyLogs: [...dailyLogs]
        .sort((left, right) => String(right.date).localeCompare(String(left.date)))
        .slice(0, 4),
      recentActivity: getRecentActivity(
        { dailyLogs, inspections, changeOrders, notesDelays },
        now,
        { limit: 8 }
      ),
      recentChangeOrders: [...changeOrders]
        .sort((left, right) => String(right.date).localeCompare(String(left.date)))
        .slice(0, 4),
      changeOrderTotals: getChangeOrderTotalsByCompany(changeOrders),
    };
  }, [tasks, inspections, notesDelays, changeOrders, dailyLogs, now]);

  const {
    schedule,
    metrics,
    health,
    focus,
    thisWeek,
    upcomingTasks,
    attention,
    upcomingInspections,
    recentDailyLogs,
    recentActivity,
    recentChangeOrders,
    changeOrderTotals,
  } = insights;

  const overviewLoading =
    isLoadingTasks || isLoadingChangeOrders || isLoadingDelays;
  const focusLoading =
    isLoadingTasks ||
    isLoadingInspections ||
    isLoadingDelays ||
    isLoadingChangeOrders;

  const dash = (loading, value) => (loading ? "—" : value);

  return (
    <ProjectLayout
      projectName={projectName}
      activeId="projectDashboard"
      onNavigate={onNavigate}
      onLogout={onLogout}
    >
      <PageHeader
        title={`${projectName} Dashboard`}
        actions={
          <span className="weather-chip" aria-label="Site weather (placeholder)">
            <Icon name="cloud-sun" size={18} />
            72°F · Clear
          </span>
        }
      />

      <section
        className="today-focus"
        aria-labelledby="today-focus-title"
        aria-busy={focusLoading}
      >
        <div className="today-focus__head">
          <div>
            <p className="today-focus__eyebrow">Today&rsquo;s Focus</p>
            <h2 id="today-focus-title" className="today-focus__headline">
              {focusLoading
                ? "Loading today's focus…"
                : focus.hasItems
                  ? `${focus.itemCount} ${
                      focus.itemCount === 1 ? "item needs" : "items need"
                    } your attention`
                  : "You're all clear for today"}
            </h2>
            <p className="today-focus__sub">
              {focusLoading
                ? "Pulling today's schedule, inspections, and open items…"
                : "Start here before you walk the site."}
            </p>
          </div>
          <Button variant="primary" onClick={() => onNavigate("scheduler")}>
            Open Schedule
          </Button>
        </div>

        <ul className="today-focus__stats">
          <li className="focus-stat">
            <span className="focus-stat__num">
              {dash(isLoadingTasks, focus.startingTodayCount)}
            </span>
            <span className="focus-stat__label">Activities starting today</span>
          </li>
          <li className="focus-stat">
            <span className="focus-stat__num">
              {dash(isLoadingInspections, focus.inspectionsDueTodayCount)}
            </span>
            <span className="focus-stat__label">Inspections due today</span>
          </li>
          <li
            className={`focus-stat${
              !isLoadingDelays && focus.activeDelays ? " focus-stat--alert" : ""
            }`}
          >
            <span className="focus-stat__num">
              {dash(isLoadingDelays, focus.activeDelays)}
            </span>
            <span className="focus-stat__label">Active delays</span>
          </li>
          <li
            className={`focus-stat${
              !isLoadingChangeOrders && focus.pendingChangeOrders
                ? " focus-stat--warning"
                : ""
            }`}
          >
            <span className="focus-stat__num">
              {dash(isLoadingChangeOrders, focus.pendingChangeOrders)}
            </span>
            <span className="focus-stat__label">Pending change orders</span>
          </li>
        </ul>
      </section>

      <section
        className="dashboard-metrics"
        aria-labelledby="project-overview-title"
        aria-busy={overviewLoading}
      >
        <h2 id="project-overview-title" className="visually-hidden">
          Project Overview
        </h2>
        <div className="kpi-grid">
          <div className="kpi-tile kpi-tile--gauge">
            <span className="kpi-tile__label">Project health</span>
            {overviewLoading ? (
              <span className="kpi-tile__value">—</span>
            ) : (
              <HealthGauge score={health.score} band={health.band} />
            )}
          </div>

          <KpiTile
            label="Schedule health"
            value={dash(isLoadingTasks, `${schedule.timelineElapsedPct}%`)}
            sub={
              isLoadingTasks
                ? "Loading schedule"
                : schedule.hasSchedule
                  ? `${schedule.activeCount} active · ${schedule.pastDueCount} past due`
                  : "No scheduled tasks yet"
            }
            tone={!isLoadingTasks && schedule.pastDueCount ? "alert" : undefined}
          />

          <KpiTile
            label="Active delays"
            value={dash(isLoadingDelays, metrics.recordedDelays)}
            sub="All delay entries"
            tone={!isLoadingDelays && metrics.recordedDelays ? "alert" : undefined}
          />

          <KpiTile
            label="Open change orders"
            value={dash(isLoadingChangeOrders, metrics.pendingChangeOrders)}
            sub={
              isLoadingChangeOrders
                ? "Loading exposure"
                : currencyFormatter.format(metrics.pendingChangeOrderValue)
            }
            tone={
              !isLoadingChangeOrders && metrics.pendingChangeOrders
                ? "warning"
                : undefined
            }
          />

          <KpiTile
            label="Starting this week"
            value={dash(isLoadingTasks, thisWeek.starting)}
            sub={
              isLoadingTasks
                ? "Loading schedule"
                : `${thisWeek.finishing} finishing · ${thisWeek.active} active`
            }
          />
        </div>
      </section>

      <div className="insight-grid">
        <Panel title="Critical activities">
          {isLoadingTasks ? (
            <LoadingState message="Loading schedule…" />
          ) : attention.length ? (
            <ul className="stack-list">
              {attention.map((task) => (
                <li key={task.id} className="stack-item">
                  <span className="stack-item__main">{task.name}</span>
                  <span
                    className={`stack-tag stack-tag--${
                      task.attention === "overdue" ? "alert" : "active"
                    }`}
                  >
                    {task.attention === "overdue"
                      ? `Past due ${formatDate(task.end_date)}`
                      : `Active · ends ${formatDate(task.end_date)}`}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="Nothing needs attention"
              description="Active and overdue activities will appear here."
            />
          )}
        </Panel>

        <Panel title="Upcoming inspections">
          {isLoadingInspections ? (
            <LoadingState message="Loading inspections…" />
          ) : upcomingInspections.length ? (
            <ul className="stack-list">
              {upcomingInspections.map((inspection) => (
                <li key={inspection.id} className="stack-item">
                  <span className="stack-item__main">
                    {inspection.inspection_type}
                    <span className="stack-item__meta">
                      {formatDate(inspection.date)}
                    </span>
                  </span>
                  <StatusBadge value={inspection.status} />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No upcoming inspections"
              description="Pending or future inspections will appear here."
            />
          )}
        </Panel>

        <Panel title="Upcoming tasks">
          {isLoadingTasks ? (
            <LoadingState message="Loading schedule…" />
          ) : upcomingTasks.length ? (
            <ul className="stack-list">
              {upcomingTasks.map((task) => (
                <li key={task.id} className="stack-item">
                  <span className="stack-item__main">
                    {task.name}
                    <span className="stack-item__meta">
                      {formatDate(task.start_date)} · {task.duration}d
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No upcoming tasks"
              description="Tasks starting in the next two weeks will appear here."
            />
          )}
        </Panel>

        <Panel title="Recent daily logs">
          {isLoadingDailyLogs ? (
            <LoadingState message="Loading daily logs…" />
          ) : recentDailyLogs.length ? (
            <ul className="stack-list">
              {recentDailyLogs.map((log) => (
                <li key={log.id} className="stack-item">
                  <span className="stack-item__main">
                    {log.company}
                    <span className="stack-item__meta">
                      {formatDate(log.date)} · {log.manpower} crew
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No daily logs yet"
              description="Recent field logs will appear here."
            />
          )}
        </Panel>
      </div>

      <div className="insight-grid insight-grid--bottom">
        <Panel title="Project activity">
          {recentActivity.length ? (
            <ul className="activity-feed">
              {recentActivity.map((item) => (
                <li key={item.key} className="activity-item">
                  <span className="activity-item__date">
                    {formatDate(item.date)}
                  </span>
                  <span className="activity-item__label">{item.label}</span>
                  {item.isNew && <span className="activity-item__new">New</span>}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No recent activity"
              description="Logs, inspections, and change orders will appear here."
            />
          )}
        </Panel>

        <Panel title="Recent changes">
          {isLoadingChangeOrders ? (
            <LoadingState message="Loading change orders…" />
          ) : recentChangeOrders.length ? (
            <>
              <ul className="stack-list">
                {recentChangeOrders.map((changeOrder) => (
                  <li key={changeOrder.id} className="stack-item">
                    <span className="stack-item__main">
                      {changeOrder.co_number}
                      <span className="stack-item__meta">
                        {changeOrder.company || "Unassigned"}
                      </span>
                    </span>
                    <StatusBadge value={changeOrder.status} />
                  </li>
                ))}
              </ul>
              {changeOrderTotals.length > 0 && (
                <div className="mini-chart" aria-hidden="true">
                  <ResponsiveContainer width="100%" height={140}>
                    <BarChart
                      data={changeOrderTotals}
                      margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="company" hide />
                      <YAxis hide />
                      <Tooltip formatter={(value) => [`$${value}`, "CO value"]} />
                      <Bar dataKey="total" fill="var(--brand)" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          ) : (
            <EmptyState
              title="No change orders yet"
              description="Recent change orders will appear here."
            />
          )}
        </Panel>

        <section
          className="insight-panel"
          aria-labelledby="quick-actions-title"
        >
          <div className="insight-panel__head">
            <h2 id="quick-actions-title" className="insight-panel__title">
              Quick Actions
            </h2>
          </div>
          <p className="insight-panel__hint">
            Start the field records used most often.
          </p>
          <div className="quick-action-stack">
            <Button variant="primary" onClick={() => onNavigate("dailyLogs")}>
              Add Daily Log
            </Button>
            <Button onClick={() => onNavigate("notesDelays")}>Report Delay</Button>
            <Button onClick={() => onNavigate("inspections")}>
              Add Inspection
            </Button>
            <Button onClick={() => onNavigate("changeOrders")}>
              Add Change Order
            </Button>
          </div>
        </section>
      </div>
    </ProjectLayout>
  );
}

export default ProjectDashboardPage;
