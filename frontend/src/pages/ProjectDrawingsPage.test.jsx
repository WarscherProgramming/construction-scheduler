import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProjectDrawingsPage from "./ProjectDrawingsPage";


const useDrawingsMock = vi.hoisted(() => vi.fn());
const relationshipPanelMock = vi.hoisted(() => vi.fn());

vi.mock("../hooks/useDrawings", () => ({ default: useDrawingsMock }));
vi.mock("../components/relationships/RelationshipPanel", () => ({
  default: (props) => {
    relationshipPanelMock(props);
    return (
      <section aria-label={props.title}>
        <h2>{props.title}</h2>
      </section>
    );
  },
}));


const CURRENT_REVISION = {
  id: 30,
  drawing_sheet_id: 20,
  document_id: 40,
  revision_code: "1",
  revision_date: "2026-07-30",
  description: "Current issue",
  sequence_number: 2,
  is_current: true,
  superseded_at: null,
  superseded_by_revision_id: null,
  original_filename: "A-101-r1.pdf",
  size_bytes: 1536,
  created_at: "2026-07-30T12:00:00Z",
  issue_ids: [50],
};

const SUPERSEDED_REVISION = {
  ...CURRENT_REVISION,
  id: 29,
  document_id: 39,
  revision_code: "0",
  sequence_number: 1,
  is_current: false,
  superseded_at: "2026-07-30T12:00:00Z",
  superseded_by_revision_id: 30,
  issue_ids: [],
};

const SHEET = {
  id: 20,
  project_id: 1,
  drawing_set_id: 10,
  drawing_set_name: "IFC",
  sheet_number: "A-101",
  title: "Floor Plan",
  discipline: "A",
  description: "Level one",
  status: "active",
  current_revision_id: 30,
  current_revision: CURRENT_REVISION,
  revision_count: 2,
  created_at: "2026-07-29T12:00:00Z",
  updated_at: "2026-07-30T12:00:00Z",
};

const DRAWING_SET = {
  id: 10,
  project_id: 1,
  name: "IFC",
  description: "Issued for construction",
  status: "active",
  issue_date: "2026-07-30",
  sheet_count: 1,
  issue_count: 1,
};

const ISSUE = {
  id: 50,
  project_id: 1,
  drawing_set_id: 10,
  drawing_set_name: "IFC",
  name: "IFC Release",
  issue_number: "ISS-001",
  issue_date: "2026-07-30",
  purpose: "construction",
  status: "draft",
  notes: "Field release",
  revisions: [],
};

let hookState;


function props(overrides = {}) {
  return {
    projectId: 1,
    projectName: "Riverside",
    onNavigate: vi.fn(),
    onLogout: vi.fn(),
    onRequestError: vi.fn(),
    ...overrides,
  };
}


describe("ProjectDrawingsPage", () => {
  beforeEach(() => {
    hookState = {
      query: {
        drawingSetId: "",
        discipline: "",
        search: "",
        sheetStatus: "",
        sort: "sheet_number",
        order: "asc",
        limit: 50,
        offset: 0,
      },
      drawingSets: [DRAWING_SET],
      register: {
        project_id: 1,
        sheets: [SHEET],
        pagination: {
          limit: 50,
          offset: 0,
          total: 1,
          has_more: false,
        },
      },
      selectedSetId: 10,
      setSheets: [SHEET],
      issues: [ISSUE],
      revisions: [CURRENT_REVISION, SUPERSEDED_REVISION],
      revisionSheetId: 20,
      isLoadingSets: false,
      isLoadingRegister: false,
      isLoadingSetDetails: false,
      isLoadingRevisions: false,
      operationError: null,
      activeOperations: [],
      updateQuery: vi.fn(),
      setSelectedSetId: vi.fn(),
      loadRevisions: vi.fn().mockResolvedValue([
        CURRENT_REVISION,
        SUPERSEDED_REVISION,
      ]),
      downloadRevision: vi.fn(),
      refresh: vi.fn(),
      clearOperationError: vi.fn(),
      createSet: vi.fn().mockResolvedValue(DRAWING_SET),
      updateSet: vi.fn().mockResolvedValue(DRAWING_SET),
      archiveSet: vi.fn().mockResolvedValue({
        ...DRAWING_SET,
        status: "archived",
      }),
      createSheet: vi.fn().mockResolvedValue(SHEET),
      updateSheet: vi.fn(),
      archiveSheet: vi.fn().mockResolvedValue({
        ...SHEET,
        status: "archived",
      }),
      uploadRevision: vi.fn().mockResolvedValue(CURRENT_REVISION),
      createIssue: vi.fn().mockResolvedValue(ISSUE),
      updateIssue: vi.fn().mockResolvedValue(ISSUE),
      deleteIssue: vi.fn(),
      addIssueRevision: vi.fn().mockResolvedValue(ISSUE),
      removeIssueRevision: vi.fn().mockResolvedValue(ISSUE),
      issueIssue: vi.fn().mockResolvedValue({
        ...ISSUE,
        status: "issued",
      }),
      voidIssue: vi.fn().mockResolvedValue({
        ...ISSUE,
        status: "void",
      }),
    };
    useDrawingsMock.mockReset();
    useDrawingsMock.mockImplementation(() => hookState);
    relationshipPanelMock.mockClear();
  });

  it("renders the project register, current revision, sets, and issues", () => {
    render(<ProjectDrawingsPage {...props()} />);

    expect(
      screen.getByRole("heading", { name: "Drawing Register", level: 1 })
    ).toBeInTheDocument();
    expect(screen.getByRole("table")).toHaveTextContent("A-101");
    expect(screen.getByRole("table")).toHaveTextContent("Current Revision");
    expect(screen.getByRole("table")).toHaveTextContent(
      "A - Architectural"
    );
    expect(screen.getByText(/IFC Release/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Drawings" })).toHaveAttribute(
      "aria-current",
      "page"
    );
  });

  it("opens the exact current revision in the secure viewer", async () => {
    const user = userEvent.setup();
    const pageProps = props();
    render(<ProjectDrawingsPage {...pageProps} />);

    await user.click(
      screen.getByRole("button", { name: "View current revision for A-101" })
    );

    expect(pageProps.onNavigate).toHaveBeenCalledWith("drawingViewer", 1, {
      sheetId: 20,
      revisionId: 30,
    });
  });

  it("mounts one selected drawing-sheet relationship panel", async () => {
    const user = userEvent.setup();
    const pageProps = props();
    render(<ProjectDrawingsPage {...pageProps} />);
    expect(relationshipPanelMock).not.toHaveBeenCalled();

    await user.click(
      screen.getByRole("button", { name: "Relationships for A-101" })
    );
    expect(
      screen.getByRole("heading", { name: "A-101 Relationships" })
    ).toBeInTheDocument();
    expect(relationshipPanelMock).toHaveBeenCalledOnce();
    expect(relationshipPanelMock).toHaveBeenCalledWith(
      expect.objectContaining({
        projectId: 1,
        entityType: "drawing_sheet",
        entityId: 20,
        onNavigate: pageProps.onNavigate,
        onError: pageProps.onRequestError,
      })
    );
    await user.click(
      screen.getByRole("button", { name: "Close relationships for A-101" })
    );
    expect(
      screen.queryByRole("heading", { name: "A-101 Relationships" })
    ).not.toBeInTheDocument();
  });

  it("opens the selected historical revision from revision history", async () => {
    const user = userEvent.setup();
    const pageProps = props();
    render(<ProjectDrawingsPage {...pageProps} />);

    await user.click(
      screen.getByRole("button", { name: "Revision history for A-101" })
    );
    await user.click(
      screen.getByRole("button", { name: "View A-101 revision 0" })
    );

    expect(pageProps.onNavigate).toHaveBeenCalledWith("drawingViewer", 1, {
      sheetId: 20,
      revisionId: 29,
    });
  });

  it("renders loading, empty, and status-specific error states", () => {
    hookState.isLoadingRegister = true;
    hookState.register = null;
    const view = render(<ProjectDrawingsPage {...props()} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading drawing register"
    );

    hookState.isLoadingRegister = false;
    hookState.register = {
      project_id: 1,
      sheets: [],
      pagination: { limit: 50, offset: 0, total: 0, has_more: false },
    };
    view.rerender(<ProjectDrawingsPage {...props()} />);
    expect(screen.getByText("No registered drawing sheets")).toBeInTheDocument();

    hookState.operationError = Object.assign(new Error("Denied"), {
      status: 403,
    });
    view.rerender(<ProjectDrawingsPage {...props()} />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "do not have access"
    );

    hookState.operationError = Object.assign(new Error("Missing"), {
      status: 404,
    });
    view.rerender(<ProjectDrawingsPage {...props()} />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "no longer available"
    );

    hookState.operationError = Object.assign(new Error("Limited"), {
      status: 429,
    });
    view.rerender(<ProjectDrawingsPage {...props()} />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "temporarily limited"
    );
  });

  it("applies search, filters, sorting, and pagination", async () => {
    const user = userEvent.setup();
    hookState.register.pagination = {
      limit: 50,
      offset: 50,
      total: 101,
      has_more: true,
    };
    render(<ProjectDrawingsPage {...props()} />);

    await user.type(screen.getByLabelText("Search drawings"), "floor");
    await user.click(
      screen.getByRole("button", { name: "Search drawing register" })
    );
    expect(hookState.updateQuery).toHaveBeenCalledWith({ search: "floor" });

    await user.selectOptions(screen.getByLabelText("Discipline"), "A");
    await user.selectOptions(screen.getByLabelText("Status"), "active");
    await user.selectOptions(screen.getByLabelText("Sort"), "revision_date:desc");
    expect(hookState.updateQuery).toHaveBeenCalledWith({ discipline: "A" });
    expect(hookState.updateQuery).toHaveBeenCalledWith({
      sheetStatus: "active",
    });
    expect(hookState.updateQuery).toHaveBeenCalledWith({
      sort: "revision_date",
      order: "desc",
    });
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(hookState.updateQuery).toHaveBeenCalledWith({ offset: 100 });
  });

  it("creates and edits sets, then confirms archival", async () => {
    const user = userEvent.setup();
    render(<ProjectDrawingsPage {...props()} />);
    const opener = screen.getByRole("button", { name: "New Set" });
    await user.click(opener);
    expect(screen.getByRole("dialog", { name: "Create Drawing Set" }))
      .toBeInTheDocument();
    await user.type(screen.getByLabelText(/Set name/), "Permit Set");
    await user.click(
      screen.getByRole("button", { name: "Save Drawing Set" })
    );
    expect(hookState.createSet).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Permit Set", status: "active" })
    );
    await waitFor(() => expect(opener).toHaveFocus());

    const setRecord = screen.getAllByText("IFC")[0].closest(
      ".drawing-set-record"
    );
    await user.click(within(setRecord).getByRole("button", { name: "Edit" }));
    expect(screen.getByDisplayValue("IFC")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Close Edit Drawing Set" })
    );
    await user.click(
      within(setRecord).getByRole("button", { name: "Archive" })
    );
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "sheets, revisions, and issued history will be retained"
    );
    await user.click(
      screen.getByRole("button", { name: "Archive Drawing Set" })
    );
    expect(hookState.archiveSet).toHaveBeenCalledWith(10);
  });

  it("validates PDF sheet creation and preserves the controlled metadata", async () => {
    const user = userEvent.setup({ applyAccept: false });
    render(<ProjectDrawingsPage {...props()} />);
    await user.click(screen.getByRole("button", { name: "Add Sheet" }));
    await user.type(screen.getByLabelText(/Sheet number/), "E-401");
    await user.type(screen.getByLabelText(/Title/), "Lighting Plan");
    await user.selectOptions(screen.getByLabelText("Discipline *"), "E");
    const invalid = new File(["bad"], "drawing.svg", {
      type: "image/svg+xml",
    });
    fireEvent.change(screen.getByLabelText(/PDF drawing/), {
      target: { files: [invalid] },
    });
    fireEvent.submit(
      screen.getByRole("dialog", { name: "Add Drawing Sheet" })
        .querySelector("form")
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(".pdf");
    expect(hookState.createSheet).not.toHaveBeenCalled();

    const pdf = new File(["%PDF"], "E-401.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(screen.getByLabelText(/PDF drawing/), {
      target: { files: [pdf] },
    });
    fireEvent.submit(
      screen.getByRole("dialog", { name: "Add Drawing Sheet" })
        .querySelector("form")
    );
    await waitFor(() =>
      expect(hookState.createSheet).toHaveBeenCalledWith(
        10,
        expect.objectContaining({
          sheet_number: "E-401",
          title: "Lighting Plan",
          discipline: "E",
          revision_code: "0",
        }),
        pdf
      )
    );
  });

  it("explains superseding and shows downloadable current and old revisions", async () => {
    const user = userEvent.setup();
    render(<ProjectDrawingsPage {...props()} />);
    await user.click(
      screen.getByRole("button", { name: "Upload revision for A-101" })
    );
    expect(screen.getByRole("dialog")).toHaveTextContent(
      "remain in revision history and become superseded"
    );
    await user.click(
      screen.getByRole("button", { name: "Close Upload Revision - A-101" })
    );

    const historyButton = screen.getByRole("button", {
      name: "Revision history for A-101",
    });
    await user.click(historyButton);
    expect(hookState.loadRevisions).toHaveBeenCalledWith(20);
    const history = screen.getByRole("dialog", {
      name: "Revision History - A-101",
    });
    expect(history).toHaveTextContent("Current Revision");
    expect(history).toHaveTextContent("Superseded");
    await user.click(
      within(history).getByRole("button", {
        name: "Download A-101 revision 0",
      })
    );
    expect(hookState.downloadRevision).toHaveBeenCalledWith(
      SUPERSEDED_REVISION
    );
    fireEvent.keyDown(history, { key: "Escape" });
    expect(historyButton).toHaveFocus();
  });

  it("creates issue membership and requires confirmation before issuing", async () => {
    const user = userEvent.setup();
    const page = props();
    const view = render(<ProjectDrawingsPage {...page} />);
    await user.click(
      screen.getByRole("button", { name: "New Draft Issue" })
    );
    await user.type(screen.getByLabelText(/Issue name/), "Bulletin 01");
    await user.type(screen.getByLabelText(/Issue number/), "B-01");
    await user.click(
      screen.getByRole("button", { name: "Save Draft Issue" })
    );
    expect(hookState.createIssue).toHaveBeenCalledWith(
      10,
      expect.objectContaining({
        name: "Bulletin 01",
        issue_number: "B-01",
      })
    );

    await user.selectOptions(
      screen.getByLabelText("Add current revision"),
      "30"
    );
    await user.click(screen.getByRole("button", { name: "Add" }));
    expect(hookState.addIssueRevision).toHaveBeenCalledWith(50, 30);

    hookState.issues = [
      {
        ...ISSUE,
        revisions: [
          {
            revision_id: 30,
            sheet_id: 20,
            sheet_number: "A-101",
            sheet_title: "Floor Plan",
            revision_code: "1",
            revision_date: "2026-07-30",
            is_current: true,
          },
        ],
      },
    ];
    view.rerender(<ProjectDrawingsPage {...page} />);
    await user.click(
      screen.getAllByRole("button", { name: "Issue Drawings" }).at(-1)
    );
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "includes 1 sheet revisions"
    );
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "freezes membership"
    );
    await user.click(
      within(screen.getByRole("alertdialog")).getByRole("button", {
        name: "Issue Drawings",
      })
    );
    expect(hookState.issueIssue).toHaveBeenCalledWith(50);

    hookState.issues = [
      {
        ...hookState.issues[0],
        status: "issued",
      },
    ];
    view.rerender(<ProjectDrawingsPage {...page} />);
    expect(screen.getByText("Membership frozen")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Void Issue" }));
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "frozen membership will remain available"
    );
    await user.click(
      within(screen.getByRole("alertdialog")).getByRole("button", {
        name: "Void Drawing Issue",
      })
    );
    expect(hookState.voidIssue).toHaveBeenCalledWith(50);
  });

  it("keeps project navigation keyboard-accessible", async () => {
    const user = userEvent.setup();
    const page = props();
    render(<ProjectDrawingsPage {...page} />);

    const documents = screen.getByRole("button", { name: "Documents" });
    documents.focus();
    await user.keyboard("{Enter}");
    expect(page.onNavigate).toHaveBeenCalledWith("projectDocuments");
  });
});
