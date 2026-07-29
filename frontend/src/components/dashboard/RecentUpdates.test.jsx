import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import RecentUpdates from "./RecentUpdates";


function recentUpdate(overrides = {}) {
  return {
    resource_type: "rfi",
    record_id: 17,
    identifier: "RFI-017",
    description: "Clarify storefront flashing",
    updated_at: "2026-07-28T21:14:00Z",
    target_page: "rfis",
    ...overrides,
  };
}


function expectedLocalTimestamp(value) {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}


describe("RecentUpdates", () => {
  it("renders supported resources in backend order", () => {
    const updates = [
      recentUpdate(),
      recentUpdate({
        resource_type: "submittal",
        record_id: 2,
        identifier: "SUB-002",
        description: "Storefront data",
        target_page: "submittals",
      }),
      recentUpdate({
        resource_type: "punch_item",
        record_id: 3,
        identifier: "PUNCH-003",
        description: "Repair lobby finish",
        target_page: "punch-items",
      }),
      recentUpdate({
        resource_type: "change_order",
        record_id: 4,
        identifier: "CO-004",
        description: "North entrance revision",
        target_page: "change-orders",
      }),
      recentUpdate({
        resource_type: "attachment",
        record_id: 5,
        identifier: "storefront-detail.pdf",
        description: "storefront-detail.pdf",
        target_page: "rfis",
      }),
    ];

    render(
      <RecentUpdates
        updates={updates}
        projectId={8}
        onNavigate={vi.fn()}
      />
    );

    const rows = screen.getAllByRole("listitem");
    expect(
      rows.map((row) => within(row).getByRole("heading").textContent)
    ).toEqual([
      "Clarify storefront flashing",
      "Storefront data",
      "Repair lobby finish",
      "North entrance revision",
      "storefront-detail.pdf",
    ]);
    expect(rows.map((row) => row.textContent)).toEqual(
      expect.arrayContaining([
        expect.stringContaining("RFI"),
        expect.stringContaining("Submittal"),
        expect.stringContaining("Punch Item"),
        expect.stringContaining("Change Order"),
        expect.stringContaining("Document"),
      ])
    );
  });

  it("uses the implemented description and identifier fallback chain", () => {
    render(
      <RecentUpdates
        updates={[
          recentUpdate({ record_id: 1, description: null }),
          recentUpdate({
            record_id: 42,
            identifier: "",
            description: "",
          }),
          recentUpdate({
            record_id: null,
            identifier: null,
            description: null,
          }),
        ]}
        projectId={8}
        onNavigate={vi.fn()}
      />
    );

    expect(
      screen.getByRole("heading", { name: "RFI-017" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Record 42" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Project record" })
    ).toBeInTheDocument();
  });

  it("formats aware timestamps locally and omits invalid values", () => {
    const validTimestamp = "2026-07-28T21:14:00Z";
    render(
      <RecentUpdates
        updates={[
          recentUpdate({ record_id: 1, updated_at: validTimestamp }),
          recentUpdate({ record_id: 2, updated_at: "invalid" }),
          recentUpdate({ record_id: 3, updated_at: null }),
        ]}
        projectId={8}
        onNavigate={vi.fn()}
      />
    );

    expect(
      screen.getByText(expectedLocalTimestamp(validTimestamp))
    ).toHaveAttribute("datetime", validTimestamp);
    expect(screen.getAllByRole("time")).toHaveLength(1);
    expect(screen.queryByText("Invalid Date")).not.toBeInTheDocument();
  });

  it("uses supported page routes and omits unsupported navigation", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    render(
      <RecentUpdates
        updates={[
          recentUpdate(),
          recentUpdate({
            resource_type: "submittal",
            record_id: 2,
            identifier: "SUB-002",
            target_page: "submittals",
          }),
          recentUpdate({
            resource_type: "punch_item",
            record_id: 3,
            identifier: "PUNCH-003",
            target_page: "punch-items",
          }),
          recentUpdate({
            resource_type: "change_order",
            record_id: 4,
            identifier: "CO-004",
            target_page: "change-orders",
          }),
          recentUpdate({
            resource_type: "rfi",
            record_id: 5,
            target_page: "unsupported",
          }),
        ]}
        projectId={31}
        onNavigate={onNavigate}
      />
    );

    const links = [
      [
        "View RFIs for recent update RFI-017",
        "#/projects/31/rfis",
        "rfis",
      ],
      [
        "View Submittals for recent update SUB-002",
        "#/projects/31/submittals",
        "submittals",
      ],
      [
        "View Punch Items for recent update PUNCH-003",
        "#/projects/31/punch-items",
        "punchItems",
      ],
      [
        "View Change Orders for recent update CO-004",
        "#/projects/31/change-orders",
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
    expect(screen.getAllByRole("link")).toHaveLength(4);
  });

  it("renders unknown resources neutrally and keeps documents non-navigable", () => {
    render(
      <RecentUpdates
        updates={[
          recentUpdate({
            resource_type: "inspection",
            target_page: "rfis",
            status: "Needs_Review",
          }),
          recentUpdate({
            resource_type: "attachment",
            record_id: 9,
            identifier: "safe-plan.pdf",
            description: "safe-plan.pdf",
            target_page: "project",
            storage_key: "private/storage/key",
            storage_path: "C:/private/path",
            signed_url: "https://example.test/private",
            mime_type: "application/pdf",
          }),
        ]}
        projectId={8}
        onNavigate={vi.fn()}
      />
    );

    expect(screen.getByText("Project Record")).toBeInTheDocument();
    expect(screen.getByText("Document")).toBeInTheDocument();
    expect(screen.queryByText("Needs_Review")).not.toBeInTheDocument();
    expect(screen.queryByText(/private\/storage|private\/path|signed_url/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("renders the complete bounded list supplied by the backend", () => {
    const updates = Array.from({ length: 8 }, (_, index) =>
      recentUpdate({
        record_id: index + 1,
        identifier: `RFI-${String(index + 1).padStart(3, "0")}`,
        description:
          index === 7
            ? "A".repeat(180)
            : `Recent update ${index + 1}`,
      })
    );

    render(
      <RecentUpdates
        updates={updates}
        projectId={8}
        onNavigate={vi.fn()}
      />
    );

    expect(screen.getAllByRole("listitem")).toHaveLength(8);
    expect(screen.getByText("A".repeat(180))).toBeInTheDocument();
  });

  it("uses factual wording when no recent updates are available", () => {
    render(
      <RecentUpdates
        updates={[]}
        projectId={8}
        onNavigate={vi.fn()}
      />
    );

    expect(
      screen.getByText("No recent record updates are available.")
    ).toBeInTheDocument();
    expect(screen.getByText(/update timestamps/i)).toBeInTheDocument();
    expect(screen.queryByText(/no activity|project inactive/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
