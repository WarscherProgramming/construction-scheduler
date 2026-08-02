import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ScheduleVarianceView from "./ScheduleVarianceView";


const filters = {
  includeSummaries: true,
  status: "",
  criticalChange: "",
  search: "",
  sort: "wbs",
  order: "asc",
  limit: 50,
  offset: 0,
};

const summary = {
  baseline_id: 7,
  baseline_name: "Contract Baseline",
  captured_at: "2026-07-01T16:00:00Z",
  baseline_leaf_task_count: 8,
  current_leaf_task_count: 9,
  project_finish_variance_workdays: 5,
  slipped_count: 2,
  improved_count: 1,
  added_count: 1,
  removed_count: 1,
  newly_critical_count: 1,
};

const tasks = [
  {
    task_id: 10,
    name: "Foundation",
    wbs: "1.1",
    is_summary: false,
    baseline_start_date: "2026-07-01",
    current_start_date: "2026-07-02",
    start_variance_workdays: 1,
    baseline_end_date: "2026-07-03",
    current_end_date: "2026-07-06",
    finish_variance_workdays: 1,
    baseline_duration: 3,
    current_duration: 4,
    duration_variance_days: 1,
    critical_change: "newly_critical",
    comparison_status: "slipped",
    hierarchy_changed: true,
    dependency_changed: false,
    duration_changed: true,
    manual_start_changed: false,
    order_changed: false,
  },
  {
    task_id: 11,
    name: "Added commissioning",
    wbs: "2",
    is_summary: false,
    baseline_start_date: null,
    current_start_date: "2026-08-01",
    start_variance_workdays: null,
    baseline_end_date: null,
    current_end_date: "2026-08-03",
    finish_variance_workdays: null,
    baseline_duration: null,
    current_duration: 2,
    duration_variance_days: null,
    critical_change: null,
    comparison_status: "added",
    hierarchy_changed: false,
    dependency_changed: false,
    duration_changed: false,
    manual_start_changed: false,
    order_changed: false,
  },
  {
    task_id: 12,
    name: "Removed allowance",
    wbs: "3",
    is_summary: false,
    baseline_start_date: "2026-08-04",
    current_start_date: null,
    start_variance_workdays: null,
    baseline_end_date: "2026-08-05",
    current_end_date: null,
    finish_variance_workdays: null,
    baseline_duration: 2,
    current_duration: null,
    duration_variance_days: null,
    critical_change: null,
    comparison_status: "removed",
    hierarchy_changed: false,
    dependency_changed: false,
    duration_changed: false,
    manual_start_changed: false,
    order_changed: false,
  },
];

function baselineState(overrides = {}) {
  return {
    variance: {
      baseline: { id: 7, name: "Contract Baseline" },
      summary,
      tasks,
      total: tasks.length,
      limit: 50,
      offset: 0,
    },
    filters,
    varianceError: null,
    isLoadingVariance: false,
    retryVariance: vi.fn(),
    updateFilters: vi.fn(),
    ...overrides,
  };
}


describe("ScheduleVarianceView", () => {
  it("shows a factual no-baseline state", () => {
    render(
      <ScheduleVarianceView
        baselines={baselineState({
          variance: {
            baseline: null,
            summary: null,
            tasks: [],
            total: 0,
            limit: 50,
            offset: 0,
          },
        })}
      />
    );

    expect(screen.getByText(/No comparison baseline is available/)).toBeInTheDocument();
  });

  it("renders textual summary metrics and task comparison context", () => {
    render(<ScheduleVarianceView baselines={baselineState()} />);

    expect(screen.getByText("5 workdays later")).toBeInTheDocument();
    expect(screen.getByText("Slipped tasks").nextElementSibling).toHaveTextContent("2");
    expect(screen.getByText("Improved tasks").nextElementSibling).toHaveTextContent("1");
    expect(screen.getByText("Added tasks").nextElementSibling).toHaveTextContent("1");
    expect(screen.getByText("Removed tasks").nextElementSibling).toHaveTextContent("1");
    expect(
      screen.getByText("Newly critical", { selector: "dt" }).nextElementSibling
    ).toHaveTextContent("1");
    expect(screen.getByText("Foundation")).toBeInTheDocument();
    expect(
      screen.getByText("Newly critical", { selector: "td" })
    ).toBeInTheDocument();
    expect(screen.getByText("Hierarchy changed, Duration changed")).toBeInTheDocument();
    expect(screen.getByText("Added commissioning")).toBeInTheDocument();
    expect(screen.getByText("Removed allowance")).toBeInTheDocument();
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
  });

  it("submits search and applies status, critical, sorting, and summary filters", async () => {
    const user = userEvent.setup();
    const updateFilters = vi.fn();
    render(
      <ScheduleVarianceView
        baselines={baselineState({ updateFilters })}
      />
    );

    await user.type(screen.getByLabelText("Search tasks"), "steel & deck");
    await user.click(screen.getByRole("button", { name: "Search variance tasks" }));
    expect(updateFilters).toHaveBeenCalledWith({ search: "steel & deck" });

    await user.selectOptions(screen.getByLabelText("Status"), "slipped");
    expect(updateFilters).toHaveBeenCalledWith({ status: "slipped" });
    await user.selectOptions(
      screen.getByLabelText("Critical change"),
      "newly_critical"
    );
    expect(updateFilters).toHaveBeenCalledWith({
      criticalChange: "newly_critical",
    });
    await user.selectOptions(
      screen.getByLabelText("Sort by"),
      "finish_variance:desc"
    );
    expect(updateFilters).toHaveBeenCalledWith({
      sort: "finish_variance",
      order: "desc",
    });
    await user.click(screen.getByLabelText("Include summary tasks"));
    expect(updateFilters).toHaveBeenCalledWith({ includeSummaries: false });
  });

  it("paginates through bounded task results", async () => {
    const user = userEvent.setup();
    const updateFilters = vi.fn();
    render(
      <ScheduleVarianceView
        baselines={baselineState({
          updateFilters,
          variance: {
            baseline: { id: 7, name: "Contract Baseline" },
            summary,
            tasks,
            total: 120,
            limit: 50,
            offset: 50,
          },
          filters: { ...filters, offset: 50 },
        })}
      />
    );

    expect(screen.getByText("51-100 of 120")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(updateFilters).toHaveBeenCalledWith({ offset: 0 });
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(updateFilters).toHaveBeenCalledWith({ offset: 100 });
  });

  it("announces loading and offers a local retry after failure", async () => {
    const user = userEvent.setup();
    const retryVariance = vi.fn();
    const { rerender } = render(
      <ScheduleVarianceView
        baselines={baselineState({ variance: null, isLoadingVariance: true })}
      />
    );
    expect(screen.getByText("Loading schedule variance...")).toBeInTheDocument();

    rerender(
      <ScheduleVarianceView
        baselines={baselineState({
          variance: null,
          varianceError: new Error("offline"),
          retryVariance,
        })}
      />
    );
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(retryVariance).toHaveBeenCalledOnce();
  });

  it("uses semantic table labels that support stacked mobile records", () => {
    const { container } = render(
      <ScheduleVarianceView baselines={baselineState()} />
    );

    expect(
      screen.getByRole("region", { name: "Schedule baseline comparison" })
    ).toBeInTheDocument();
    expect(screen.getByRole("table")).toHaveAccessibleName(
      "Current schedule compared with Contract Baseline"
    );
    expect(
      container.querySelector('td[data-label="Status / Changes"]')
    ).toBeInTheDocument();
  });
});
