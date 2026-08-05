import { useState } from "react";

import {
  formatComparisonStatus,
  formatCriticalChange,
  formatDurationVariance,
  formatScheduleDate,
  formatScheduleTimestamp,
  formatWorkdayVariance,
  getStructuralChanges,
} from "../../utils/scheduleVariance";
import { formatProgressStatus } from "../../utils/scheduleProgress";
import LoadingState from "../LoadingState";
import StatusBadge from "../StatusBadge";
import Button from "../ui/Button";
import Icon from "../ui/Icon";


function VarianceSummary({ summary }) {
  const metrics = [
    ["Project finish", formatWorkdayVariance(summary.project_finish_variance_workdays)],
    ["Slipped tasks", summary.slipped_count],
    ["Improved tasks", summary.improved_count],
    ["Added tasks", summary.added_count],
    ["Removed tasks", summary.removed_count],
    ["Newly critical", summary.newly_critical_count],
  ];

  return (
    <section aria-labelledby="variance-summary-title">
      <div className="schedule-variance-heading">
        <div>
          <h2 id="variance-summary-title">Variance Summary</h2>
          <p>
            Compared with {summary.baseline_name}, captured{" "}
            {formatScheduleTimestamp(summary.captured_at)}.
          </p>
        </div>
      </div>
      <dl className="schedule-variance-summary">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}


function VarianceFilters({ filters, isLoading, onChange }) {
  const [search, setSearch] = useState(filters.search);

  return (
    <form
      className="schedule-variance-filters"
      aria-label="Schedule variance filters"
      onSubmit={(event) => {
        event.preventDefault();
        void onChange({ search });
      }}
    >
      <div className="field-group schedule-variance-search">
        <label className="field-label" htmlFor="variance-search">
          Search tasks
        </label>
        <div className="schedule-variance-search-input">
          <input
            id="variance-search"
            className="field-control"
            maxLength={200}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <Button type="submit" disabled={isLoading} aria-label="Search variance tasks">
            <Icon name="search" size={16} />
          </Button>
        </div>
      </div>
      <div className="field-group">
        <label className="field-label" htmlFor="variance-status">
          Status
        </label>
        <select
          id="variance-status"
          className="field-control"
          value={filters.status}
          disabled={isLoading}
          onChange={(event) => void onChange({ status: event.target.value })}
        >
          <option value="">All statuses</option>
          {[
            "slipped",
            "improved",
            "unchanged",
            "added",
            "removed",
            "unscheduled",
            "incomparable",
          ].map((status) => (
            <option key={status} value={status}>
              {formatComparisonStatus(status)}
            </option>
          ))}
        </select>
      </div>
      <div className="field-group">
        <label className="field-label" htmlFor="variance-critical">
          Critical change
        </label>
        <select
          id="variance-critical"
          className="field-control"
          value={filters.criticalChange}
          disabled={isLoading}
          onChange={(event) =>
            void onChange({ criticalChange: event.target.value })
          }
        >
          <option value="">All critical states</option>
          {[
            "newly_critical",
            "no_longer_critical",
            "remained_critical",
            "remained_noncritical",
          ].map((change) => (
            <option key={change} value={change}>
              {formatCriticalChange(change)}
            </option>
          ))}
        </select>
      </div>
      <div className="field-group">
        <label className="field-label" htmlFor="variance-sort">
          Sort by
        </label>
        <select
          id="variance-sort"
          className="field-control"
          value={`${filters.sort}:${filters.order}`}
          disabled={isLoading}
          onChange={(event) => {
            const [sort, order] = event.target.value.split(":");
            void onChange({ sort, order });
          }}
        >
          <option value="wbs:asc">WBS</option>
          <option value="name:asc">Task name</option>
          <option value="finish_variance:desc">Finish variance: latest first</option>
          <option value="finish_variance:asc">Finish variance: earliest first</option>
          <option value="status:asc">Status</option>
        </select>
      </div>
      <label className="schedule-variance-checkbox">
        <input
          type="checkbox"
          checked={filters.includeSummaries}
          disabled={isLoading}
          onChange={(event) =>
            void onChange({ includeSummaries: event.target.checked })
          }
        />
        Include summary tasks
      </label>
    </form>
  );
}


function ComparisonCell({ label, baseline, current, variance }) {
  return (
    <div className="schedule-variance-comparison">
      <span><strong>Baseline:</strong> {baseline}</span>
      <span><strong>Current:</strong> {current}</span>
      <span><strong>{label}:</strong> {variance}</span>
    </div>
  );
}


function ScheduleVarianceView({ baselines }) {
  if (baselines.isLoadingVariance && !baselines.variance) {
    return <LoadingState message="Loading schedule variance..." />;
  }

  if (baselines.varianceError) {
    return (
      <div className="schedule-load-error" role="alert">
        <p>Schedule variance is unavailable. Current schedule data is unchanged.</p>
        <Button onClick={() => baselines.retryVariance()}>
          <Icon name="refresh" size={16} />
          Retry
        </Button>
      </div>
    );
  }

  const variance = baselines.variance;
  if (!variance?.baseline || !variance.summary) {
    return (
      <div className="schedule-empty-state" role="status">
        No comparison baseline is available. Capture or select a baseline to
        measure schedule variance.
      </div>
    );
  }

  const { summary, tasks, total, limit, offset } = variance;

  return (
    <div className="schedule-variance-view">
      <VarianceSummary summary={summary} />
      <div className="schedule-variance-actions">
        <div>
          <p>
            {summary.current_leaf_task_count} current leaf tasks and{" "}
            {summary.baseline_leaf_task_count} baseline leaf tasks.
          </p>
          {Number.isInteger(summary.completed_count) && (
            <p className="schedule-variance-progress-summary">
              {summary.completed_count} completed, {summary.in_progress_count}{" "}
              in progress, {summary.not_started_count} not started, and{" "}
              {summary.out_of_sequence_count} out of sequence through{" "}
              {formatScheduleDate(summary.current_data_date)}.
            </p>
          )}
        </div>
        <Button
          size="sm"
          disabled={baselines.isLoadingVariance}
          onClick={() => baselines.retryVariance()}
        >
          <Icon name="refresh" size={16} />
          Refresh
        </Button>
      </div>
      <VarianceFilters
        key={baselines.filters.search}
        filters={baselines.filters}
        isLoading={baselines.isLoadingVariance}
        onChange={baselines.updateFilters}
      />

      {tasks.length === 0 ? (
        <div className="schedule-empty-state" role="status">
          {total === 0 && !baselines.filters.search && !baselines.filters.status
            ? "This comparison contains no schedule tasks."
            : "No tasks match the current variance filters."}
        </div>
      ) : (
        <div
          className="table-scroll-region schedule-variance-table-region"
          role="region"
          aria-label="Schedule baseline comparison"
          tabIndex={0}
        >
          <table className="data-table schedule-variance-table">
            <caption className="visually-hidden">
              Current schedule compared with {summary.baseline_name}
            </caption>
            <thead>
              <tr>
                <th scope="col">WBS / Task</th>
                <th scope="col">Start</th>
                <th scope="col">Finish</th>
                <th scope="col">Duration</th>
                <th scope="col">Critical path</th>
                <th scope="col">Status / Changes</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => {
                const changes = getStructuralChanges(task);
                return (
                  <tr
                    key={`${task.task_id}:${task.comparison_status}`}
                    className={task.is_summary ? "schedule-variance-summary-row" : undefined}
                  >
                    <td data-label="WBS / Task">
                      <span className="schedule-variance-task">
                        <strong>{task.wbs}</strong>
                        <span>{task.name}</span>
                        {task.is_summary && <span>Summary task</span>}
                      </span>
                    </td>
                    <td data-label="Start">
                      <ComparisonCell
                        label="Variance"
                        baseline={formatScheduleDate(task.baseline_start_date)}
                        current={formatScheduleDate(task.current_start_date)}
                        variance={formatWorkdayVariance(task.start_variance_workdays)}
                      />
                    </td>
                    <td data-label="Finish">
                      <ComparisonCell
                        label="Variance"
                        baseline={formatScheduleDate(task.baseline_end_date)}
                        current={formatScheduleDate(task.current_end_date)}
                        variance={formatWorkdayVariance(task.finish_variance_workdays)}
                      />
                    </td>
                    <td data-label="Duration">
                      <ComparisonCell
                        label="Change"
                        baseline={task.baseline_duration ?? "Unavailable"}
                        current={task.current_duration ?? "Unavailable"}
                        variance={formatDurationVariance(task.duration_variance_days)}
                      />
                    </td>
                    <td data-label="Critical path">
                      {formatCriticalChange(task.critical_change)}
                    </td>
                    <td data-label="Status / Changes">
                      <StatusBadge value={formatComparisonStatus(task.comparison_status)} />
                      {task.progress_status && (
                        <span className="schedule-variance-live-progress">
                          <strong>Live progress:</strong>{" "}
                          {formatProgressStatus(task.progress_status)}, {task.percent_complete}%
                          {task.remaining_duration == null
                            ? ""
                            : `, ${task.remaining_duration} workdays remaining`}
                        </span>
                      )}
                      {task.out_of_sequence && (
                        <span className="schedule-sequence-warning">
                          <Icon name="alert-triangle" size={15} />
                          Out of sequence
                          {task.out_of_sequence_reason && (
                            <span>{task.out_of_sequence_reason}</span>
                          )}
                        </span>
                      )}
                      <span className="schedule-variance-change-list">
                        {changes.length ? changes.join(", ") : "No structural changes"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {total > limit && (
        <nav className="schedule-variance-pagination" aria-label="Variance task pages">
          <Button
            size="sm"
            disabled={offset === 0 || baselines.isLoadingVariance}
            onClick={() => baselines.updateFilters({ offset: Math.max(0, offset - limit) })}
          >
            <Icon name="chevron-left" size={16} />
            Previous
          </Button>
          <span>
            {offset + 1}-{Math.min(offset + limit, total)} of {total}
          </span>
          <Button
            size="sm"
            disabled={offset + limit >= total || baselines.isLoadingVariance}
            onClick={() => baselines.updateFilters({ offset: offset + limit })}
          >
            Next
            <Icon name="chevron-right" size={16} />
          </Button>
        </nav>
      )}
    </div>
  );
}


export default ScheduleVarianceView;
