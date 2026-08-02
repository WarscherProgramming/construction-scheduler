import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProjectDocumentSearchPage from "./ProjectDocumentSearchPage";


const useDocumentSearchMock = vi.hoisted(() => vi.fn());
vi.mock("../hooks/useDocumentSearch", () => ({
  default: useDocumentSearchMock,
}));


const RESULT = {
  result_type: "document",
  document_id: 8,
  drawing_revision_id: null,
  drawing_sheet_id: null,
  drawing_set_id: null,
  display_name: "Unsafe <script> Exhibit",
  document_type: "Specification",
  sheet_number: null,
  sheet_title: null,
  discipline: null,
  revision_code: null,
  revision_status: null,
  page_number: 3,
  snippet: "Angle <script> & formula =SUM(A1:A2)",
  match_ranges: [{ start: 6, end: 14 }],
  rank: 1.25,
  extraction_method: "embedded_text",
  updated_at: "2026-08-01T12:00:00Z",
  route_target: { type: "document", document_id: 8 },
};

let searchState;


function props(overrides = {}) {
  return {
    projectId: 4,
    projectName: "Riverside",
    onNavigate: vi.fn(),
    onLogout: vi.fn(),
    onRequestError: vi.fn(),
    ...overrides,
  };
}


describe("ProjectDocumentSearchPage", () => {
  beforeEach(() => {
    searchState = {
      data: null,
      error: null,
      isLoading: false,
      submit: vi.fn(),
      goToOffset: vi.fn(),
      retry: vi.fn(),
      clear: vi.fn(),
    };
    useDocumentSearchMock.mockReset();
    useDocumentSearchMock.mockImplementation(() => searchState);
  });

  it("renders one h1 and makes no request before submit", () => {
    render(<ProjectDocumentSearchPage {...props()} />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(
      screen.getByRole("heading", { name: "Document Search" })
    ).toBeInTheDocument();
    expect(screen.getByText("No search submitted")).toBeInTheDocument();
    expect(searchState.submit).not.toHaveBeenCalled();
  });

  it("validates empty input and submits explicit filters", async () => {
    const user = userEvent.setup();
    render(<ProjectDocumentSearchPage {...props()} />);
    await user.click(screen.getByRole("button", { name: "Search" }));
    expect(screen.getByRole("alert")).toHaveTextContent("required");
    expect(searchState.submit).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("Document content"), "  AHU-7  ");
    await user.selectOptions(screen.getByLabelText("Scope"), "drawings");
    await user.selectOptions(screen.getByLabelText("Discipline"), "M");
    await user.type(screen.getByLabelText("Drawing set ID"), "12");
    await user.selectOptions(
      screen.getByLabelText("Text source"),
      "embedded_text"
    );
    await user.click(
      screen.getByLabelText("Current drawing revisions only")
    );
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(searchState.submit).toHaveBeenCalledWith(
      "AHU-7",
      expect.objectContaining({
        scope: "drawings",
        discipline: "M",
        drawingSetId: "12",
        extractionMethod: "embedded_text",
        currentRevisionsOnly: false,
      })
    );
  });

  it("renders unsafe snippets as text with accessible match emphasis", () => {
    searchState.data = {
      project_id: 4,
      query: "script",
      scope: "all",
      results: [RESULT],
      pagination: { limit: 20, offset: 0, total: 1, has_more: false },
    };
    render(<ProjectDocumentSearchPage {...props()} />);

    expect(screen.getByText("<script>", { selector: "mark" })).toBeInTheDocument();
    expect(screen.queryByText("alert(1)")).not.toBeInTheDocument();
    const open = screen.getByRole("button", { name: /Open Unsafe/ });
    const result = open.closest("article");
    expect(within(result).getByText("Embedded PDF text")).toBeInTheDocument();
    expect(within(result).getByText("3")).toBeInTheDocument();
    expect(open).toBeEnabled();
  });

  it("navigates documents and exact drawing revisions", async () => {
    const user = userEvent.setup();
    const pageProps = props();
    const drawing = {
      ...RESULT,
      result_type: "drawing_revision",
      document_id: 9,
      drawing_sheet_id: 20,
      drawing_revision_id: 30,
      sheet_number: "A-101",
      sheet_title: "Floor Plan",
      revision_code: "1",
      revision_status: "current",
      route_target: {
        type: "drawing_revision",
        document_id: 9,
        drawing_sheet_id: 20,
        drawing_revision_id: 30,
      },
    };
    searchState.data = {
      project_id: 4,
      query: "plan",
      scope: "all",
      results: [RESULT, drawing],
      pagination: { limit: 20, offset: 0, total: 2, has_more: false },
    };
    render(<ProjectDocumentSearchPage {...pageProps} />);
    await user.click(screen.getByRole("button", { name: /Open Unsafe/ }));
    await user.click(screen.getByRole("button", { name: "Open A-101 - Floor Plan" }));
    expect(pageProps.onNavigate).toHaveBeenNthCalledWith(
      1,
      "projectDocuments",
      4,
      undefined
    );
    expect(pageProps.onNavigate).toHaveBeenNthCalledWith(
      2,
      "drawingViewer",
      4,
      { sheetId: 20, revisionId: 30 }
    );
  });

  it("shows loading, no-results, errors, retry, and pagination", async () => {
    const user = userEvent.setup();
    searchState.isLoading = true;
    const view = render(<ProjectDocumentSearchPage {...props()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Searching");

    searchState.isLoading = false;
    searchState.data = {
      project_id: 4,
      query: "missing",
      scope: "all",
      results: [],
      pagination: { limit: 20, offset: 0, total: 0, has_more: false },
    };
    view.rerender(<ProjectDocumentSearchPage {...props()} />);
    expect(screen.getByText("No matching documents")).toBeInTheDocument();

    searchState.data = null;
    searchState.error = Object.assign(new Error("Too many requests"), {
      status: 429,
    });
    view.rerender(<ProjectDocumentSearchPage {...props()} />);
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(searchState.retry).toHaveBeenCalledOnce();

    searchState.error = null;
    searchState.data = {
      project_id: 4,
      query: "plan",
      scope: "all",
      results: [RESULT],
      pagination: { limit: 20, offset: 20, total: 41, has_more: true },
    };
    view.rerender(<ProjectDocumentSearchPage {...props()} />);
    await waitFor(() =>
      expect(screen.getByText("21-21 of 41")).toBeInTheDocument()
    );
    await user.click(screen.getByRole("button", { name: "Previous" }));
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(searchState.goToOffset).toHaveBeenNthCalledWith(1, 0);
    expect(searchState.goToOffset).toHaveBeenNthCalledWith(2, 40);
  });
});
