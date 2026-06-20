import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import GanttChart from "./GanttChart";


describe("GanttChart", () => {
  it("describes task bars without relying on color", () => {
    render(
      <GanttChart
        selectedTaskId={1}
        tasks={[
          {
            id: 1,
            name: "Foundations",
            duration: 2,
            start_date: "2026-06-20",
            end_date: "2026-06-21",
            parent_task_id: null,
            predecessor_task_id: null,
          },
        ]}
      />
    );

    expect(
      screen.getByRole("img", {
        name: "Foundations, 06/20/2026 through 06/21/2026, selected",
      })
    ).toBeInTheDocument();
    expect(screen.getByText("Selected task.")).toHaveClass("visually-hidden");
  });
});
