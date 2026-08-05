# Schedule Baselines and Variance

M17.2 adds immutable, project-scoped schedule snapshots and workday variance
analysis to the existing deterministic scheduler. M17.3 adds live progress
and Data Date context. M17.4 extends immutable planning snapshots with
milestones, constraints, and complete normalized dependency sets without
turning variance into earned-value analysis. M17.5 Look-Ahead Plans remain
live operational views; teams use these baselines when immutable task dates
or historical variance are required.

## Architecture

```text
SchedulerPage
  -> useScheduleBaselines
  -> project-scoped baseline and variance APIs
  -> schedule_baseline service
  -> ScheduleBaseline + ScheduleBaselineTask
  -> ProjectScheduleSettings.comparison_baseline_id
```

Baseline state loads only on the lazy Schedule route. It is intentionally
separate from `useRecordForms`, dashboard resources, task editing, and the
current schedule PDF. The comparison is a table-first subview of the existing
`#/projects/{project_id}/schedule` route.

## Data Model

`ScheduleBaseline` stores the owned project, immutable name and description,
server-generated capture time and user, captured Schedule Start Date, task
count, active/archived lifecycle, and archive timestamp.

`ScheduleBaselineTask` stores enough historical context to explain a future
comparison:

- original stable task ID and name;
- order, WBS path, parent ID, every predecessor/type/lag relationship;
- duration, milestone state, constraint type/date, manual start, calculated
  start, and calculated finish;
- summary/leaf classification, critical state, and total float.

Snapshot parent, predecessor, and task IDs are raw original IDs rather than
foreign keys to live tasks. Live task deletion must not erase history or make
a baseline unreadable. PostgreSQL task IDs are sequence-backed and are the
stable join key used by the current schema. SQLite is test-only and can reuse
the highest deleted integer ID if callers manually rely on implicit ID
allocation; production identity permanence depends on PostgreSQL sequences.

One `ProjectScheduleSettings.comparison_baseline_id` pointer separates
project comparison preference from snapshot data. Its foreign key uses
`ON DELETE SET NULL`; project deletion cascades baseline headers and snapshot
rows.

## Lifecycle and Immutability

Capture is one transaction:

1. Authenticate and resolve the owned project.
2. Lock the project row with `SELECT FOR UPDATE` on PostgreSQL.
3. Validate the bounded, trimmed name and optional description.
4. Load settings and tasks in deterministic order.
5. Validate and recalculate against the persisted Schedule Start Date and
   Data Date.
6. Derive critical path and float.
7. Insert one header and all snapshot rows.
8. Select the new baseline as the comparison default.
9. Commit once, or roll back every write.

Task create, update, delete, reorder, template apply, Schedule Start Date
update, and baseline capture use the same project lock. SQLite proves
transaction behavior but cannot prove PostgreSQL row-lock scheduling.

Names are unique per project across active and archived history using a
case-folded normalized value. Duplicate names return `409`; FieldFlow never
silently renames a baseline. Archived names are not reusable.

Snapshots have no update, task-insert, task-delete, or hard-delete API. Name,
description, capture metadata, settings, and task rows remain immutable.
Archiving is idempotent and preserves the full snapshot. Archiving the
selected default clears the settings pointer atomically and requires the user
to select another comparison. Archived history remains explicitly viewable
but cannot be persisted as the default.

If no pointer is selected, variance uses the newest active baseline for that
request without silently persisting it. A newly captured baseline becomes the
explicit default. If no baseline exists, the API returns `baseline: null`,
`summary: null`, and no rows rather than misleading zero variance.

## Variance Contract

Current and baseline tasks join by stable task ID in memory after one bounded
current-task load and one snapshot-task load. Date differences reuse the
fixed federal workday calendar:

- start variance = current start minus baseline start, in workdays;
- finish variance = current finish minus baseline finish, in workdays;
- duration variance = current duration minus baseline duration, in days;
- float variance = current total float minus baseline total float, in
  workdays.

Positive date variance is later; negative is earlier; zero is unchanged.
Missing or invalid dates remain `unscheduled` or `incomparable`. Added and
removed rows have no invented numeric variance.

Finish dates classify matched tasks as `slipped`, `improved`, or `unchanged`.
The remaining states are `added`, `removed`, `unscheduled`, and
`incomparable`. Critical comparison reports newly critical, no longer
critical, remained critical, or remained noncritical. Structural flags report
hierarchy, dependency-set, milestone, constraint, duration, manual-start, and
order changes.

Summary rows preserve hierarchy and may appear in the detail table, but
project counts use leaf tasks so work is not double counted. The response
includes baseline/current task and leaf counts, classification totals,
project finishes and finish variance, critical totals, and critical changes.

M17.3 variance rows add live status, percent, actual dates, remaining
duration, and out-of-sequence context. The summary adds current Data Date and
leaf counts for Not Started, In Progress, Completed, and Out of Sequence.
Completed rows compare factual finish; in-progress rows compare forecast
finish. Baseline rows remain unchanged and progress-free.

## API

```text
POST /projects/{project_id}/schedule-baselines
GET  /projects/{project_id}/schedule-baselines
GET  /projects/{project_id}/schedule-baselines/{baseline_id}
POST /projects/{project_id}/schedule-baselines/{baseline_id}/archive
PUT  /projects/{project_id}/schedule-baseline-comparison
GET  /projects/{project_id}/schedule-variance
```

All routes reuse access-token authentication and `get_owned_project`.
Baseline IDs are resolved inside the requested project; foreign and guessed
IDs return the repository's safe missing-record behavior. Mutation schemas
forbid unknown fields and client ownership, capture, lifecycle, count, and
snapshot data. List/detail/variance limits are bounded. Variance search is
trimmed and length-bounded, and status, critical change, sorting, and order
are allowlisted. GET responses use `Cache-Control: no-store`.

## Frontend Workflow

The sidebar lists at most 100 baselines newest first, groups active and
archived history, shows capture time and lifecycle state, and provides
capture and archive actions. The capture dialog shows the current Schedule
Start Date, task count, server timestamp policy, and immutable-snapshot
warning. It validates the name, prevents duplicate submission, traps focus,
supports Escape, restores focus, and surfaces local plus global errors.

The Baseline Comparison subview presents textual project metrics, explicit
later/earlier wording, search, allowlisted filters and sorting, summary-row
control, bounded pagination, and a semantic table. At narrow widths each row
becomes a labeled comparison record. Added, removed, unavailable, critical,
and structural states remain visible text and do not rely on color.
Live progress and factual out-of-sequence reasons appear as additive text in
the same comparison rows.

`useScheduleBaselines` owns list, comparison, capture, archive, filters,
variance, abort controllers, retries, mutation deduplication, and global
feedback integration. Project changes synchronously expose empty derived
state, abort old work, reject late responses, and remount the scheduler so an
open dialog and local comparison mode cannot leak across projects.

## Scale and Query Behavior

Local in-memory SQLite TestClient probes on August 2, 2026 used a linear FS
chain and a 200-row variance response page:

| Tasks | Capture | Variance | Capture response | Variance response |
|---:|---:|---:|---:|---:|
| 100 | 28.51 ms | 14.22 ms | 291 B | 73,032 B |
| 500 | 72.03 ms | 28.43 ms | 291 B | 145,740 B |
| 2,000 | 282.97 ms | 87.97 ms | 293 B | 145,951 B |

These are local correctness probes, not PostgreSQL production latency or
browser-usability claims. Normalized live and baseline dependency loading adds
two bounded select-in queries; instrumentation verifies no more than six
`SELECT` statements for variance. The UI requests 50 rows by default;
the API caps a variance page at 200 and a baseline detail page at 500. Browser
render profiling at large task counts was not performed.

## Deliberate Deferrals

- The dashboard receives no baseline request or metric; baseline analytics
  remain a later M17 analytics decision.
- PDF export remains current-schedule only; it does not export variance.
- The Gantt has live progress and a Data Date marker, but no baseline overlay.
  An overlay would require safe handling of removed tasks and combined
  timeline bounds, so the semantic table remains the accessible comparison
  source.
- Progress history, resource loading, configurable calendars, version labels,
  snapshot purge, and signed comparison exports are not implemented.
- Look-Ahead Plans do not copy baseline rows, add per-item variance requests,
  or alter the selected comparison baseline.

## Verification

M17.5 passes 536 frontend tests across 78 files and 384 backend tests, with
393 backend subtests reported separately. Baseline revision `a2c7e9f4b610`
remains immutable beneath progress revision `c8d4f1a7b903` and advanced
scheduling revision `d4e8a1c7f925`; existing projects still receive no
automatic baseline.

Deterministic tests cover ownership, mass assignment, immutability, rollback,
selection and archive policy, malformed and missing dates, classifications,
critical and structural changes, query bounds, filters, pagination, stale
requests, focus behavior, and 100/500/2,000-task correctness. A live browser
matrix at 320, 375, 768, and 1024 pixels, wide desktop, and 200% zoom was not
run and remains manual release verification.
