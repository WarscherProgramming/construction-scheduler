import { toLocalDateInputValue } from "../utils/date";

export const DEMO_PROJECT_NAME = "Riverside Medical Center — Phase 2";

const COMPANIES = [
  { name: "Summit Builders", trade: "General Contractor" },
  { name: "Desert Concrete", trade: "Concrete" },
  { name: "Ironclad Steel", trade: "Structural Steel" },
  { name: "Valley Electric", trade: "Electrical" },
  { name: "ProMech HVAC", trade: "Mechanical" },
  { name: "ClearView Glazing", trade: "Glazing & Envelope" },
];

// Sequential schedule. Each task starts when the previous one ends, anchored a
// few weeks before "today" so the timeline spans completed, in-progress, and
// upcoming work.
const TASK_PLAN = [
  { name: "Mobilization & Site Setup", duration: 3 },
  { name: "Site Grading & Underground Utilities", duration: 8 },
  { name: "Underground Plumbing", duration: 5 },
  { name: "Footings & Foundations", duration: 7 },
  { name: "Foundation Walls & Waterproofing", duration: 6 },
  { name: "Structural Steel Erection", duration: 10 },
  { name: "Roof Deck & Membrane", duration: 6 },
  { name: "Exterior Framing & Sheathing", duration: 8 },
  { name: "Building Envelope & Glazing", duration: 9 },
  { name: "Electrical Rough-In", duration: 10 },
  { name: "Plumbing Rough-In", duration: 8 },
  { name: "HVAC Rough-In", duration: 11 },
  { name: "Drywall & Interior Finishes", duration: 15 },
  { name: "Fire & Life-Safety Systems", duration: 6 },
  { name: "Final Inspections & Punch List", duration: 7 },
];

const DAILY_LOGS = [
  {
    dayOffset: -1,
    company: "Desert Concrete",
    manpower: 8,
    notes:
      "Formed and poured foundation walls on grids A–C. Stripped forms on the east footings.",
  },
  {
    dayOffset: -2,
    company: "Ironclad Steel",
    manpower: 6,
    notes:
      "Set columns and beams for the west bay. Crane remains on site through Thursday.",
  },
  {
    dayOffset: -3,
    company: "Valley Electric",
    manpower: 5,
    notes:
      "Pulled feeders to the main electrical room. Coordinating rough-in sequencing with HVAC.",
  },
  {
    dayOffset: -6,
    company: "Summit Builders",
    manpower: 12,
    notes:
      "Weekly coordination walk. Concrete and steel tracking on schedule; envelope submittals still pending.",
  },
];

const INSPECTIONS = [
  { dayOffset: -4, inspection_type: "Footing / Foundation", status: "Pass" },
  { dayOffset: -2, inspection_type: "Underground Plumbing", status: "Partial Pass" },
  { dayOffset: 1, inspection_type: "Structural Framing", status: "Pending" },
];

const NOTES_DELAYS = [
  {
    dayOffset: -5,
    entry_type: "Delay",
    company: "Desert Concrete",
    description:
      "Heavy rain halted the foundation pour for one day; concrete delivery was rescheduled.",
    impact: "One day added to the foundation phase.",
  },
  {
    dayOffset: -3,
    entry_type: "Note",
    company: "Summit Builders",
    description:
      "Owner requested upgraded lobby finishes; pricing to follow as a change order.",
    impact: "Potential scope addition under review.",
  },
];

const CHANGE_ORDERS = [
  {
    dayOffset: -7,
    co_number: "CO-101",
    company: "Desert Concrete",
    status: "Approved",
    description:
      "Added ADA curb ramp and additional site drainage at the north entrance.",
    amount: "4500",
    responsible_party: "Summit Builders",
  },
  {
    dayOffset: -2,
    co_number: "CO-102",
    company: "ClearView Glazing",
    status: "Pending",
    description:
      "Upgrade lobby storefront to insulated low-E glazing per owner request.",
    amount: "12500",
    responsible_party: "Owner",
  },
];

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

/**
 * Build the demo project payloads, with all dates anchored relative to
 * `referenceDate` (defaults to now) so the sample always looks current.
 * Pure — performs no I/O. The seeder feeds these to the existing create APIs.
 */
export function buildDemoProject(referenceDate = new Date()) {
  const base = new Date(referenceDate);
  base.setHours(0, 0, 0, 0);

  const dateFrom = (dayOffset) => toLocalDateInputValue(addDays(base, dayOffset));

  let cursor = addDays(base, -21);
  const tasks = TASK_PLAN.map(({ name, duration }) => {
    const task = {
      name,
      duration,
      predecessor: null,
      manual_start_date: toLocalDateInputValue(cursor),
    };
    cursor = addDays(cursor, duration);
    return task;
  });

  return {
    project: { name: DEMO_PROJECT_NAME },
    companies: COMPANIES.map((company) => ({ ...company })),
    tasks,
    dailyLogs: DAILY_LOGS.map(({ dayOffset, ...rest }) => ({
      date: dateFrom(dayOffset),
      ...rest,
    })),
    inspections: INSPECTIONS.map(({ dayOffset, ...rest }) => ({
      date: dateFrom(dayOffset),
      ...rest,
    })),
    notesDelays: NOTES_DELAYS.map(({ dayOffset, ...rest }) => ({
      date: dateFrom(dayOffset),
      ...rest,
    })),
    changeOrders: CHANGE_ORDERS.map(({ dayOffset, ...rest }) => ({
      date: dateFrom(dayOffset),
      ...rest,
    })),
  };
}
