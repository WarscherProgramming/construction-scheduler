import { describe, expect, it } from "vitest";

import {
  buildScheduleProgressSummary,
  formatProgressStatus,
  isTaskStatused,
  isValidStatusDate,
} from "./scheduleProgress";


describe("schedule progress utilities", () => {
  it("formats statuses and identifies statused tasks", () => {
    expect(formatProgressStatus("in_progress")).toBe("In Progress");
    expect(formatProgressStatus("unknown")).toBe("Not Started");
    expect(isTaskStatused({ progress_status: "completed" })).toBe(true);
    expect(isTaskStatused({ progress_status: "not_started" })).toBe(false);
  });

  it("validates strict local actual dates through the Data Date", () => {
    expect(isValidStatusDate("2026-03-09", "2026-03-09")).toBe(true);
    expect(isValidStatusDate("2026-03-10", "2026-03-09")).toBe(false);
    expect(isValidStatusDate("2026-02-30", "2026-03-09")).toBe(false);
    expect(isValidStatusDate("03/09/2026", "2026-03-09")).toBe(false);
  });

  it("builds duration-weighted leaf metrics without inflating summaries", () => {
    const summary = buildScheduleProgressSummary(
      [
        {
          id: 1,
          duration: 2,
          parent_task_id: null,
          progress_status: "in_progress",
          percent_complete: 50,
          end_date: "2026-03-12",
        },
        {
          id: 2,
          duration: 4,
          parent_task_id: 1,
          progress_status: "completed",
          percent_complete: 100,
          end_date: "2026-03-06",
        },
        {
          id: 3,
          duration: 2,
          parent_task_id: 1,
          progress_status: "in_progress",
          percent_complete: 50,
          out_of_sequence: true,
          end_date: "2026-03-13",
        },
      ],
      "2026-03-09"
    );

    expect(summary).toEqual({
      total_leaf_tasks: 2,
      not_started_count: 0,
      in_progress_count: 1,
      completed_count: 1,
      out_of_sequence_count: 1,
      percent_complete_weighted: 83.3,
      data_date: "2026-03-09",
      forecast_project_finish: "2026-03-13",
    });
  });

  it("returns stable empty metrics", () => {
    expect(buildScheduleProgressSummary([], "2026-03-09")).toMatchObject({
      total_leaf_tasks: 0,
      percent_complete_weighted: 0,
      forecast_project_finish: null,
    });
  });
});
