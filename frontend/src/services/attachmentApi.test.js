import { afterEach, describe, expect, it, vi } from "vitest";

import {
  deleteAttachment,
  downloadAttachment,
  listAttachments,
  uploadAttachment,
} from "./api";
import { configureAuthentication } from "./httpClient";


function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}


describe("attachment API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    configureAuthentication({ token: null, onUnauthorized: null });
  });

  it("encodes the parent query and forwards authentication and signal", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ attachments: [] })
    );
    const controller = new AbortController();
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "token-123", onUnauthorized: null });

    await listAttachments(12, "change_order", 44, {
      signal: controller.signal,
    });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain(
      "/projects/12/attachments?parent_type=change_order&parent_id=44"
    );
    expect(options.headers.Authorization).toBe("Bearer token-123");
    expect(options.signal).toBe(controller.signal);
  });

  it("uploads multipart data without forcing a Content-Type boundary", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1 }, 201));
    const file = new File(["plans"], "plans.pdf", {
      type: "application/pdf",
    });
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "token-123", onUnauthorized: null });

    await uploadAttachment(3, "rfi", 9, file);

    const [, options] = fetchMock.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(options.headers.Authorization).toBe("Bearer token-123");
    expect(options.headers["Content-Type"]).toBeUndefined();
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get("parent_type")).toBe("rfi");
    expect(options.body.get("parent_id")).toBe("9");
    expect(options.body.get("file")).toBe(file);
  });

  it("returns a binary download with its response headers", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("binary", {
          headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'inline; filename="plans.pdf"',
          },
        })
      )
    );
    configureAuthentication({ token: "token-123", onUnauthorized: null });

    const result = await downloadAttachment(4, 15);

    expect(await result.blob.text()).toBe("binary");
    expect(result.headers.get("content-disposition")).toContain("plans.pdf");
  });

  it("sends an authenticated delete request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ message: "Attachment deleted" })
    );
    vi.stubGlobal("fetch", fetchMock);
    configureAuthentication({ token: "token-123", onUnauthorized: null });

    await deleteAttachment(7, 22);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/7/attachments/22"),
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
      })
    );
  });

  it("preserves normalized API errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: "Attachment parent not found" }, 404)
      )
    );

    await expect(
      listAttachments(1, "project", 1)
    ).rejects.toMatchObject({
      status: 404,
      message: "Attachment parent not found",
    });
  });

  it("preserves AbortError instead of converting cancellation to an API error", async () => {
    const abortError = new DOMException("Aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortError));

    await expect(
      downloadAttachment(1, 2, {
        signal: new AbortController().signal,
      })
    ).rejects.toBe(abortError);
  });
});
