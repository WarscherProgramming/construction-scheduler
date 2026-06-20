import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RecordTable from "./RecordTable";


describe("RecordTable", () => {
  it("provides a labeled keyboard-scrollable region", () => {
    render(
      <RecordTable label="Daily logs" headers={["Date", "Company"]}>
        <tr>
          <td>06/20/2026</td>
          <td>Desert Concrete</td>
        </tr>
      </RecordTable>
    );

    const region = screen.getByRole("region", { name: "Daily logs" });

    expect(region).toHaveAttribute("tabindex", "0");
    expect(
      screen.getByRole("columnheader", { name: "Date" })
    ).toHaveAttribute("scope", "col");
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
});
