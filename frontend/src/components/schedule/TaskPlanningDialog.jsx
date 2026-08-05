import { useEffect, useId, useMemo, useRef, useState } from "react";

import { parseLocalDateInputValue } from "../../utils/date";
import {
  buildWbsMap,
  getTaskDependencies,
} from "../../utils/taskReferences";
import Button from "../ui/Button";
import Icon from "../ui/Icon";


const CONSTRAINTS = [
  ["ASAP", "As Soon As Possible"],
  ["ALAP", "As Late As Possible"],
  ["SNET", "Start No Earlier Than"],
  ["SNLT", "Start No Later Than"],
  ["FNET", "Finish No Earlier Than"],
  ["FNLT", "Finish No Later Than"],
  ["MS", "Mandatory Start"],
  ["MF", "Mandatory Finish"],
];
const DEPENDENCY_TYPES = ["FS", "SS", "FF", "SF"];

function TaskPlanningDialog({
  task,
  tasks,
  displayId,
  isSubmitting = false,
  onSubmit,
  onCancel,
}) {
  const titleId = useId();
  const dialogRef = useRef(null);
  const milestoneRef = useRef(null);
  const [isMilestone, setIsMilestone] = useState(Boolean(task.is_milestone));
  const [duration, setDuration] = useState(task.duration ?? 1);
  const [regularDuration, setRegularDuration] = useState(
    task.is_milestone ? 1 : task.duration || 1
  );
  const [constraintType, setConstraintType] = useState(
    task.constraint_type || "ASAP"
  );
  const [constraintDate, setConstraintDate] = useState(
    task.constraint_date || ""
  );
  const [dependencies, setDependencies] = useState(() =>
    getTaskDependencies(task).map((dependency) => ({
      predecessor_task_id: String(dependency.predecessor_task_id),
      dependency_type: dependency.dependency_type || "FS",
      lag_days: String(dependency.lag_days || 0),
    }))
  );
  const [errors, setErrors] = useState({});
  const wbsMap = useMemo(() => buildWbsMap(tasks), [tasks]);
  const predecessorOptions = useMemo(
    () => tasks.filter((candidate) => candidate.id !== task.id),
    [task.id, tasks]
  );
  const requiresDate = !["ASAP", "ALAP"].includes(constraintType);

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    milestoneRef.current?.focus();
    return () => {
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
  }, []);

  useEffect(() => {
    const closeOnEscape = (event) => {
      if (event.key === "Escape" && !isSubmitting) onCancel();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [isSubmitting, onCancel]);

  const handleKeyDown = (event) => {
    if (event.key === "Escape" && !isSubmitting) {
      event.stopPropagation();
      onCancel();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable =
      dialogRef.current?.querySelectorAll(
        "select:not(:disabled), input:not(:disabled), button:not(:disabled)"
      ) || [];
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const updateDependency = (index, field, value) => {
    setDependencies((current) =>
      current.map((dependency, rowIndex) =>
        rowIndex === index ? { ...dependency, [field]: value } : dependency
      )
    );
    setErrors({});
  };

  const addDependency = () => {
    if (dependencies.length >= 50) {
      setErrors({ dependencies: "A task can have at most 50 predecessors." });
      return;
    }
    const used = new Set(
      dependencies.map((dependency) => dependency.predecessor_task_id)
    );
    const candidate = predecessorOptions.find(
      (option) => !used.has(String(option.id))
    );
    if (!candidate) {
      setErrors({ dependencies: "No additional predecessor is available." });
      return;
    }
    setDependencies((current) => [
      ...current,
      {
        predecessor_task_id: String(candidate.id),
        dependency_type: "FS",
        lag_days: "0",
      },
    ]);
    setErrors({});
  };

  const validate = () => {
    const nextErrors = {};
    const parsedDuration = Number(duration);
    if (
      !Number.isInteger(parsedDuration) ||
      parsedDuration < (isMilestone ? 0 : 1) ||
      parsedDuration > 36_500
    ) {
      nextErrors.duration = isMilestone
        ? "Milestones require zero duration."
        : "Enter 1 to 36500 workdays.";
    }
    if (isMilestone && task.progress_status === "in_progress") {
      nextErrors.milestone = "In Progress tasks cannot be milestones.";
    }
    if (requiresDate) {
      const parsedDate = parseLocalDateInputValue(constraintDate);
      if (!parsedDate) {
        nextErrors.constraintDate = "Select a constraint date.";
      } else if ([0, 6].includes(parsedDate.getDay())) {
        nextErrors.constraintDate = "Constraint dates must be workdays.";
      }
    }

    const predecessorIds = dependencies.map((dependency) =>
      Number(dependency.predecessor_task_id)
    );
    if (new Set(predecessorIds).size !== predecessorIds.length) {
      nextErrors.dependencies = "Each predecessor can only be added once.";
    }
    dependencies.forEach((dependency, index) => {
      const lag = Number(dependency.lag_days);
      if (
        !predecessorIds[index] ||
        !Number.isInteger(lag) ||
        lag < -36_500 ||
        lag > 36_500
      ) {
        nextErrors.dependencies =
          "Select each predecessor and enter a whole lag from -36500 to 36500.";
      }
    });
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!validate()) return;
    void onSubmit(task.id, {
      duration: Number(duration),
      is_milestone: isMilestone,
      constraint_type: constraintType,
      constraint_date: requiresDate ? constraintDate : null,
      dependencies: dependencies.map((dependency) => ({
        predecessor_task_id: Number(dependency.predecessor_task_id),
        dependency_type: dependency.dependency_type,
        lag_days: Number(dependency.lag_days),
      })),
    });
  };

  return (
    <div
      className="dialog-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isSubmitting) onCancel();
      }}
    >
      <div
        ref={dialogRef}
        className="dialog schedule-planning-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={handleKeyDown}
      >
        <div className="dialog__header">
          <span className="dialog__icon">
            <Icon name="calendar" size={20} />
          </span>
          <div className="dialog__text">
            <h2 id={titleId} className="dialog__title">
              Plan Task: {task.name}
            </h2>
            <p className="dialog__message">Task {displayId}</p>
          </div>
        </div>

        <form className="form-stack" noValidate onSubmit={handleSubmit}>
          <div className="schedule-planning-fields">
            <div className="field-group">
              <label className="schedule-checkbox">
                <input
                  ref={milestoneRef}
                  type="checkbox"
                  checked={isMilestone}
                  disabled={isSubmitting}
                  aria-describedby={
                    errors.milestone ? `${titleId}-milestone-error` : undefined
                  }
                  onChange={(event) => {
                    const checked = event.target.checked;
                    if (checked) {
                      setRegularDuration(Number(duration) || 1);
                      setDuration(0);
                    } else {
                      setDuration(regularDuration);
                    }
                    setIsMilestone(checked);
                    setErrors({});
                  }}
                />
                Milestone
              </label>
              {errors.milestone && (
                <span
                  id={`${titleId}-milestone-error`}
                  className="cell-error"
                  role="alert"
                >
                  {errors.milestone}
                </span>
              )}
            </div>
            <div className="field-group">
              <label className="field-label" htmlFor={`${titleId}-duration`}>
                Duration
              </label>
              <input
                id={`${titleId}-duration`}
                className="field-control"
                type="number"
                min={isMilestone ? "0" : "1"}
                max="36500"
                step="1"
                value={duration}
                disabled={isMilestone || isSubmitting}
                aria-invalid={Boolean(errors.duration)}
                onChange={(event) => {
                  setDuration(event.target.value);
                  setRegularDuration(event.target.value);
                  setErrors({});
                }}
              />
              {errors.duration && (
                <span className="cell-error" role="alert">
                  {errors.duration}
                </span>
              )}
            </div>
          </div>

          <div className="schedule-planning-fields">
            <div className="field-group">
              <label className="field-label" htmlFor={`${titleId}-constraint`}>
                Constraint
              </label>
              <select
                id={`${titleId}-constraint`}
                className="field-control"
                value={constraintType}
                disabled={isSubmitting}
                onChange={(event) => {
                  const value = event.target.value;
                  setConstraintType(value);
                  if (["ASAP", "ALAP"].includes(value)) setConstraintDate("");
                  setErrors({});
                }}
              >
                {CONSTRAINTS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            {requiresDate && (
              <div className="field-group">
                <label
                  className="field-label"
                  htmlFor={`${titleId}-constraint-date`}
                >
                  Constraint Date
                </label>
                <input
                  id={`${titleId}-constraint-date`}
                  className="field-control"
                  type="date"
                  value={constraintDate}
                  disabled={isSubmitting}
                  aria-invalid={Boolean(errors.constraintDate)}
                  onChange={(event) => {
                    setConstraintDate(event.target.value);
                    setErrors({});
                  }}
                />
                {errors.constraintDate && (
                  <span className="cell-error" role="alert">
                    {errors.constraintDate}
                  </span>
                )}
              </div>
            )}
          </div>

          <fieldset className="schedule-dependency-editor">
            <legend>Predecessors</legend>
            {dependencies.length === 0 ? (
              <p className="field-hint">No predecessors</p>
            ) : (
              <div className="schedule-dependency-list">
                {dependencies.map((dependency, index) => (
                  <div
                    className="schedule-dependency-row"
                    key={`${dependency.predecessor_task_id}:${index}`}
                  >
                    <div className="field-group">
                      <label
                        className="field-label"
                        htmlFor={`${titleId}-predecessor-${index}`}
                      >
                        Predecessor {index + 1}
                      </label>
                      <select
                        id={`${titleId}-predecessor-${index}`}
                        className="field-control"
                        value={dependency.predecessor_task_id}
                        disabled={isSubmitting}
                        onChange={(event) =>
                          updateDependency(
                            index,
                            "predecessor_task_id",
                            event.target.value
                          )
                        }
                      >
                        {predecessorOptions.map((option) => (
                          <option key={option.id} value={option.id}>
                            {wbsMap.get(option.id)} - {option.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="field-group">
                      <label
                        className="field-label"
                        htmlFor={`${titleId}-type-${index}`}
                      >
                        Type
                      </label>
                      <select
                        id={`${titleId}-type-${index}`}
                        className="field-control"
                        value={dependency.dependency_type}
                        disabled={isSubmitting}
                        onChange={(event) =>
                          updateDependency(
                            index,
                            "dependency_type",
                            event.target.value
                          )
                        }
                      >
                        {DEPENDENCY_TYPES.map((type) => (
                          <option key={type} value={type}>
                            {type}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="field-group">
                      <label
                        className="field-label"
                        htmlFor={`${titleId}-lag-${index}`}
                      >
                        Lag
                      </label>
                      <input
                        id={`${titleId}-lag-${index}`}
                        className="field-control"
                        type="number"
                        min="-36500"
                        max="36500"
                        step="1"
                        value={dependency.lag_days}
                        disabled={isSubmitting}
                        onChange={(event) =>
                          updateDependency(index, "lag_days", event.target.value)
                        }
                      />
                    </div>
                    <button
                      type="button"
                      className="schedule-icon-button schedule-icon-button--danger"
                      aria-label={`Remove predecessor ${index + 1}`}
                      title={`Remove predecessor ${index + 1}`}
                      disabled={isSubmitting}
                      onClick={() => {
                        setDependencies((current) =>
                          current.filter((_, rowIndex) => rowIndex !== index)
                        );
                        setErrors({});
                      }}
                    >
                      <Icon name="x" size={17} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            {errors.dependencies && (
              <span className="cell-error" role="alert">
                {errors.dependencies}
              </span>
            )}
            <Button
              size="sm"
              disabled={
                isSubmitting ||
                dependencies.length >= Math.min(50, predecessorOptions.length)
              }
              onClick={addDependency}
            >
              <Icon name="plus" size={16} />
              Add Predecessor
            </Button>
          </fieldset>

          <div className="dialog__actions">
            <Button disabled={isSubmitting} onClick={onCancel}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              aria-busy={isSubmitting}
            >
              {isSubmitting ? "Saving..." : "Save Planning"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default TaskPlanningDialog;
