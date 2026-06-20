import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RecordCell from "./RecordCell";
import RecordTable from "./RecordTable";


describe("RecordTable", () => {
  it("provides a labeled keyboard-scrollable region", () => {
    render(
      <RecordTable label="Daily logs" headers={["Date", "Company"]}>
        <tr>
          <RecordCell label="Date">06/20/2026</RecordCell>
          <RecordCell label="Company">Desert Concrete</RecordCell>
        </tr>
      </RecordTable>
    );

    const region = screen.getByRole("region", { name: "Daily logs" });

    expect(region).toHaveAttribute("tabindex", "0");
    expect(
      screen.getByRole("columnheader", { name: "Date" })
    ).toHaveAttribute("scope", "col");
    expect(screen.getByText("Desert Concrete")).toHaveAttribute(
      "data-label",
      "Company"
    );
  });

  it("shows a useful empty state when no rows exist", () => {
    render(
      <RecordTable
        label="Inspections"
        headers={["Date", "Status"]}
        emptyMessage="No inspections yet."
      />
    );

    expect(screen.getByText("No inspections yet.")).toBeInTheDocument();
  });

  it("shows loading instead of an empty-state message while fetching", () => {
    render(
      <RecordTable
        label="Change orders"
        headers={["Date", "Status"]}
        emptyMessage="No change orders yet."
        isLoading
        loadingMessage="Loading change orders…"
      />
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading change orders…"
    );
    expect(screen.queryByText("No change orders yet.")).not.toBeInTheDocument();
  });
});
