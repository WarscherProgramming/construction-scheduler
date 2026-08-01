import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PdfCanvasViewport from "./PdfCanvasViewport";


const createTextLayerMock = vi.hoisted(() => vi.fn());
vi.mock("../../../utils/pdfViewer", () => ({
  PDF_ANNOTATION_MODE_DISABLED: 0,
  createPdfTextLayer: createTextLayerMock,
}));


function viewport(scale) {
  return {
    width: 600 * scale,
    height: 800 * scale,
    scale,
    rotation: 0,
    rawDims: { pageWidth: 600, pageHeight: 800, pageX: 0, pageY: 0 },
  };
}


describe("PdfCanvasViewport", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("ResizeObserver", class {
      observe() {}
      disconnect() {}
    });
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      callback();
      return 1;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({});
    createTextLayerMock.mockReturnValue({
      render: vi.fn().mockResolvedValue(undefined),
      cancel: vi.fn(),
    });
  });

  it("renders one canvas page and a selectable text layer", async () => {
    const renderTask = { promise: Promise.resolve(), cancel: vi.fn() };
    const page = {
      getViewport: vi.fn(({ scale }) => viewport(scale)),
      render: vi.fn(() => renderTask),
      getTextContent: vi.fn().mockResolvedValue({
        items: [{ str: "Floor plan" }],
        styles: {},
      }),
    };
    const pdfDocument = { getPage: vi.fn().mockResolvedValue(page) };
    const onRenderStateChange = vi.fn();
    const view = render(
      <PdfCanvasViewport
        pdfDocument={pdfDocument}
        pageNumber={1}
        zoomMode="fit-width"
        zoomPercent={100}
        sheetLabel="A-101 Floor Plan"
        onRenderStateChange={onRenderStateChange}
      />
    );

    await waitFor(() => expect(onRenderStateChange).toHaveBeenCalledWith("ready"));
    expect(screen.getByLabelText("A-101 Floor Plan, PDF page 1")).toBeInTheDocument();
    expect(page.render).toHaveBeenCalledWith(
      expect.objectContaining({
        canvas: expect.any(HTMLCanvasElement),
        annotationMode: 0,
      })
    );
    expect(createTextLayerMock).toHaveBeenCalledWith(
      expect.objectContaining({ textContentSource: expect.any(Object) })
    );

    view.unmount();
    expect(renderTask.cancel).toHaveBeenCalled();
  });

  it("keeps the viewer shell available when a page render fails and retries", async () => {
    const page = {
      getViewport: vi.fn(({ scale }) => viewport(scale)),
      render: vi.fn(() => ({
        promise: Promise.reject(new Error("Canvas memory pressure")),
        cancel: vi.fn(),
      })),
    };
    const pdfDocument = { getPage: vi.fn().mockResolvedValue(page) };
    render(
      <PdfCanvasViewport
        pdfDocument={pdfDocument}
        pageNumber={1}
        zoomMode="percent"
        zoomPercent={100}
        sheetLabel="A-101 Floor Plan"
      />
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This page could not be rendered"
    );
    await userEvent.click(screen.getByRole("button", { name: "Retry Page" }));
    await waitFor(() => expect(pdfDocument.getPage.mock.calls.length).toBeGreaterThan(1));
  });
});
