import { describe, expect, it } from "vitest";

import {
  buildWbsMap,
  formatPredecessorForApi,
  formatPredecessorForSchedule,
  getScheduleTaskNumber,
} from "./taskReferences";

const flatTasks = [{ id: 212 }, { id: 318 }, { id: 451 }];

const hierarchyTasks = [
  { id: 10, parent_task_id: null },
  { id: 11, parent_task_id: 10 },
  { id: 12, parent_task_id: 10 },
  { id: 13, parent_task_id: 12 },
  { id: 20, parent_task_id: null },
  { id: 21, parent_task_id: 20 },
];

describe("buildWbsMap", () => {
  it("numbers roots sequentially and children hierarchically", () => {
    const wbs = buildWbsMap(hierarchyTasks);

    expect(wbs.get(10)).toBe("1");
    expect(wbs.get(11)).toBe("1.1");
    expect(wbs.get(12)).toBe("1.2");
    expect(wbs.get(13)).toBe("1.2.1");
    expect(wbs.get(20)).toBe("2");
    expect(wbs.get(21)).toBe("2.1");
  });

  it("treats flat lists as sequential root numbering", () => {
    const wbs = buildWbsMap(flatTasks);

    expect(wbs.get(212)).toBe("1");
    expect(wbs.get(451)).toBe("3");
  });
});

describe("task reference formatting", () => {
  it("uses the task's WBS number as its schedule ID", () => {
    expect(getScheduleTaskNumber(flatTasks, 212)).toBe("1");
    expect(getScheduleTaskNumber(hierarchyTasks, 13)).toBe("1.2.1");
    expect(getScheduleTaskNumber(hierarchyTasks, 999)).toBeNull();
  });

  it("formats stored predecessor IDs as WBS schedule IDs", () => {
    expect(formatPredecessorForSchedule("318SS+4", flatTasks)).toBe("2SS+4");
    expect(formatPredecessorForSchedule("12+3", hierarchyTasks)).toBe("1.2+3");
  });

  it("translates WBS schedule IDs back to stored task IDs", () => {
    expect(formatPredecessorForApi("2ss+4", flatTasks)).toEqual({
      value: "318SS+4",
      error: null,
    });
    expect(formatPredecessorForApi("1.2.1+2", hierarchyTasks)).toEqual({
      value: "13+2",
      error: null,
    });
  });

  it("rejects malformed references with format guidance", () => {
    expect(formatPredecessorForApi("abc", flatTasks).error).toBe(
      "Use a schedule ID such as 2, 1.2, 2+3, or 1.2SS+4."
    );
  });

  it("rejects schedule IDs that do not exist", () => {
    expect(formatPredecessorForApi("4", flatTasks)).toEqual({
      value: null,
      error: "No task has schedule ID 4. Use the ID shown in the first column.",
    });
    expect(formatPredecessorForApi("1.7", hierarchyTasks).error).toBe(
      "No task has schedule ID 1.7. Use the ID shown in the first column."
    );
  });
});
