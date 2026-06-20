import { describe, expect, it } from "vitest";

import {
  formatPredecessorForApi,
  formatPredecessorForSchedule,
  getScheduleTaskNumber,
} from "./taskReferences";

const tasks = [{ id: 212 }, { id: 318 }, { id: 451 }];

describe("task reference formatting", () => {
  it("uses the task's position as its schedule ID", () => {
    expect(getScheduleTaskNumber(tasks, 212)).toBe(1);
    expect(getScheduleTaskNumber(tasks, 451)).toBe(3);
  });

  it("formats stored predecessor IDs as schedule IDs", () => {
    expect(formatPredecessorForSchedule("318SS+4", tasks)).toBe("2SS+4");
  });

  it("translates schedule predecessor IDs back to stored task IDs", () => {
    expect(formatPredecessorForApi("2ss+4", tasks)).toEqual({
      value: "318SS+4",
      error: null,
    });
  });

  it("rejects schedule IDs outside the current schedule", () => {
    expect(formatPredecessorForApi("4", tasks)).toEqual({
      value: null,
      error: "Predecessor must use a schedule ID between 1 and 3.",
    });
  });
});
