import { buildAppHash } from "../../utils/navigation";
import { formatDashboardCurrency } from "../../utils/dashboardSummary";
import DashboardMetricCard from "./DashboardMetricCard";


function resourceContext(total, emptyMessage, populatedMessage) {
  return total === 0 ? emptyMessage : populatedMessage;
}


function DashboardSummaryGrid({
  dashboard,
  projectId,
  onNavigate,
}) {
  const link = (page, label) => ({
    href: buildAppHash(page, projectId),
    linkLabel: label,
    onNavigate: () => onNavigate(page),
  });

  const primaryMetrics = [
    {
      label: "Past Planned Finish",
      value: dashboard.schedule.past_planned_finish_count,
      context: resourceContext(
        dashboard.schedule.task_count,
        "No schedule tasks have been added.",
        "Tasks with planned finish dates before the dashboard date."
      ),
      ...link("scheduler", "View schedule"),
    },
    {
      label: "Upcoming Starts",
      value: dashboard.schedule.upcoming_start_count,
      context: resourceContext(
        dashboard.schedule.task_count,
        "No schedule tasks have been added.",
        "Starts due in the next seven days."
      ),
      ...link("scheduler", "View upcoming schedule"),
    },
    {
      label: "Open RFIs",
      value: dashboard.rfis.open,
      context: resourceContext(
        dashboard.rfis.total,
        "No RFIs have been added.",
        `${dashboard.rfis.overdue} currently overdue.`
      ),
      ...link("rfis", "View RFIs"),
    },
    {
      label: "Overdue RFIs",
      value: dashboard.rfis.overdue,
      context: resourceContext(
        dashboard.rfis.total,
        "No RFIs have been added.",
        `${dashboard.rfis.due_soon} due in the next seven days.`
      ),
      ...link("rfis", "Review RFI deadlines"),
    },
    {
      label: "Pending Submittals",
      value: dashboard.submittals.pending,
      context: resourceContext(
        dashboard.submittals.total,
        "No Submittals have been added.",
        `${dashboard.submittals.overdue} currently overdue.`
      ),
      ...link("submittals", "View Submittals"),
    },
    {
      label: "Open Punch Items",
      value: dashboard.punch_items.open,
      context: resourceContext(
        dashboard.punch_items.total,
        "No Punch Items have been added.",
        `${dashboard.punch_items.overdue} currently overdue.`
      ),
      ...link("punchItems", "View Punch List"),
    },
    {
      label: "Active Change Order Value",
      value: formatDashboardCurrency(
        dashboard.change_orders.active_value
      ),
      context: resourceContext(
        dashboard.change_orders.total,
        "No Change Orders have been added.",
        `${dashboard.change_orders.active} active Change Orders.`
      ),
      ...link("changeOrders", "View Change Orders"),
    },
    {
      label: "Today's Daily Logs",
      value: dashboard.daily_logs.today_count,
      context: resourceContext(
        dashboard.daily_logs.total,
        "No Daily Logs have been added.",
        `${dashboard.daily_logs.today_manpower} workers recorded today.`
      ),
      ...link("dailyLogs", "View Daily Logs"),
    },
  ];

  const secondaryMetrics = [
    {
      label: "Overdue Submittals",
      value: dashboard.submittals.overdue,
      context: `${dashboard.submittals.due_soon} due in the next seven days.`,
      ...link("submittals", "Review Submittal deadlines"),
    },
    {
      label: "Overdue Punch Items",
      value: dashboard.punch_items.overdue,
      context: `${dashboard.punch_items.completed_last_7_days} completed in the last seven days.`,
      ...link("punchItems", "Review Punch Item deadlines"),
    },
    {
      label: "Approved Change Order Value",
      value: formatDashboardCurrency(
        dashboard.change_orders.approved_value
      ),
      context: `${dashboard.change_orders.approved} approved or executed.`,
      ...link("changeOrders", "Review approved Change Orders"),
    },
    {
      label: "Documents Uploaded",
      value: dashboard.documents.uploaded_last_7_days,
      context: resourceContext(
        dashboard.documents.total,
        "No documents have been uploaded.",
        "Uploaded during the last seven days."
      ),
    },
  ];

  return (
    <div className="dashboard-summary">
      <section aria-labelledby="dashboard-summary-title">
        <h2 id="dashboard-summary-title">Project Summary</h2>
        <div className="dashboard-summary-grid">
          {primaryMetrics.map((metric) => (
            <DashboardMetricCard key={metric.label} {...metric} />
          ))}
        </div>
      </section>

      <section aria-labelledby="dashboard-followup-title">
        <h2 id="dashboard-followup-title">Follow-up Indicators</h2>
        <div className="dashboard-summary-grid dashboard-summary-grid--compact">
          {secondaryMetrics.map((metric) => (
            <DashboardMetricCard key={metric.label} {...metric} />
          ))}
        </div>
      </section>
    </div>
  );
}

export default DashboardSummaryGrid;
