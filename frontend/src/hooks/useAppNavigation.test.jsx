import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import useAppNavigation from "./useAppNavigation";


describe("useAppNavigation drawing viewer routes", () => {
  beforeEach(() => window.history.replaceState({}, "", "#/"));

  it("navigates to a viewer and responds to browser history events", () => {
    const { result } = renderHook(() => useAppNavigation());

    act(() => {
      result.current.navigateTo("drawingViewer", 4, {
        sheetId: 10,
        revisionId: 12,
      });
    });
    expect(result.current.currentPage).toBe("drawingViewer");
    expect(result.current.routeParams).toEqual({ sheetId: 10, revisionId: 12 });

    act(() => {
      window.history.pushState({}, "", "#/projects/4/drawings");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(result.current.currentPage).toBe("projectDrawings");
    expect(result.current.routeParams).toEqual({ sheetId: null, revisionId: null });
  });
});
