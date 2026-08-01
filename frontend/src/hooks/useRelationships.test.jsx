import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useRelationships from "./useRelationships";


const apiMocks = vi.hoisted(() => ({
  listRelationships: vi.fn(),
  createRelationship: vi.fn(),
  deleteRelationship: vi.fn(),
}));

vi.mock("../services/api", () => apiMocks);


const DEFAULT_PROPS = {
  projectId: 1,
  entityType: "rfi",
  entityId: 10,
  enabled: true,
};
const RELATIONSHIP = {
  id: 7,
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
    route: { page: "drawingViewer", sheet_id: 20, revision_id: 30 },
  },
};


function response(relationships = [], overrides = {}) {
  return {
    relationships,
    pagination: {
      limit: 50,
      offset: 0,
      total: relationships.length,
      has_more: false,
      ...overrides,
    },
  };
}


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
    (currentProps) => useRelationships(currentProps),
    { initialProps: props }
  );
  await waitFor(() => expect(hook.result.current.isLoading).toBe(false));
  return hook;
}


describe("useRelationships", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listRelationships.mockResolvedValue(response());
    apiMocks.createRelationship.mockResolvedValue(RELATIONSHIP);
    apiMocks.deleteRelationship.mockResolvedValue({
      message: "Relationship deleted",
    });
  });

  it("does not request while disabled", () => {
    const { result } = renderHook(() =>
      useRelationships({ ...DEFAULT_PROPS, enabled: false })
    );
    expect(result.current.relationships).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(apiMocks.listRelationships).not.toHaveBeenCalled();
  });

  it("deduplicates the initial request under Strict Mode", async () => {
    const pending = deferred();
    apiMocks.listRelationships.mockReturnValue(pending.promise);
    const { result } = renderHook(
      () => useRelationships(DEFAULT_PROPS),
      { wrapper: StrictMode }
    );
    await waitFor(() =>
      expect(apiMocks.listRelationships).toHaveBeenCalledTimes(1)
    );
    await act(async () => {
      pending.resolve(response());
      await pending.promise;
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
  });

  it("loads relationship totals and bounded pages", async () => {
    apiMocks.listRelationships.mockResolvedValueOnce(
      response([RELATIONSHIP], { total: 2, has_more: true })
    );
    const hook = await renderLoadedHook();
    expect(hook.result.current.relationships).toEqual([RELATIONSHIP]);
    expect(hook.result.current.total).toBe(2);
    expect(hook.result.current.hasMore).toBe(true);

    apiMocks.listRelationships.mockResolvedValueOnce(
      response([{ ...RELATIONSHIP, id: 8 }], {
        offset: 1,
        total: 2,
      })
    );
    await act(async () => {
      await hook.result.current.loadMore();
    });
    expect(hook.result.current.relationships.map((item) => item.id)).toEqual([
      7,
      8,
    ]);
    expect(apiMocks.listRelationships.mock.calls[1][3]).toEqual(
      expect.objectContaining({ offset: 1, limit: 50 })
    );
  });

  it("clears immediately and rejects a stale entity response", async () => {
    const first = deferred();
    const second = deferred();
    apiMocks.listRelationships
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const hook = renderHook(
      (props) => useRelationships(props),
      { initialProps: DEFAULT_PROPS }
    );
    await waitFor(() =>
      expect(apiMocks.listRelationships).toHaveBeenCalledTimes(1)
    );
    hook.rerender({ ...DEFAULT_PROPS, entityId: 11 });
    expect(hook.result.current.relationships).toEqual([]);
    await waitFor(() =>
      expect(apiMocks.listRelationships).toHaveBeenCalledTimes(2)
    );
    await act(async () => {
      second.resolve(response([{ ...RELATIONSHIP, id: 8 }]));
      await second.promise;
    });
    await waitFor(() =>
      expect(hook.result.current.relationships[0]?.id).toBe(8)
    );
    await act(async () => {
      first.resolve(response([RELATIONSHIP]));
      await first.promise;
    });
    expect(hook.result.current.relationships[0]?.id).toBe(8);
  });

  it("aborts on project switch and unmount", async () => {
    const first = deferred();
    const second = deferred();
    apiMocks.listRelationships
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const hook = renderHook(
      (props) => useRelationships(props),
      { initialProps: DEFAULT_PROPS }
    );
    await waitFor(() =>
      expect(apiMocks.listRelationships).toHaveBeenCalledTimes(1)
    );
    const firstSignal = apiMocks.listRelationships.mock.calls[0][3].signal;
    hook.rerender({ ...DEFAULT_PROPS, projectId: 2 });
    expect(firstSignal.aborted).toBe(true);
    await waitFor(() =>
      expect(apiMocks.listRelationships).toHaveBeenCalledTimes(2)
    );
    const secondSignal = apiMocks.listRelationships.mock.calls[1][3].signal;
    hook.unmount();
    expect(secondSignal.aborted).toBe(true);
  });

  it("reports list failures and retries", async () => {
    const error = new Error("Relationships unavailable");
    const onError = vi.fn();
    apiMocks.listRelationships.mockRejectedValueOnce(error);
    const hook = await renderLoadedHook({ ...DEFAULT_PROPS, onError });
    expect(hook.result.current.error).toMatchObject({
      operation: "list",
      message: error.message,
    });
    expect(onError).toHaveBeenCalledWith(
      "Unable to load relationships",
      error
    );

    apiMocks.listRelationships.mockResolvedValueOnce(response([RELATIONSHIP]));
    await act(async () => {
      await hook.result.current.refresh();
    });
    expect(hook.result.current.relationships).toEqual([RELATIONSHIP]);
    expect(hook.result.current.error).toBe(null);
  });

  it("creates once and refreshes only relationship state", async () => {
    const hook = await renderLoadedHook();
    apiMocks.listRelationships.mockResolvedValueOnce(response([RELATIONSHIP]));
    const payload = {
      source_type: "rfi",
      source_id: 10,
      target_type: "drawing_revision",
      target_id: 30,
      relationship_type: "references",
    };
    let created;
    await act(async () => {
      created = await hook.result.current.createRelationship(payload);
    });
    expect(created).toBe(true);
    expect(apiMocks.createRelationship).toHaveBeenCalledOnce();
    expect(apiMocks.createRelationship).toHaveBeenCalledWith(
      1,
      payload,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(apiMocks.listRelationships).toHaveBeenCalledTimes(2);
    expect(hook.result.current.relationships).toEqual([RELATIONSHIP]);
  });

  it("preserves the list when creation fails", async () => {
    apiMocks.listRelationships.mockResolvedValue(response([RELATIONSHIP]));
    apiMocks.createRelationship.mockRejectedValue(
      Object.assign(new Error("Relationship already exists"), { status: 409 })
    );
    const onError = vi.fn();
    const hook = await renderLoadedHook({ ...DEFAULT_PROPS, onError });
    await act(async () => {
      expect(
        await hook.result.current.createRelationship({})
      ).toBe(false);
    });
    expect(hook.result.current.relationships).toEqual([RELATIONSHIP]);
    expect(hook.result.current.error).toMatchObject({
      operation: "create",
      status: 409,
    });
    expect(onError).toHaveBeenCalledWith(
      "Unable to create relationship",
      expect.any(Error)
    );
  });

  it("deletes and refreshes while preserving data on failure", async () => {
    apiMocks.listRelationships.mockResolvedValue(response([RELATIONSHIP]));
    const hook = await renderLoadedHook();
    apiMocks.listRelationships.mockResolvedValueOnce(response());
    await act(async () => {
      expect(
        await hook.result.current.deleteRelationship(RELATIONSHIP)
      ).toBe(true);
    });
    expect(apiMocks.deleteRelationship).toHaveBeenCalledWith(
      1,
      7,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(hook.result.current.relationships).toEqual([]);

    apiMocks.listRelationships.mockResolvedValueOnce(response([RELATIONSHIP]));
    await act(async () => {
      await hook.result.current.refresh();
    });
    apiMocks.deleteRelationship.mockRejectedValueOnce(
      new Error("Delete unavailable")
    );
    await act(async () => {
      expect(
        await hook.result.current.deleteRelationship(RELATIONSHIP)
      ).toBe(false);
    });
    expect(hook.result.current.relationships).toEqual([RELATIONSHIP]);
    expect(hook.result.current.error.operation).toBe("delete");
  });
});
