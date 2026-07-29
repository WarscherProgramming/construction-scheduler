import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import WorkflowAnalytics from "./WorkflowAnalytics";


const DASHBOARD = {
  rfis: { total: 12, open: 4, overdue: 2, due_soon: 1 },
  submittals: { total: 9, pending: 5, overdue: 1, due_soon: 2 },
  punch_items: {
    total: 7,
    open: 3,
    overdue: 2,
    completed_last_7_days: 1,
  },
  change_orders: {
    total: 6,
    active: 2,
    approved: 2,
    rejected: 1,
    unknown_status: 1,
    active_value: "1234567890.12",
    approved_value: "100.30",
  },
};


function workflowCard(name) {
  return screen
    .getByRole("heading", { level: 3, name })
    .closest("article");
}


function metricCount(card, label) {
  return within(card).getByText(label).parentElement.querySelector("strong");
}


describe("WorkflowAnalytics", () => {
  it("renders exact aggregate counts for all four workflows", () => {
    render(
      <WorkflowAnalytics
        dashboard={DASHBOARD}
        projectId={4}
        onNavigate={vi.fn()}
      />
    );

    const rfiCard = workflowCard("RFIs");
    const submittalCard = workflowCard("Submittals");
    const punchCard = workflowCard("Punch Items");
    const changeOrderCard = workflowCard("Change Orders");

    expect(within(rfiCard).getByText("12")).toBeInTheDocument();
    expect(metricCount(rfiCard, "Open")).toHaveTextContent("4");
    expect(metricCount(rfiCard, "Overdue")).toHaveTextContent("2");
    expect(metricCount(rfiCard, "Due soon")).toHaveTextContent("1");

    expect(metricCount(submittalCard, "Pending")).toHaveTextContent("5");
    expect(metricCount(submittalCard, "Overdue")).toHaveTextContent("1");
    expect(metricCount(punchCard, "Open")).toHaveTextContent("3");
    expect(
      metricCount(punchCard, "Completed in last 7 days")
    ).toHaveTextContent("1");

    expect(metricCount(changeOrderCard, "Active")).toHaveTextContent("2");
    expect(metricCount(changeOrderCard, "Approved")).toHaveTextContent("2");
    expect(metricCount(changeOrderCard, "Rejected")).toHaveTextContent("1");
    expect(
      metricCount(changeOrderCard, "Unknown status")
    ).toHaveTextContent("1");
  });

  it("keeps zero status counts visible when records exist", () => {
    render(
      <WorkflowAnalytics
        dashboard={{
          ...DASHBOARD,
          rfis: { total: 2, open: 0, overdue: 0, due_soon: 0 },
        }}
        projectId={4}
        onNavigate={vi.fn()}
      />
    );

    const rfiCard = workflowCard("RFIs");
    expect(metricCount(rfiCard, "Open")).toHaveTextContent("0");
    expect(metricCount(rfiCard, "Overdue")).toHaveTextContent("0");
    expect(
      rfiCard.querySelector(
        ".dashboard-workflow-metric__track"
      )
    ).toHaveAttribute("aria-hidden", "true");
  });

  it("uses factual empty messages for zero-total workflows", () => {
    const emptyDashboard = {
      rfis: { total: 0, open: 0, overdue: 0, due_soon: 0 },
      submittals: { total: 0, pending: 0, overdue: 0, due_soon: 0 },
      punch_items: {
        total: 0,
        open: 0,
        overdue: 0,
        completed_last_7_days: 0,
      },
      change_orders: {
        total: 0,
        active: 0,
        approved: 0,
        rejected: 0,
        unknown_status: 0,
        active_value: "0.00",
        approved_value: "0.00",
      },
    };

    render(
      <WorkflowAnalytics
        dashboard={emptyDashboard}
        projectId={4}
        onNavigate={vi.fn()}
      />
    );

    expect(screen.getByText("No RFIs have been added.")).toBeInTheDocument();
    expect(
      screen.getByText("No Submittals have been added.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("No Punch Items have been added.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("No Change Orders have been added.")
    ).toBeInTheDocument();
    expect(screen.getAllByText("$0.00")).toHaveLength(2);
    expect(screen.queryByText(/healthy|all clear|complete/i)).not.toBeInTheDocument();
  });

  it("formats decimal and large backend currency values without recalculating", () => {
    render(
      <WorkflowAnalytics
        dashboard={DASHBOARD}
        projectId={4}
        onNavigate={vi.fn()}
      />
    );

    expect(screen.getByText("$1,234,567,890.12")).toBeInTheDocument();
    expect(screen.getByText("$100.30")).toBeInTheDocument();
  });

  it("fails safely for unavailable counts while retaining known values", () => {
    render(
      <WorkflowAnalytics
        dashboard={{
          ...DASHBOARD,
          change_orders: {
            ...DASHBOARD.change_orders,
            total: null,
            active: -1,
            unknown_status: 7,
          },
        }}
        projectId={4}
        onNavigate={vi.fn()}
      />
    );

    const card = workflowCard("Change Orders");
    expect(within(card).getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(metricCount(card, "Unknown status")).toHaveTextContent("7");
  });

  it("uses active-project page links and does not mutate the response", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    const dashboard = structuredClone(DASHBOARD);
    const original = structuredClone(dashboard);

    render(
      <WorkflowAnalytics
        dashboard={dashboard}
        projectId={42}
        onNavigate={onNavigate}
      />
    );

    const links = [
      ["View RFIs in Workflow Analytics", "#/projects/42/rfis", "rfis"],
      [
        "View Submittals in Workflow Analytics",
        "#/projects/42/submittals",
        "submittals",
      ],
      [
        "View Punch Items in Workflow Analytics",
        "#/projects/42/punch-items",
        "punchItems",
      ],
      [
        "View Change Orders in Workflow Analytics",
        "#/projects/42/change-orders",
        "changeOrders",
      ],
    ];
    for (const [label, href, page] of links) {
      await user.tab();
      const link = screen.getByRole("link", { name: label });
      expect(link).toHaveFocus();
      expect(link).toHaveAttribute("href", href);
      await user.click(link);
      expect(onNavigate).toHaveBeenLastCalledWith(page);
    }
    expect(dashboard).toEqual(original);
  });
});
