import { useState } from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CreateRelationshipDialog from "./CreateRelationshipDialog";
import RelationshipPanel from "./RelationshipPanel";


const apiMocks = vi.hoisted(() => ({
  listRelationshipCandidates: vi.fn(),
}));
const hookMock = vi.hoisted(() => vi.fn());

vi.mock("../../services/api", () => apiMocks);
vi.mock("../../hooks/useRelationships", () => ({ default: hookMock }));


const BASE_RELATIONSHIP = {
  id: 1,
  project_id: 1,
  relationship_type: "references",
  relationship_label: "References",
  direction: "outgoing",
  created_at: "2026-08-01T12:00:00Z",
  related: {
    type: "drawing_revision",
    id: 30,
    identifier: "A-101 - Rev 1",
    title: "Floor Plan",
    status: "Current",
    available: true,
    route: {
      page: "drawingViewer",
      sheet_id: 20,
      revision_id: 30,
    },
  },
};
const CANDIDATE = {
  type: "drawing_revision",
  id: 30,
  identifier: "A-101 - Rev 1",
  title: "Floor Plan",
  status: "Current",
  available: true,
  route: {
    page: "drawingViewer",
    sheet_id: 20,
    revision_id: 30,
  },
};

let hookState;


function panelProps(overrides = {}) {
  return {
    projectId: 1,
    entityType: "rfi",
    entityId: 10,
    title: "RFI Relationships",
    onNavigate: vi.fn(),
    onError: vi.fn(),
    ...overrides,
  };
}


function dialogProps(overrides = {}) {
  return {
    projectId: 1,
    entityType: "rfi",
    entityId: 10,
    relationships: [],
    isCreating: false,
    mutationError: null,
    onCreate: vi.fn().mockResolvedValue(true),
    onClose: vi.fn(),
    onError: vi.fn(),
    ...overrides,
  };
}


describe("RelationshipPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hookState = {
      relationships: [],
      total: 0,
      hasMore: false,
      isLoading: false,
      isCreating: false,
      deletingIds: [],
      error: null,
      refresh: vi.fn(),
      loadMore: vi.fn(),
      createRelationship: vi.fn().mockResolvedValue(true),
      deleteRelationship: vi.fn().mockResolvedValue(true),
      clearError: vi.fn(),
    };
    hookMock.mockImplementation(() => hookState);
    apiMocks.listRelationshipCandidates.mockResolvedValue({
      candidates: [CANDIDATE],
      has_more: false,
    });
  });

  it("renders loading and factual empty states with a count", () => {
    hookState.isLoading = true;
    const view = render(<RelationshipPanel {...panelProps()} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading relationships"
    );
    hookState.isLoading = false;
    view.rerender(<RelationshipPanel {...panelProps()} />);
    expect(screen.getByText("No relationships yet.")).toBeInTheDocument();
    expect(screen.getByLabelText("Relationship count: 0")).toBeInTheDocument();
  });

  it("renders incoming, outgoing, symmetric, archived, and unavailable text", () => {
    hookState.relationships = [
      BASE_RELATIONSHIP,
      {
        ...BASE_RELATIONSHIP,
        id: 2,
        relationship_label: "Referenced by",
        direction: "incoming",
        related: {
          ...BASE_RELATIONSHIP.related,
          type: "rfi",
          id: 11,
          identifier: "RFI-011",
          status: "Open",
          route: { page: "rfis" },
        },
      },
      {
        ...BASE_RELATIONSHIP,
        id: 3,
        relationship_type: "associated_with",
        relationship_label: "Associated with",
        direction: "symmetric",
        related: {
          ...BASE_RELATIONSHIP.related,
          type: "drawing_sheet",
          id: 20,
          identifier: "A-101",
          status: "Archived",
          route: { page: "projectDrawings" },
        },
      },
      {
        ...BASE_RELATIONSHIP,
        id: 4,
        related: {
          type: "document",
          id: 44,
          identifier: "Related record unavailable",
          title: "Document",
          status: "Unavailable",
          available: false,
          route: null,
        },
      },
    ];
    hookState.total = 4;
    render(<RelationshipPanel {...panelProps()} />);
    const list = screen.getByRole("list", {
      name: "RFI Relationships list",
    });
    expect(within(list).getAllByText("References")).toHaveLength(2);
    expect(within(list).getByText("Referenced by")).toBeInTheDocument();
    expect(within(list).getByText("Associated with")).toBeInTheDocument();
    expect(within(list).getByText("Status: Archived")).toBeInTheDocument();
    expect(within(list).getByText("Record unavailable")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Open Document Related record unavailable",
      })
    ).not.toBeInTheDocument();
  });

  it("navigates to the exact drawing revision route", async () => {
    const user = userEvent.setup();
    hookState.relationships = [BASE_RELATIONSHIP];
    hookState.total = 1;
    const props = panelProps();
    render(<RelationshipPanel {...props} />);
    await user.click(
      screen.getByRole("button", {
        name: "Open Drawing Revision A-101 - Rev 1",
      })
    );
    expect(props.onNavigate).toHaveBeenCalledWith("drawingViewer", 1, {
      sheetId: 20,
      revisionId: 30,
    });
  });

  it("confirms removal without changing the related record", async () => {
    const user = userEvent.setup();
    hookState.relationships = [BASE_RELATIONSHIP];
    hookState.total = 1;
    render(<RelationshipPanel {...panelProps()} />);
    await user.click(
      screen.getByRole("button", {
        name: "Remove relationship to Drawing Revision A-101 - Rev 1",
      })
    );
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveTextContent("The related record will remain unchanged");
    await user.click(
      within(dialog).getByRole("button", { name: "Remove Relationship" })
    );
    expect(hookState.deleteRelationship).toHaveBeenCalledWith(
      BASE_RELATIONSHIP
    );
  });

  it("shows retry and mutation errors without hiding existing links", async () => {
    const user = userEvent.setup();
    hookState.relationships = [BASE_RELATIONSHIP];
    hookState.total = 1;
    hookState.error = {
      operation: "list",
      message: "Relationships unavailable",
    };
    const view = render(<RelationshipPanel {...panelProps()} />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Relationships unavailable"
    );
    expect(screen.getByText("A-101 - Rev 1")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(hookState.refresh).toHaveBeenCalledOnce();

    hookState.error = { operation: "delete", message: "Remove failed" };
    view.rerender(<RelationshipPanel {...panelProps()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Remove failed");
  });
});


describe("CreateRelationshipDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listRelationshipCandidates.mockResolvedValue({
      candidates: [CANDIDATE],
      has_more: false,
    });
  });

  it("searches allowed candidates and confirms a forward relationship", async () => {
    const user = userEvent.setup();
    const props = dialogProps();
    render(<CreateRelationshipDialog {...props} />);

    await user.selectOptions(
      screen.getByLabelText("Relationship *"),
      "references:outgoing"
    );
    expect(screen.getByLabelText("Record type *")).toHaveTextContent(
      "Drawing Revision"
    );
    await user.selectOptions(
      screen.getByLabelText("Record type *"),
      "drawing_revision"
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Searching project records"
    );
    await waitFor(() =>
      expect(apiMocks.listRelationshipCandidates).toHaveBeenCalledWith(
        1,
        "drawing_revision",
        expect.objectContaining({ limit: 20, signal: expect.any(AbortSignal) })
      )
    );
    await user.click(
      await screen.findByRole("option", { name: /A-101 - Rev 1/ })
    );
    expect(screen.getByText("Relationship summary")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Add Relationship" })
    );
    expect(props.onCreate).toHaveBeenCalledWith({
      source_type: "rfi",
      source_id: 10,
      target_type: "drawing_revision",
      target_id: 30,
      relationship_type: "references",
    });
    expect(props.onClose).toHaveBeenCalledOnce();
  });

  it("creates reverse-facing links in backend direction", async () => {
    const user = userEvent.setup();
    apiMocks.listRelationshipCandidates.mockResolvedValue({
      candidates: [
        {
          ...CANDIDATE,
          type: "rfi",
          id: 10,
          identifier: "RFI-010",
          title: "Clarify detail",
          route: { page: "rfis" },
        },
      ],
      has_more: false,
    });
    const props = dialogProps({
      entityType: "drawing_revision",
      entityId: 30,
    });
    render(<CreateRelationshipDialog {...props} />);
    await user.selectOptions(
      screen.getByLabelText("Relationship *"),
      "references:incoming"
    );
    await user.selectOptions(screen.getByLabelText("Record type *"), "rfi");
    await user.click(
      await screen.findByRole("option", { name: /RFI-010/ })
    );
    await user.click(
      screen.getByRole("button", { name: "Add Relationship" })
    );
    expect(props.onCreate).toHaveBeenCalledWith({
      source_type: "rfi",
      source_id: 10,
      target_type: "drawing_revision",
      target_id: 30,
      relationship_type: "references",
    });
  });

  it("filters existing links and reports candidate failures with retry", async () => {
    const user = userEvent.setup();
    apiMocks.listRelationshipCandidates
      .mockResolvedValueOnce({ candidates: [CANDIDATE], has_more: false })
      .mockRejectedValueOnce(new Error("Search unavailable"))
      .mockResolvedValueOnce({ candidates: [], has_more: false });
    const props = dialogProps({ relationships: [BASE_RELATIONSHIP] });
    render(<CreateRelationshipDialog {...props} />);
    await user.selectOptions(
      screen.getByLabelText("Relationship *"),
      "references:outgoing"
    );
    await user.selectOptions(
      screen.getByLabelText("Record type *"),
      "drawing_revision"
    );
    expect(await screen.findByText("No available records found.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Find record"), "roof");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Search unavailable"
    );
    expect(props.onError).toHaveBeenCalledWith(
      "Unable to search relationship candidates",
      expect.any(Error)
    );
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() =>
      expect(apiMocks.listRelationshipCandidates).toHaveBeenCalledTimes(3)
    );
  });

  it("supports keyboard listbox selection and duplicate conflict feedback", async () => {
    const user = userEvent.setup();
    render(
      <CreateRelationshipDialog
        {...dialogProps({
          mutationError: {
            operation: "create",
            status: 409,
            message: "Relationship already exists",
          },
        })}
      />
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "That relationship already exists"
    );
    await user.selectOptions(
      screen.getByLabelText("Relationship *"),
      "references:outgoing"
    );
    await user.selectOptions(
      screen.getByLabelText("Record type *"),
      "drawing_revision"
    );
    const search = screen.getByLabelText("Find record");
    const listbox = screen.getByRole("listbox", {
      name: "Related project records",
    });
    await waitFor(() =>
      expect(within(listbox).getAllByRole("option")).toHaveLength(1)
    );
    search.focus();
    await user.keyboard("{ArrowDown}{Enter}");
    expect(screen.getByText("Relationship summary")).toBeInTheDocument();
  });

  it("traps focus and restores it after Escape", async () => {
    const user = userEvent.setup();

    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            Open dialog
          </button>
          {open && (
            <CreateRelationshipDialog
              {...dialogProps({ onClose: () => setOpen(false) })}
            />
          )}
        </>
      );
    }

    render(<Harness />);
    const opener = screen.getByRole("button", { name: "Open dialog" });
    await user.click(opener);
    const close = screen.getByRole("button", {
      name: "Close Add relationship",
    });
    expect(close).toHaveFocus();
    fireEvent.keyDown(close, { key: "Tab", shiftKey: true });
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });
});
