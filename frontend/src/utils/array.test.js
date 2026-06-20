import { describe, expect, it } from "vitest";

import { moveArrayItem } from "./array";


describe("moveArrayItem", () => {
  it("moves an item without mutating the original array", () => {
    const original = ["a", "b", "c"];

    expect(moveArrayItem(original, 0, 2)).toEqual(["b", "c", "a"]);
    expect(original).toEqual(["a", "b", "c"]);
  });
});
