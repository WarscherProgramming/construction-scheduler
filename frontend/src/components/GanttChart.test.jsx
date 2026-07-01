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

  it("renders child tasks alongside their summary parent", () => {
    render(
      <GanttChart
        selectedTaskId={null}
        tasks={[
          {
            id: 1,
            name: "Foundations",
            duration: 2,
            start_date: "2026-06-20",
            end_date: "2026-06-23",
            parent_task_id: null,
            predecessor_task_id: null,
          },
          {
            id: 2,
            name: "Footings",
            duration: 2,
            start_date: "2026-06-20",
            end_date: "2026-06-21",
            parent_task_id: 1,
            predecessor_task_id: null,
          },
        ]}
      />
    );

    expect(
      screen.getByRole("img", {
        name: "Foundations summary, 06/20/2026 through 06/23/2026",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Footings, 06/20/2026 through 06/21/2026",
      })
    ).toBeInTheDocument();
  });

  it("hides children of a collapsed parent without rescaling the timeline", () => {
    render(
      <GanttChart
        selectedTaskId={null}
        tasks={[
          {
            id: 1,
            name: "Foundations",
            duration: 2,
            start_date: "2026-06-20",
            end_date: "2026-06-23",
            parent_task_id: null,
            predecessor_task_id: null,
            is_collapsed: 1,
          },
          {
            id: 2,
            name: "Footings",
            duration: 2,
            start_date: "2026-06-20",
            end_date: "2026-06-21",
            parent_task_id: 1,
            predecessor_task_id: null,
          },
        ]}
      />
    );

    expect(
      screen.getByRole("img", { name: /Foundations summary/ })
    ).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /Footings/ })).not.toBeInTheDocument();
    expect(screen.queryByText("Footings")).not.toBeInTheDocument();
  });

  it("labels critical-path tasks and explains them in the legend", () => {
    render(
      <GanttChart
        selectedTaskId={null}
        tasks={[
          {
            id: 1,
            name: "Structural Steel",
            duration: 2,
            start_date: "2026-06-22",
            end_date: "2026-06-23",
            parent_task_id: null,
            predecessor_task_id: null,
            is_critical: true,
            total_float: 0,
          },
          {
            id: 2,
            name: "Landscaping",
            duration: 1,
            start_date: "2026-06-22",
            end_date: "2026-06-22",
            parent_task_id: null,
            predecessor_task_id: null,
            is_critical: false,
            total_float: 1,
          },
        ]}
      />
    );

    expect(
      screen.getByRole("img", {
        name: "Structural Steel, 06/22/2026 through 06/23/2026, on the critical path",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Landscaping, 06/22/2026 through 06/22/2026",
      })
    ).toBeInTheDocument();
    expect(screen.getByText("Critical path")).toBeInTheDocument();
  });

  it("marks today on the timeline when it falls inside the project range", () => {
    const today = new Date();
    const iso = (date) => {
      const y = date.getFullYear();
      const m = String(date.getMonth() + 1).padStart(2, "0");
      const d = String(date.getDate()).padStart(2, "0");
      return `${y}-${m}-${d}`;
    };
    const end = new Date(today);
    end.setDate(end.getDate() + 3);

    const { container } = render(
      <GanttChart
        selectedTaskId={null}
        tasks={[
          {
            id: 1,
            name: "Mobilization",
            duration: 4,
            start_date: iso(today),
            end_date: iso(end),
            parent_task_id: null,
            predecessor_task_id: null,
          },
        ]}
      />
    );

    expect(container.querySelector(".gantt-today-column")).toBeInTheDocument();
    expect(container.querySelector(".gantt-day--today")).toBeInTheDocument();
    expect(screen.getByText("Today")).toBeInTheDocument();
  });
});
