# Advanced Scheduling QA

Use synthetic project data. Record browser, viewport, zoom, API environment,
database revision, and result for each run. A checked item requires the stated
expected result; unavailable live checks must be marked Not Verified.

## Deterministic Schedule

- [ ] Set Schedule Start and Data Date independently; both persist as local
  `YYYY-MM-DD` values and recalculation is explicit.
- [ ] Create hierarchy and reorder it; parent/child order and stable IDs remain
  valid.
- [ ] Verify summary dates, duration rule, and critical path from leaf tasks.
- [ ] Exercise FS, SS, FF, and SF with positive, zero, and negative lag.
- [ ] Reject a cycle, self edge, cross-project edge, and invalid null input
  without partial writes.
- [ ] Create a milestone and all supported constraint families; mandatory
  conflicts are textual and deterministic.

## Progress and Baselines

- [ ] Exercise Not Started, In Progress, and Completed with valid actual dates,
  percent complete, and remaining duration.
- [ ] Confirm incomplete work cannot forecast before Data Date and completed
  work does not remain incorrectly critical.
- [ ] Produce and clear an out-of-sequence warning through valid input changes.
- [ ] Capture an immutable baseline, select it, paginate detail, and compare
  slipped/improved/added/removed/critical-change rows.
- [ ] Archive a baseline; snapshots remain unchanged and invalid selection is
  rejected.

## Look-Ahead and Resources

- [ ] Create a 21-day plan and verify carryover plus each weekly group exactly
  once.
- [ ] Exercise readiness, blocker, target date, commitment, company, manual
  include/exclude, archive, stale/missing task, filters, and browser print.
- [ ] Create crews/equipment, assignments, and capacity overrides; reject
  cross-project and archived targets.
- [ ] Verify over-allocation, unavailable conflicts, unassigned work, resource
  labels, bounded conflict counts, pagination, and browser print.
- [ ] Confirm look-ahead/resource actions do not move task dates.

## Health, Dashboard, and Reports

- [ ] Verify stable, attention, and critical categories from documented rules;
  reasons and thresholds are visible and no score is shown.
- [ ] Verify missing baseline is attention, zero states are defined, reasons
  are capped at 10, and attention items are deterministic/capped at 10.
- [ ] Confirm the dashboard performs one aggregate request and no task,
  look-ahead, resource-loading, attachment, or report request.
- [ ] Open Schedule Summary as the fifth Scheduler mode; loading, retry,
  project switching, baseline/Data Date context, and both report controls work.
- [ ] Download current and executive PDFs; verify authentication, ASCII-safe
  filename, escaped long/malicious names, factual missing-baseline state,
  bounded sections, and temporary cleanup.

## Authorization and Security

- [ ] With two users, cover settings, task CRUD/reorder/progress/planning,
  baselines/variance, look-ahead, crews/equipment, assignments/availability,
  resource loading, dashboard health, and both reports.
- [ ] Verify own-resource success plus foreign project, guessed ID,
  wrong-project nested ID, dependency, company, and resource denial.
- [ ] Verify no foreign name/content appears in health, conflict, or report
  output and clients cannot submit ownership/audit fields.
- [ ] Reconfirm refresh/CSRF/CORS/header/rate-limit/request-size behavior,
  unknown-field rejection, rollback, safe errors, and redacted logs.

## Accessibility

- [ ] Each Scheduler mode and dashboard has one `h1`, logical section headings,
  semantic tables/lists, labeled controls, visible focus, and named status.
- [ ] Complete task grid, mode tabs, filters, dialogs, report controls, and
  dashboard link by keyboard; verify dialog trap, Escape, and focus return.
- [ ] Confirm health, variance direction, progress, blockers, and conflicts use
  text rather than color alone; loading/error states are announced.
- [ ] At 200% zoom, all actions remain reachable. Treat the Gantt as visual
  support, not the sole accessible representation.

## Responsive and Browser Matrix

- [ ] 320px: Current, Baseline, Look-Ahead, Resource, Summary, dashboard.
- [ ] 375px: same views; long task/resource/blocker text and dialogs.
- [ ] 768px and 1024px: wrapped/scrollable tabs and contained workspaces.
- [ ] 1280px and 1600px: stable wide layout and internal timelines.
- [ ] 200% zoom: no page-level overflow outside intentional schedule regions.
- [ ] Chromium: hash routes, downloads, print, sticky columns, dialogs, Gantt,
  Back/Forward, and session cookies.
- [ ] Firefox: same matrix.
- [ ] Safari/WebKit: same matrix.

## Production Readiness

- [ ] Database current equals the single Alembic head `f7c5d0b3e826`; fresh,
  pre-M17, downgrade/re-upgrade, and autogenerate-check paths pass.
- [ ] Production CORS/session configuration, temporary PDF directory,
  request/response proxy limits, indexes, and PostgreSQL query plans are
  verified. No scheduling worker, cron, or new secret is required.
- [ ] Observe production response sizes and latency for 100, 500, and 2,000
  task schedules plus 2,000 tasks/200 resources.
- [ ] Run complete tests, lint, build, dependency audits, secret scan, and
  repository cleanup; retain no generated PDF, profile, log, database, build,
  coverage, or scale fixture.
