import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  createProject: vi.fn(),
  createProjectCompany: vi.fn(),
  createTask: vi.fn(),
  createDailyLog: vi.fn(),
  createInspection: vi.fn(),
  createNoteDelay: vi.fn(),
  createChangeOrder: vi.fn(),
}));

import {
  createChangeOrder,
  createDailyLog,
  createInspection,
  createNoteDelay,
  createProject,
  createProjectCompany,
  createTask,
} from "./api";
import { seedDemoProject } from "./demoSeeder";

const REFERENCE = new Date("2026-06-30T12:00:00");
const PROJECT = { id: 42, name: "Riverside Medical Center — Phase 2" };

describe("seedDemoProject", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createProject.mockResolvedValue(PROJECT);
    createProjectCompany.mockResolvedValue({});
    createTask.mockResolvedValue({ tasks: [] });
    createDailyLog.mockResolvedValue({});
    createInspection.mockResolvedValue({});
    createNoteDelay.mockResolvedValue({});
    createChangeOrder.mockResolvedValue({});
  });

  it("seeds every record against the new project id and reports progress", async () => {
    const onProgress = vi.fn();

    const project = await seedDemoProject({
      referenceDate: REFERENCE,
      onProgress,
    });

    expect(project).toEqual(PROJECT);
    expect(createProject).toHaveBeenCalledOnce();
    expect(createProjectCompany).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ name: expect.any(String) })
    );
    expect(createTask).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ manual_start_date: expect.any(String) })
    );
    expect(createChangeOrder).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ co_number: expect.any(String) })
    );

    const total =
      1 +
      createProjectCompany.mock.calls.length +
      createTask.mock.calls.length +
      createDailyLog.mock.calls.length +
      createInspection.mock.calls.length +
      createNoteDelay.mock.calls.length +
      createChangeOrder.mock.calls.length;

    expect(onProgress).toHaveBeenCalledTimes(total);
    const lastProgress = onProgress.mock.calls.at(-1)[0];
    expect(lastProgress).toEqual({
      step: total,
      total,
      label: expect.any(String),
    });
  });

  it("propagates an error if a record fails to create", async () => {
    createTask.mockRejectedValueOnce(new Error("boom"));

    await expect(
      seedDemoProject({ referenceDate: REFERENCE })
    ).rejects.toThrow("boom");
  });
});
