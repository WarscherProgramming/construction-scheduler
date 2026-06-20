import { describe, expect, it } from "vitest";

import { findIndentParent, getTaskDepthFromList } from "./taskHierarchy";

describe("task hierarchy", () => {
  it("finds task depth from immutable parent IDs", () => {
    const tasks = [
      { id: 1, parent_task_id: null },
      { id: 2, parent_task_id: 1 },
      { id: 3, parent_task_id: 2 },
    ];

    expect(getTaskDepthFromList(tasks, tasks[2])).toBe(2);
  });

  it("makes consecutive top-level indents siblings", () => {
    const tasks = [
      { id: 1, parent_task_id: null },
      { id: 2, parent_task_id: 1 },
      { id: 3, parent_task_id: null },
    ];

    expect(findIndentParent(tasks, 3)).toEqual(tasks[0]);
  });

  it("allows a child to indent under a preceding sibling", () => {
    const tasks = [
      { id: 1, parent_task_id: null },
      { id: 2, parent_task_id: 1 },
      { id: 3, parent_task_id: 1 },
    ];

    expect(findIndentParent(tasks, 3)).toEqual(tasks[1]);
  });

  it("does not cross into a previous hierarchy branch", () => {
    const tasks = [
      { id: 1, parent_task_id: null },
      { id: 2, parent_task_id: 1 },
      { id: 3, parent_task_id: null },
      { id: 4, parent_task_id: 3 },
    ];

    expect(findIndentParent(tasks, 4)).toBeNull();
  });
});
