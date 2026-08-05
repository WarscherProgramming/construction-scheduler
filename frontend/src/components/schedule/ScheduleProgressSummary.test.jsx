import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ScheduleProgressSummary from "./ScheduleProgressSummary";


describe("ScheduleProgressSummary", () => {
  it("renders the authoritative server summary with textual labels", () => {
    render(
      <ScheduleProgressSummary
        summary={{
          total_leaf_tasks: 8,
          not_started_count: 3,
          in_progress_count: 2,
          completed_count: 3,
          out_of_sequence_count: 1,
          percent_complete_weighted: 62.5,
          data_date: "2026-03-09",
          forecast_project_finish: "2026-04-10",
        }}
        tasks={[]}
        dataDate="2026-03-09"
      />
    );

    expect(screen.getByRole("heading", { name: "Schedule Progress" }))
      .toBeInTheDocument();
    expect(screen.getByText("Status through 03/09/2026.")).toBeInTheDocument();
    expect(screen.getByText("8 leaf tasks")).toBeInTheDocument();
    expect(screen.getByText("Complete").nextElementSibling)
      .toHaveTextContent("62.5%");
    expect(screen.getByText("Out of Sequence").nextElementSibling)
      .toHaveTextContent("1");
    expect(screen.getByText("Forecast Finish").nextElementSibling)
      .toHaveTextContent("04/10/2026");
  });

  it("falls back to the current task collection when summary data is absent", () => {
    render(
      <ScheduleProgressSummary
        summary={null}
        dataDate="2026-03-09"
        tasks={[
          {
            id: 1,
            duration: 2,
            progress_status: "completed",
            percent_complete: 100,
            end_date: "2026-03-05",
          },
          {
            id: 2,
            duration: 2,
            progress_status: "not_started",
            percent_complete: 0,
            end_date: "2026-03-11",
          },
        ]}
      />
    );

    expect(screen.getByText("Complete").nextElementSibling)
      .toHaveTextContent("50%");
    expect(screen.getByText("Completed").nextElementSibling)
      .toHaveTextContent("1");
  });

  it("announces loading without showing stale metrics", () => {
    render(
      <ScheduleProgressSummary
        isLoading
        summary={{ percent_complete_weighted: 99 }}
        tasks={[]}
        dataDate="2026-03-09"
      />
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading schedule progress..."
    );
    expect(screen.queryByText("99%")).not.toBeInTheDocument();
  });
});
