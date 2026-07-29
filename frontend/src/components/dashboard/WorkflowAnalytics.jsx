import { formatDashboardCurrency } from "../../utils/dashboardSummary";
import WorkflowSummaryCard from "./WorkflowSummaryCard";


function workflowSummaries(dashboard) {
  return [
    {
      title: "RFIs",
      total: dashboard.rfis?.total,
      metrics: [
        { label: "Open", count: dashboard.rfis?.open },
        { label: "Overdue", count: dashboard.rfis?.overdue },
        { label: "Due soon", count: dashboard.rfis?.due_soon },
      ],
      emptyMessage: "No RFIs have been added.",
      page: "rfis",
      linkLabel: "View RFIs",
    },
    {
      title: "Submittals",
      total: dashboard.submittals?.total,
      metrics: [
        { label: "Pending", count: dashboard.submittals?.pending },
        { label: "Overdue", count: dashboard.submittals?.overdue },
        { label: "Due soon", count: dashboard.submittals?.due_soon },
      ],
      emptyMessage: "No Submittals have been added.",
      page: "submittals",
      linkLabel: "View Submittals",
    },
    {
      title: "Punch Items",
      total: dashboard.punch_items?.total,
      metrics: [
        { label: "Open", count: dashboard.punch_items?.open },
        { label: "Overdue", count: dashboard.punch_items?.overdue },
        {
          label: "Completed in last 7 days",
          count: dashboard.punch_items?.completed_last_7_days,
        },
      ],
      emptyMessage: "No Punch Items have been added.",
      page: "punchItems",
      linkLabel: "View Punch Items",
    },
    {
      title: "Change Orders",
      total: dashboard.change_orders?.total,
      metrics: [
        { label: "Active", count: dashboard.change_orders?.active },
        { label: "Approved", count: dashboard.change_orders?.approved },
        { label: "Rejected", count: dashboard.change_orders?.rejected },
        {
          label: "Unknown status",
          count: dashboard.change_orders?.unknown_status,
        },
      ],
      values: [
        {
          label: "Active value",
          value: formatDashboardCurrency(
            dashboard.change_orders?.active_value
          ),
        },
        {
          label: "Approved value",
          value: formatDashboardCurrency(
            dashboard.change_orders?.approved_value
          ),
        },
      ],
      emptyMessage: "No Change Orders have been added.",
      page: "changeOrders",
      linkLabel: "View Change Orders",
    },
  ];
}


function WorkflowAnalytics({
  dashboard,
  projectId,
  onNavigate,
}) {
  return (
    <section
      className="dashboard-insight-section dashboard-workflow-analytics"
      aria-labelledby="dashboard-workflow-title"
    >
      <div className="dashboard-insight-section__header">
        <h2 id="dashboard-workflow-title">Workflow Analytics</h2>
        <p>Current status distribution across project workflows.</p>
      </div>

      <div className="dashboard-workflow-grid">
        {workflowSummaries(dashboard).map((workflow) => (
          <WorkflowSummaryCard
            key={workflow.title}
            {...workflow}
            projectId={projectId}
            onNavigate={onNavigate}
          />
        ))}
      </div>
    </section>
  );
}

export default WorkflowAnalytics;
