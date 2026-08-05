# Schedule Progress and Data Date

M17.3 extends FieldFlow's deterministic project scheduler with live task
progress, actual dates, remaining duration, and a persistent Data Date. It
keeps one task collection, one scheduling engine, and the existing project
ownership and transaction boundaries.

## Architecture

```text
SchedulerPage / useScheduleActions
  -> project task collection + focused progress mutation
  -> task_progress service
  -> deterministic scheduling domain
  -> Task + ProjectScheduleSettings
```

The frontend continues to load one task collection on the lazy Schedule
route. Task-list responses add a project progress summary, so the UI does not
make a second progress request. The dashboard receives no task collection or
new schedule request in M17.3.

## Data Date

Each `ProjectScheduleSettings` row stores two independent ISO date-only
values:

- `schedule_start_date` is the planning anchor for unconstrained root work.
- `data_date` is the date through which recorded progress is current.

New projects initialize both values from the same server-selected project
date. Migration `c8d4f1a7b903` backfills existing Data Dates from each
project's persisted Schedule Start Date. Recalculation receives both dates
explicitly and never substitutes the current server date.

Settings updates are partial. Omitted fields remain unchanged, unchanged
values are idempotent, and a Data Date change recalculates the complete task
collection in the same transaction. A Data Date cannot move before a stored
Actual Start or Actual Finish.

## Progress State

Leaf tasks persist:

- `progress_status`: `not_started`, `in_progress`, or `completed`;
- `percent_complete`: whole number from 0 through 100;
- `actual_start_date` and `actual_finish_date`: ISO date-only strings;
- `remaining_duration`: whole workdays;
- `status_updated_at` and `status_updated_by`: server-controlled metadata.

The valid states are:

| State | Percent | Actual Start | Actual Finish | Remaining |
|---|---:|---|---|---:|
| Not Started | 0 | none | none | planned duration |
| In Progress | 1-99 | required | none | at least 1 |
| Completed | 100 | required | required | 0 |

Actual Finish cannot precede Actual Start, and actual dates cannot be after
the project Data Date. Corrections may move in either direction. The server
normalizes cleared fields for the target state; FieldFlow does not retain a
progress-history ledger in M17.3.

Summary progress is derived from descendants and cannot be updated directly.
Status rolls up from child states, actual dates roll up where factual, and
percent complete is duration-weighted across leaf work. Summary duration
retains its existing direct-child-count display contract.

## Scheduling Contract

Completed tasks use factual Actual Start and Actual Finish as their current
dates. They are removed from the remaining CPM network, report zero float,
and are not marked critical. Successors use their factual dates.

In-progress tasks preserve Actual Start. Remaining work is forecast from the
later of the Data Date workday boundary and any retained dependency boundary,
using `remaining_duration`. Percent complete does not infer remaining
duration.

Not-started tasks continue to derive from their predecessor, manual date, or
Schedule Start Date, but incomplete work cannot forecast before the Data
Date boundary. Planned-duration edits reset remaining duration only while a
task is Not Started.

The CPM backward pass uses remaining work for incomplete tasks. Summary
criticality and float continue to roll up from incomplete descendants.

## Out-of-Sequence Progress

FieldFlow uses retained logic. Actual progress is accepted when factual even
if it began before an FS, SS, FF, or SF predecessor boundary. Dependency links
remain unchanged, remaining work still respects the applicable boundary, and
the response derives:

- `out_of_sequence`;
- `out_of_sequence_reason` with the factual task, relationship, and date
  context.

All four relationship types, signed lag, nested summaries, and summary
predecessors use the same rule.
The flag is derived and cannot be supplied by a client.

## API

```text
GET /projects/{project_id}/tasks
PUT /projects/{project_id}/tasks/{task_id}/progress

GET /projects/{project_id}/schedule-settings
PUT /projects/{project_id}/schedule-settings
```

The focused progress request accepts only progress fields. Ownership,
forecast dates, OOS metadata, updater metadata, and project identity are
server-controlled. The response returns the complete recalculated task
collection plus an additive `summary` containing leaf counts, weighted
percent, OOS count, Data Date, forecast finish, and recent start/finish
counts.

All routes reuse authentication and `get_owned_project`. The progress service
locks the project schedule, validates the target leaf task, normalizes the
state, recalculates once, and commits once. Any validation or recalculation
failure rolls back progress, metadata, settings, and forecast dates.

## Baselines, Variance, and Templates

Baseline snapshot schemas remain planning-only and immutable. Capturing after
progress records the current forecast, milestone/constraint state, and full
dependency set as a new planning snapshot without copying live progress
fields into baseline rows.

Variance responses add current progress, actual dates, remaining duration,
OOS context, Data Date, and leaf status counts. Completed task comparison
uses its factual current finish; in-progress comparison uses its current
forecast finish. Existing slipped, improved, unchanged, added, removed,
critical, and structural classifications remain unchanged.

Templates remain planning-only. They preserve milestones, constraints, and
complete dependency sets, but saving does not copy progress or actuals.
Applying initializes every target task as Not Started with zero percent,
milestones at zero remaining duration, regular tasks at planned remaining
duration, and null actual dates. The target project's Schedule Start Date and
Data Date remain authoritative.

## Frontend

The existing Schedule route adds:

- independent Schedule Start Date and Data Date controls;
- a textual project progress summary;
- a focus-managed leaf-task progress dialog with conditional fields and
  completed-work correction confirmation;
- progress, remaining duration, actual dates, and visible OOS context in the
  task table;
- a Data Date marker and textual progress labels in the Gantt;
- a planning dialog for milestones, constraints, multiple predecessors, all
  four relationship types, lag, and lead;
- labeled Gantt milestone diamonds, constraints, and dependency connectors;
- live progress context in Baseline Comparison.

Mutation keys prevent duplicate submissions. Project generations and abort
signals reject stale success and failure callbacks. The loaded task
collection is tagged with its project before presentation, so a project
switch does not render the previous project's progress metrics.

The progress dialog traps focus, supports Escape while idle, restores focus,
associates errors with fields, keeps recoverable values after failure, and
does not expose direct progress editing for summary tasks. Narrow scheduler
tables become labeled stacked records; the semantic task table remains the
accessible Gantt fallback.

## Dashboard and Export

M17.3 does not change dashboard requests, schedule health-score inputs, or
dashboard presentation. The additive task summary is available for a later
analytics phase without introducing task fan-out now.

The existing PDF remains a current-schedule export. It now identifies the
Data Date and includes status, percent complete, remaining duration, current
forecast dates, and actual dates while preserving ownership, safe escaping,
the 5,000-task cap, and temporary-file cleanup.

## Database Safeguards

The migration adds the Data Date, progress columns, the updater foreign key,
state/range/date-order checks, and `(project_id, progress_status)`. Existing
tasks backfill to Not Started with zero percent, remaining duration equal to
planned duration, null actuals, and null updater metadata. Existing baseline
rows and planned task dates are not rewritten.

## Resource Loading Boundary

M17.6 uses these live progress and Data Date fields only to determine remaining
forecast workdays for planned crew and equipment demand. Completed tasks add no
demand, and in-progress demand starts no earlier than the Data Date. Resource
allocation never infers percent complete, remaining duration, actual dates, or
task status. Daily Log manpower remains separate historical actual reporting.

## Verification

M17.7 passes 567 frontend tests across 86 files and 404 backend tests, with
407 backend subtests reported separately. The local PostgreSQL database is at
the single Alembic head `f7c5d0b3e826`, autogenerate detects no schema drift,
and the temporary-SQLite lifecycle test passes upgrade, downgrade, re-upgrade,
constraint, index, and data-preservation checks.

Finite pure-domain probes at 100, 500, and 2,000 chained tasks measured a
maximum median of 69.44 ms across planned, in-progress, and moved-Data-Date
recalculation cases. These are local calculation measurements, not production
database, network, or browser-performance claims.

## Limits

- no progress history or strict transition graph;
- no earned value, cost loading, productivity inference, resource leveling, or
  planned-versus-actual manpower comparison;
- no configurable calendars;
- no dashboard progress visualization in M17.3;
- no baseline Gantt overlay, timeline zoom, or schedule virtualization.

M17.5 Look-Ahead Plans read these same live task progress and forecast fields.
The existing progress dialog remains the only look-ahead progress action;
readiness and commitment metadata never update percent complete, remaining
duration, or actual dates. Progress mutations refresh selected plan detail so
membership and carryover remain current without a second task collection.
