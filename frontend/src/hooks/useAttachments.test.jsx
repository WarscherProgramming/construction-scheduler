import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import useAttachments from "./useAttachments";


const apiMocks = vi.hoisted(() => ({
  listAttachments: vi.fn(),
  uploadAttachment: vi.fn(),
  downloadAttachment: vi.fn(),
  deleteAttachment: vi.fn(),
}));

vi.mock("../services/api", () => apiMocks);


const DEFAULT_PROPS = {
  projectId: 1,
  parentType: "project",
  parentId: 1,
  enabled: true,
};

const ATTACHMENT = {
  id: 11,
  original_filename: "plans.pdf",
  mime_type: "application/pdf",
  size_bytes: 512,
  created_at: "2026-07-26T12:00:00Z",
};


function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}


async function renderLoadedHook(props = DEFAULT_PROPS) {
  const hook = renderHook(
    (currentProps) => useAttachments(currentProps),
    { initialProps: props }
  );
  await waitFor(() => expect(hook.result.current.isLoading).toBe(false));
  return hook;
}


describe("useAttachments", () => {
  beforeEach(() => {
    apiMocks.listAttachments.mockReset();
    apiMocks.uploadAttachment.mockReset();
    apiMocks.downloadAttachment.mockReset();
    apiMocks.deleteAttachment.mockReset();
    apiMocks.listAttachments.mockResolvedValue({ attachments: [] });
    apiMocks.uploadAttachment.mockResolvedValue({ id: 20 });
    apiMocks.deleteAttachment.mockResolvedValue({
      message: "Attachment deleted",
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("does not request attachments while disabled", async () => {
    const { result } = renderHook(() =>
      useAttachments({ ...DEFAULT_PROPS, enabled: false })
    );

    expect(result.current.attachments).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(apiMocks.listAttachments).not.toHaveBeenCalled();
  });

  it("deduplicates the initial request under Strict Mode", async () => {
    const pending = deferred();
    apiMocks.listAttachments.mockReturnValue(pending.promise);

    const { result } = renderHook(() => useAttachments(DEFAULT_PROPS), {
      wrapper: StrictMode,
    });

    expect(result.current.isLoading).toBe(true);
    await waitFor(() =>
      expect(apiMocks.listAttachments).toHaveBeenCalledTimes(1)
    );
    await act(async () => {
      pending.resolve({ attachments: [] });
      await pending.promise;
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
  });

  it("loads empty and populated attachment responses", async () => {
    apiMocks.listAttachments.mockResolvedValue({
      attachments: [ATTACHMENT],
    });

    const { result } = await renderLoadedHook();

    expect(result.current.attachments).toEqual([ATTACHMENT]);
    expect(apiMocks.listAttachments).toHaveBeenCalledTimes(1);
  });

  it("clears files when project, parent type, or parent ID changes", async () => {
    apiMocks.listAttachments
      .mockResolvedValueOnce({ attachments: [ATTACHMENT] })
      .mockResolvedValue({ attachments: [] });
    const hook = await renderLoadedHook();

    hook.rerender({ ...DEFAULT_PROPS, projectId: 2 });
    expect(hook.result.current.attachments).toEqual([]);
    await waitFor(() => expect(hook.result.current.isLoading).toBe(false));

    hook.rerender({
      ...DEFAULT_PROPS,
      projectId: 2,
      parentType: "rfi",
      parentId: 8,
    });
    expect(hook.result.current.attachments).toEqual([]);
    await waitFor(() => expect(hook.result.current.isLoading).toBe(false));

    hook.rerender({
      ...DEFAULT_PROPS,
      projectId: 2,
      parentType: "rfi",
      parentId: 9,
    });
    expect(hook.result.current.attachments).toEqual([]);
    await waitFor(() => expect(hook.result.current.isLoading).toBe(false));
    expect(apiMocks.listAttachments).toHaveBeenCalledTimes(4);
  });

  it("rejects a stale response from the previous parent", async () => {
    const first = deferred();
    const second = deferred();
    apiMocks.listAttachments
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const hook = renderHook(
      (props) => useAttachments(props),
      { initialProps: DEFAULT_PROPS }
    );

    await waitFor(() =>
      expect(apiMocks.listAttachments).toHaveBeenCalledTimes(1)
    );
    hook.rerender({ ...DEFAULT_PROPS, parentId: 2 });
    await waitFor(() =>
      expect(apiMocks.listAttachments).toHaveBeenCalledTimes(2)
    );
    await act(async () => {
      second.resolve({ attachments: [{ ...ATTACHMENT, id: 22 }] });
      await second.promise;
    });
    await waitFor(() =>
      expect(hook.result.current.attachments[0]?.id).toBe(22)
    );

    await act(async () => {
      first.resolve({ attachments: [ATTACHMENT] });
      await first.promise;
    });
    expect(hook.result.current.attachments[0]?.id).toBe(22);
  });

  it("aborts the previous request when identity changes", async () => {
    const first = deferred();
    apiMocks.listAttachments
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({ attachments: [] });
    const hook = renderHook(
      (props) => useAttachments(props),
      { initialProps: DEFAULT_PROPS }
    );
    await waitFor(() =>
      expect(apiMocks.listAttachments).toHaveBeenCalledTimes(1)
    );
    const firstSignal = apiMocks.listAttachments.mock.calls[0][3].signal;

    hook.rerender({ ...DEFAULT_PROPS, projectId: 2 });

    expect(firstSignal.aborted).toBe(true);
    await waitFor(() => expect(hook.result.current.isLoading).toBe(false));
  });

  it("refreshes on demand without duplicating requests", async () => {
    const { result } = await renderLoadedHook();

    await act(async () => {
      await result.current.refresh();
    });

    expect(apiMocks.listAttachments).toHaveBeenCalledTimes(2);
  });

  it("uploads multiple files sequentially and refreshes once", async () => {
    const order = [];
    apiMocks.uploadAttachment.mockImplementation(async (
      projectId,
      parentType,
      parentId,
      file
    ) => {
      order.push(file.name);
      return { id: order.length };
    });
    const { result } = await renderLoadedHook();
    const files = [
      new File(["one"], "one.pdf", { type: "application/pdf" }),
      new File(["two"], "two.pdf", { type: "application/pdf" }),
    ];

    let uploadResults;
    await act(async () => {
      uploadResults = await result.current.uploadFiles(files);
    });

    expect(order).toEqual(["one.pdf", "two.pdf"]);
    expect(uploadResults.map((item) => item.status)).toEqual([
      "success",
      "success",
    ]);
    expect(apiMocks.listAttachments).toHaveBeenCalledTimes(2);
  });

  it("preserves successful uploads when another file fails", async () => {
    apiMocks.uploadAttachment
      .mockResolvedValueOnce({ id: 1 })
      .mockRejectedValueOnce(new Error("Upload unavailable"));
    const onError = vi.fn();
    const { result } = await renderLoadedHook({
      ...DEFAULT_PROPS,
      onError,
    });
    const files = [
      new File(["one"], "one.pdf"),
      new File(["two"], "two.pdf"),
    ];

    await act(async () => {
      await result.current.uploadFiles(files);
    });

    expect(result.current.uploadResults).toEqual([
      expect.objectContaining({ filename: "one.pdf", status: "success" }),
      expect.objectContaining({ filename: "two.pdf", status: "error" }),
    ]);
    expect(result.current.error).toMatchObject({
      operation: "upload",
      filename: "two.pdf",
    });
    expect(apiMocks.listAttachments).toHaveBeenCalledTimes(2);
    expect(onError).toHaveBeenCalledTimes(1);
  });

  it("rejects invalid files before making an upload request", async () => {
    const { result } = await renderLoadedHook();

    await act(async () => {
      await result.current.uploadFiles([
        new File([], "empty.pdf"),
        { name: "large.pdf", size: 26_214_401 },
        new File(["svg"], "drawing.svg"),
      ]);
    });

    expect(apiMocks.uploadAttachment).not.toHaveBeenCalled();
    expect(result.current.uploadResults).toHaveLength(3);
    expect(
      result.current.uploadResults.every((item) => item.status === "error")
    ).toBe(true);
    expect(apiMocks.listAttachments).toHaveBeenCalledTimes(1);
  });

  it("prevents duplicate upload submission while a batch is active", async () => {
    const pending = deferred();
    apiMocks.uploadAttachment.mockReturnValue(pending.promise);
    const { result } = await renderLoadedHook();
    const file = new File(["one"], "one.pdf");
    let firstPromise;
    let secondPromise;

    act(() => {
      firstPromise = result.current.uploadFiles([file]);
      secondPromise = result.current.uploadFiles([file]);
    });
    expect(firstPromise).toBe(secondPromise);
    expect(apiMocks.uploadAttachment).toHaveBeenCalledTimes(1);

    await act(async () => {
      pending.resolve({ id: 1 });
      await firstPromise;
    });
  });

  it("deletes and refreshes after success", async () => {
    apiMocks.listAttachments
      .mockResolvedValueOnce({ attachments: [ATTACHMENT] })
      .mockResolvedValueOnce({ attachments: [] });
    const { result } = await renderLoadedHook();

    let deleted;
    await act(async () => {
      deleted = await result.current.deleteAttachment(ATTACHMENT);
    });

    expect(deleted).toBe(true);
    expect(apiMocks.deleteAttachment).toHaveBeenCalledWith(
      1,
      11,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(result.current.attachments).toEqual([]);
    expect(apiMocks.listAttachments).toHaveBeenCalledTimes(2);
  });

  it("preserves the file and reports a delete failure", async () => {
    apiMocks.listAttachments.mockResolvedValue({
      attachments: [ATTACHMENT],
    });
    apiMocks.deleteAttachment.mockRejectedValue(
      new Error("Delete unavailable")
    );
    const { result } = await renderLoadedHook();

    await act(async () => {
      await result.current.deleteAttachment(ATTACHMENT);
    });

    expect(result.current.attachments).toEqual([ATTACHMENT]);
    expect(result.current.error).toMatchObject({
      operation: "delete",
      filename: "plans.pdf",
    });
    expect(apiMocks.listAttachments).toHaveBeenCalledTimes(1);
  });

  it("previews an eligible authenticated Blob and revokes its URL", async () => {
    const createObjectURL = vi.fn(() => "blob:preview");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURL,
    });
    vi.spyOn(window, "open").mockReturnValue({});
    apiMocks.downloadAttachment.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      headers: new Headers({
        "Content-Disposition":
          "inline; filename*=UTF-8''Reviewed%20plans.pdf",
      }),
    });
    const { result } = await renderLoadedHook();
    vi.useFakeTimers();

    let outcome;
    await act(async () => {
      outcome = await result.current.downloadAttachment(ATTACHMENT);
    });

    expect(outcome).toEqual({
      filename: "Reviewed plans.pdf",
      mode: "preview",
    });
    expect(window.open).toHaveBeenCalledWith(
      "blob:preview",
      "_blank",
      "noopener,noreferrer"
    );
    expect(revokeObjectURL).not.toHaveBeenCalled();
    act(() => vi.runAllTimers());
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:preview");
  });

  it("downloads Office files and falls back when preview is blocked", async () => {
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:download"),
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    apiMocks.downloadAttachment.mockResolvedValue({
      blob: new Blob(["document"], {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      }),
      headers: new Headers(),
    });
    const { result } = await renderLoadedHook();
    vi.useFakeTimers();

    const officeResult = await act(() =>
      result.current.downloadAttachment({
        ...ATTACHMENT,
        original_filename: "report.docx",
        mime_type:
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      })
    );

    expect(officeResult.mode).toBe("download");
    expect(open).not.toHaveBeenCalled();
    expect(click).toHaveBeenCalledTimes(1);

    apiMocks.downloadAttachment.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      headers: new Headers(),
    });
    const fallbackResult = await act(() =>
      result.current.downloadAttachment(ATTACHMENT)
    );
    expect(fallbackResult.mode).toBe("download");
    expect(open).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(2);
    act(() => vi.runAllTimers());
  });

  it("reports download failures without removing the attachment", async () => {
    apiMocks.listAttachments.mockResolvedValue({
      attachments: [ATTACHMENT],
    });
    apiMocks.downloadAttachment.mockRejectedValue(
      new Error("Download unavailable")
    );
    const { result } = await renderLoadedHook();

    let outcome;
    await act(async () => {
      outcome = await result.current.downloadAttachment(ATTACHMENT);
    });

    expect(outcome).toBeNull();
    expect(result.current.attachments).toEqual([ATTACHMENT]);
    expect(result.current.error.operation).toBe("download");
  });
});
