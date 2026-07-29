import StatusBadge from "../StatusBadge";
import { buildAppHash } from "../../utils/navigation";
import { formatOptionalDashboardDate } from "../../utils/dashboardSummary";


const RESOURCE_LABELS = {
  rfi: "RFI",
  submittal: "Submittal",
  punch_item: "Punch Item",
  task: "Schedule",
};

const TARGETS = {
  schedule: {
    page: "scheduler",
    label: "View Schedule",
  },
  rfis: {
    page: "rfis",
    label: "View RFIs",
  },
  submittals: {
    page: "submittals",
    label: "View Submittals",
  },
  "punch-items": {
    page: "punchItems",
    label: "View Punch Items",
  },
};

const SEVERITY_LABELS = {
  overdue: "Overdue",
  due_soon: "Due soon",
  informational: "Informational",
};


function textValue(value) {
  return typeof value === "string" ? value.trim() : "";
}


function readableValue(value, fallback) {
  const normalized = textValue(value).replace(/[_-]+/g, " ");
  if (!normalized) return fallback;

  return normalized.replace(/\b\w/g, (character) =>
    character.toUpperCase()
  );
}


function AttentionItem({
  item,
  projectId,
  onNavigate,
}) {
  const identifier = textValue(item?.identifier);
  const suppliedTitle = textValue(item?.title);
  const title =
    suppliedTitle ||
    identifier ||
    (item?.record_id
      ? `Record ${item.record_id}`
      : "Project record");
  const isKnownResource = Object.hasOwn(
    RESOURCE_LABELS,
    item?.resource_type
  );
  const resourceLabel =
    RESOURCE_LABELS[item?.resource_type] || "Project Item";
  const severityLabel =
    SEVERITY_LABELS[item?.severity] ||
    readableValue(item?.severity, "Status unavailable");
  const navigation =
    isKnownResource ? TARGETS[item?.target_page] : null;
  const formattedDate = formatOptionalDashboardDate(item?.due_date);
  const reason = textValue(item?.reason);

  return (
    <li className="dashboard-action-item">
      <div className="dashboard-action-item__metadata">
        <span className="dashboard-action-item__resource">
          {resourceLabel}
        </span>
        <StatusBadge value={severityLabel} />
      </div>

      {identifier && suppliedTitle && identifier !== suppliedTitle && (
        <p className="dashboard-action-item__identifier">
          {identifier}
        </p>
      )}
      <h3>{title}</h3>

      {formattedDate && (
        <p className="dashboard-action-item__detail">
          <span>
            {item?.resource_type === "task"
              ? "Planned finish"
              : "Due"}
          </span>{" "}
          <time dateTime={item.due_date}>{formattedDate}</time>
        </p>
      )}
      {reason && (
        <p className="dashboard-action-item__reason">{reason}</p>
      )}

      {navigation && projectId && (
        <a
          className="dashboard-action-item__link"
          href={buildAppHash(navigation.page, projectId)}
          onClick={(event) => {
            event.preventDefault();
            onNavigate?.(navigation.page);
          }}
        >
          {navigation.label}
        </a>
      )}
    </li>
  );
}

export default AttentionItem;
