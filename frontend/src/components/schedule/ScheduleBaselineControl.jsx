import { useState } from "react";

import { formatScheduleTimestamp } from "../../utils/scheduleVariance";
import Button from "../ui/Button";
import Card from "../ui/Card";
import ConfirmDialog from "../ui/ConfirmDialog";
import Icon from "../ui/Icon";
import CreateBaselineDialog from "./CreateBaselineDialog";


const SELECT_REQUIRED = "select-required";


function ScheduleBaselineControl({
  baselines,
  scheduleStartDate,
  taskCount,
  isScheduleLoading = false,
}) {
  const [createOpen, setCreateOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const active = baselines.baselines.filter((item) => item.status === "active");
  const archived = baselines.baselines.filter(
    (item) => item.status === "archived"
  );
  const selected = baselines.selectedBaseline;
  const selectValue = baselines.requiresSelection
    ? SELECT_REQUIRED
    : baselines.viewBaselineId == null
      ? ""
      : String(baselines.viewBaselineId);

  return (
    <Card
      title="Schedule Baselines"
      className="schedule-baseline-control"
      style={{ marginBottom: "var(--space-4)" }}
    >
      {createOpen && (
        <CreateBaselineDialog
          open
          scheduleStartDate={scheduleStartDate}
          taskCount={taskCount}
          isSubmitting={baselines.isCreating}
          serverError={baselines.mutationError}
          onSubmit={baselines.createBaseline}
          onCancel={() => setCreateOpen(false)}
          onClearError={baselines.clearMutationError}
        />
      )}
      <ConfirmDialog
        open={archiveOpen}
        destructive
        title={`Archive ${selected?.name || "baseline"}?`}
        message="The immutable snapshot will remain available for historical comparison, but it can no longer be the project default."
        confirmLabel="Archive Baseline"
        confirmDisabled={baselines.isArchiving}
        onConfirm={async () => {
          const result = await baselines.archiveBaseline(selected?.id);
          if (result) setArchiveOpen(false);
        }}
        onCancel={() => setArchiveOpen(false)}
      />

      {baselines.isLoadingList && !baselines.baselines.length ? (
        <p role="status">Loading schedule baselines...</p>
      ) : baselines.listError ? (
        <div className="schedule-baseline-inline-error" role="alert">
          <p>Schedule baselines are unavailable.</p>
          <Button size="sm" onClick={baselines.retryBaselines}>
            <Icon name="refresh" size={16} />
            Retry
          </Button>
        </div>
      ) : (
        <div className="form-stack schedule-baseline-fields">
          <div className="field-group">
            <label className="field-label" htmlFor="comparison-baseline">
              Comparison baseline
            </label>
            <select
              id="comparison-baseline"
              className="field-control"
              value={selectValue}
              disabled={baselines.isSelecting || !baselines.baselines.length}
              onChange={(event) => {
                if (event.target.value === SELECT_REQUIRED) return;
                void baselines.selectBaseline(event.target.value || null);
              }}
            >
              {baselines.requiresSelection && (
                <option value={SELECT_REQUIRED}>Select a baseline</option>
              )}
              <option value="">Automatic: newest active</option>
              {active.length > 0 && (
                <optgroup label="Active baselines">
                  {active.map((baseline) => (
                    <option key={baseline.id} value={baseline.id}>
                      {baseline.name}
                    </option>
                  ))}
                </optgroup>
              )}
              {archived.length > 0 && (
                <optgroup label="Archived baselines">
                  {archived.map((baseline) => (
                    <option key={baseline.id} value={baseline.id}>
                      {baseline.name} (Archived)
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>

          {selected ? (
            <p className="schedule-baseline-selection">
              <strong>{selected.name}</strong>
              <span>
                Captured {formatScheduleTimestamp(selected.captured_at)}
              </span>
              {selected.status === "archived" && <span>Archived baseline</span>}
            </p>
          ) : (
            <p className="field-hint">
              {baselines.baselines.length
                ? "Choose a baseline to compare the current schedule."
                : "No baselines have been captured for this project."}
            </p>
          )}

          {baselines.mutationError && !createOpen && (
            <p className="schedule-baseline-error" role="alert">
              {baselines.mutationError.message}
            </p>
          )}

          <Button
            variant="primary"
            disabled={baselines.isCreating || isScheduleLoading}
            title={
              isScheduleLoading
                ? "Schedule data must finish loading before capture"
                : undefined
            }
            onClick={() => {
              baselines.clearMutationError();
              setCreateOpen(true);
            }}
          >
            <Icon name="plus" size={16} />
            Create Baseline
          </Button>
          {selected?.status === "active" && (
            <Button
              variant="danger"
              disabled={baselines.isArchiving}
              onClick={() => setArchiveOpen(true)}
            >
              <Icon name="trash" size={16} />
              Archive Baseline
            </Button>
          )}
        </div>
      )}
    </Card>
  );
}


export default ScheduleBaselineControl;
