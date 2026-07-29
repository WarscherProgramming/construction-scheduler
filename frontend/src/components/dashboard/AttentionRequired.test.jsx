import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AttentionRequired from "./AttentionRequired";


function attentionItem(overrides = {}) {
  return {
    resource_type: "rfi",
    record_id: 17,
    identifier: "RFI-017",
    title: "Clarify storefront flashing",
    due_date: "2026-07-24",
    reason: "Overdue",
    severity: "overdue",
    target_page: "rfis",
    ...overrides,
  };
}


describe("AttentionRequired", () => {
  it("renders every attention source in backend order with contextual dates", () => {
    const items = [
      attentionItem(),
      attentionItem({
        resource_type: "submittal",
        record_id: 4,
        identifier: "SUB-004",
        title: "Storefront data",
        due_date: "2026-07-23",
        target_page: "submittals",
      }),
      attentionItem({
        resource_type: "punch_item",
        record_id: 8,
        identifier: "PUNCH-008",
        title: "Repair lobby finish",
        due_date: "2026-07-22",
        target_page: "punch-items",
      }),
      attentionItem({
        resource_type: "task",
        record_id: 12,
        identifier: "Task 12",
        title: "Install storefront",
        due_date: "2026-07-20",
        reason: "Past planned finish",
        severity: "informational",
        target_page: "schedule",
      }),
    ];

    render(
      <AttentionRequired
        items={items}
        projectId={7}
        onNavigate={vi.fn()}
      />
    );

    const rows = screen.getAllByRole("listitem");
    expect(rows).toHaveLength(4);
    expect(
      rows.map((row) => within(row).getByRole("heading").textContent)
    ).toEqual([
      "Clarify storefront flashing",
      "Storefront data",
      "Repair lobby finish",
      "Install storefront",
    ]);
    expect(rows.map((row) => row.textContent)).toEqual(
      expect.arrayContaining([
        expect.stringContaining("RFI"),
        expect.stringContaining("Submittal"),
        expect.stringContaining("Punch Item"),
        expect.stringContaining("Schedule"),
      ])
    );

    expect(within(rows[0]).getByText("Due")).toBeInTheDocument();
    expect(within(rows[0]).getByText("July 24, 2026")).toHaveAttribute(
      "datetime",
      "2026-07-24"
    );
    expect(within(rows[3]).getByText("Planned finish")).toBeInTheDocument();
    expect(within(rows[3]).getByText("Past planned finish")).toBeInTheDocument();
    expect(within(rows[3]).getByText("Informational")).toBeInTheDocument();
    expect(within(rows[3]).queryByText("Overdue")).not.toBeInTheDocument();
  });

  it("uses restrained title and enum fallbacks without unsafe links", () => {
    render(
      <AttentionRequired
        items={[
          attentionItem({
            record_id: 18,
            identifier: "RFI-018",
            title: null,
          }),
          attentionItem({
            resource_type: "inspection",
            record_id: 42,
            identifier: null,
            title: "",
            severity: "needs_review",
            target_page: "schedule",
          }),
          attentionItem({
            record_id: 19,
            identifier: "RFI-019",
            target_page: "unsupported",
          }),
        ]}
        projectId={7}
        onNavigate={vi.fn()}
      />
    );

    expect(
      screen.getByRole("heading", { name: "RFI-018" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Record 42" })
    ).toBeInTheDocument();
    expect(screen.getByText("Project Item")).toBeInTheDocument();
    expect(screen.getByText("Needs Review")).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(
      screen.queryByRole("link", { name: /inspection|project item/i })
    ).not.toBeInTheDocument();
  });

  it("uses page-level navigation for the active project", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    render(
      <AttentionRequired
        items={[
          attentionItem(),
          attentionItem({
            resource_type: "submittal",
            record_id: 2,
            identifier: "SUB-002",
            target_page: "submittals",
          }),
          attentionItem({
            resource_type: "punch_item",
            record_id: 3,
            identifier: "PUNCH-003",
            target_page: "punch-items",
          }),
          attentionItem({
            resource_type: "task",
            record_id: 4,
            identifier: "Task 4",
            target_page: "schedule",
          }),
        ]}
        projectId={29}
        onNavigate={onNavigate}
      />
    );

    const expectedLinks = [
      ["View RFIs for attention item RFI-017", "#/projects/29/rfis", "rfis"],
      [
        "View Submittals for attention item SUB-002",
        "#/projects/29/submittals",
        "submittals",
      ],
      [
        "View Punch Items for attention item PUNCH-003",
        "#/projects/29/punch-items",
        "punchItems",
      ],
      [
        "View Schedule for attention item Task 4",
        "#/projects/29/schedule",
        "scheduler",
      ],
    ];

    for (const [label, href, page] of expectedLinks) {
      await user.tab();
      const link = screen.getByRole("link", { name: label });
      expect(link).toHaveFocus();
      expect(link).toHaveAttribute("href", href);
      await user.click(link);
      expect(onNavigate).toHaveBeenLastCalledWith(page);
    }
  });

  it("renders the complete bounded list supplied by the backend", () => {
    const longTitle = "A".repeat(180);
    const items = Array.from({ length: 10 }, (_, index) =>
      attentionItem({
        record_id: index + 1,
        identifier: `RFI-${String(index + 1).padStart(3, "0")}`,
        title: index === 9 ? longTitle : `Item ${index + 1}`,
      })
    );

    render(
      <AttentionRequired
        items={items}
        projectId={7}
        onNavigate={vi.fn()}
      />
    );

    expect(screen.getAllByRole("listitem")).toHaveLength(10);
    expect(screen.getByText(longTitle)).toBeInTheDocument();
  });

  it("omits absent and invalid dates without displaying Invalid Date", () => {
    render(
      <AttentionRequired
        items={[
          attentionItem({ record_id: 1, due_date: null }),
          attentionItem({ record_id: 2, due_date: "2026-02-31" }),
        ]}
        projectId={7}
        onNavigate={vi.fn()}
      />
    );

    expect(screen.queryByText("Invalid Date")).not.toBeInTheDocument();
    expect(screen.queryByText("Due")).not.toBeInTheDocument();
    expect(screen.queryByRole("time")).not.toBeInTheDocument();
  });

  it("keeps a factual empty state visible", () => {
    render(
      <AttentionRequired
        items={[]}
        projectId={7}
        onNavigate={vi.fn()}
      />
    );

    expect(
      screen.getByText(
        "No attention items were identified for this dashboard date."
      )
    ).toBeInTheDocument();
    expect(screen.getByText(/not a complete risk assessment/i)).toBeInTheDocument();
    expect(screen.queryByText(/everything is on track|no risks/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
