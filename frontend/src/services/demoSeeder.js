import {
  createChangeOrder,
  createDailyLog,
  createInspection,
  createNoteDelay,
  createProject,
  createProjectCompany,
  createTask,
} from "./api";
import { buildDemoProject } from "../data/demoProject";

/**
 * Seed a realistic demo project using only the existing create APIs.
 *
 * Records are created sequentially so a caller can render deterministic
 * progress. `onProgress` receives `{ step, total, label }` after each record.
 * Returns the created project (with its server-assigned id).
 *
 * No backend or API changes — this composes the same endpoints the app already
 * uses when a user builds a project by hand.
 */
export async function seedDemoProject({ referenceDate, onProgress } = {}) {
  const blueprint = buildDemoProject(referenceDate);

  const total =
    1 +
    blueprint.companies.length +
    blueprint.tasks.length +
    blueprint.dailyLogs.length +
    blueprint.inspections.length +
    blueprint.notesDelays.length +
    blueprint.changeOrders.length;

  let step = 0;
  const advance = (label) => {
    step += 1;
    onProgress?.({ step, total, label });
  };

  const project = await createProject(blueprint.project);
  advance("Creating the project");

  for (const company of blueprint.companies) {
    await createProjectCompany(project.id, company);
    advance("Adding project companies");
  }

  for (const task of blueprint.tasks) {
    await createTask(project.id, task);
    advance("Building the schedule");
  }

  for (const log of blueprint.dailyLogs) {
    await createDailyLog(project.id, log);
    advance("Recording daily logs");
  }

  for (const inspection of blueprint.inspections) {
    await createInspection(project.id, inspection);
    advance("Scheduling inspections");
  }

  for (const entry of blueprint.notesDelays) {
    await createNoteDelay(project.id, entry);
    advance("Logging notes & delays");
  }

  for (const changeOrder of blueprint.changeOrders) {
    await createChangeOrder(project.id, changeOrder);
    advance("Adding change orders");
  }

  return project;
}
