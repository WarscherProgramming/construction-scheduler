import { buildAppHash } from "../../utils/navigation";
import {
  formatDashboardLinkContext,
  formatDashboardTimestamp,
} from "../../utils/dashboardSummary";


const RESOURCE_LABELS = {
  rfi: "RFI",
  submittal: "Submittal",
  punch_item: "Punch Item",
  change_order: "Change Order",
  attachment: "Document",
};

const TARGETS = {
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
  "change-orders": {
    page: "changeOrders",
    label: "View Change Orders",
  },
};


function textValue(value) {
  return typeof value === "string" ? value.trim() : "";
}


function RecentUpdateItem({
  update,
  projectId,
  onNavigate,
}) {
  const description = textValue(update?.description);
  const identifier = textValue(update?.identifier);
  const title =
    description ||
    identifier ||
    (update?.record_id
      ? `Record ${update.record_id}`
      : "Project record");
  const isKnownResource = Object.hasOwn(
    RESOURCE_LABELS,
    update?.resource_type
  );
  const resourceLabel =
    RESOURCE_LABELS[update?.resource_type] || "Project Record";
  const navigation =
    isKnownResource && update?.resource_type !== "attachment"
      ? TARGETS[update?.target_page]
      : null;
  const timestamp = formatDashboardTimestamp(update?.updated_at);
  const linkContext = formatDashboardLinkContext(
    identifier || description,
    resourceLabel
  );

  return (
    <li className="dashboard-recent-update">
      <p className="dashboard-recent-update__resource">
        {resourceLabel}
      </p>
      {identifier && description && identifier !== description && (
        <p className="dashboard-recent-update__identifier">
          {identifier}
        </p>
      )}
      <h3>{title}</h3>

      {timestamp && (
        <p className="dashboard-recent-update__timestamp">
          Updated{" "}
          <time dateTime={update.updated_at}>{timestamp}</time>
        </p>
      )}

      {navigation && projectId && (
        <a
          className="dashboard-insight-link"
          href={buildAppHash(navigation.page, projectId)}
          aria-label={`${navigation.label} for recent update ${linkContext}`}
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

export default RecentUpdateItem;
