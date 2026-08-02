# Scheduling Architecture

This document defines the deterministic scheduling contract established in
M17.1 and extended with immutable baselines and variance in M17.2. It
describes shipped behavior only; progress, actual dates, look-ahead planning,
resource loading, and configurable calendars are not implemented.

## Architecture

```text
SchedulerPage / useScheduleActions + useScheduleBaselines
        |
        v
project-scoped task, settings, baseline, and variance APIs
        |
        v
FastAPI routers -> scheduling/validation services
        |
        v
pure scheduling domain -> scheduling services -> SQLAlchemy schedule models
```

`backend/app/domain/scheduling.py` is a pure calculation layer. It receives
tasks and an explicit project start date and has no database, authentication,
or server-clock access. Routers own project authorization and transaction
boundaries. Services translate ORM tasks into immutable domain values and
persist calculated dates.

The frontend loads tasks, schedule settings, and focused baseline state only
on the lazy Schedule route. It does not add any of those requests to the
project dashboard. Baseline lifecycle, snapshot contents, variance formulas,
and deliberate deferrals are documented in
[`SCHEDULE_BASELINES.md`](SCHEDULE_BASELINES.md).

## Schedule Start Anchor

Every project owns exactly one `ProjectScheduleSettings` row:

- `project_id` is both the primary key and project foreign key.
- `schedule_start_date` is a non-null ISO `YYYY-MM-DD` string.
- `comparison_baseline_id` is the nullable project comparison pointer.
- `created_at` and `updated_at` are timezone-aware timestamps.
- deleting a project cascades to its settings row.

New project creation chooses the server's local date once and persists it in
the same transaction as the project. Scheduling never falls back to the
current date. Recalculating identical task inputs against the same settings
therefore produces identical dates on every day.

Existing projects are backfilled in this order:

1. Earliest valid start date among root leaf tasks.
2. Earliest valid start date among any leaf task.
3. The migration execution date when no valid leaf date exists.

Summary dates are excluded from backfill candidates because they are derived
rollups. The fallback is calculated once per migration run and then persisted.

Root leaf tasks without `manual_start_date` use the project anchor. A manual
root date remains authoritative and snaps to the next workday. A task with a
predecessor derives from that predecessor; its manual date is not a second
constraint.

## Task Lifecycle

Task create, update, delete, reorder, template apply, schedule-start update,
and baseline capture serialize on the same project row. Each mutation uses
one transaction:

1. Authenticate and resolve the owned project.
2. Validate input, ownership, references, hierarchy, and graph structure.
3. Flush the intended mutation without committing.
4. Load the persistent schedule anchor.
5. Recalculate the complete project task collection.
6. Commit once, or roll back settings, task fields, and calculated dates
   together on any failure.

Task responses continue to return the complete recalculated collection for
create, update, and delete. Reorder and template apply preserve their existing
message responses.

## Dependencies

Each leaf task supports one stable task-ID predecessor:

- `FS`: start after the predecessor finish.
- `SS`: start from the predecessor start.
- `lag_days`: zero through 36,500 calendar days.

FS adds one calendar day after predecessor finish, adds lag, then snaps to the
next workday. SS adds lag to predecessor start, then snaps to the next
workday. This preserves the existing API syntax such as `12`, `12+3`, and
`12SS+4`.

Self references, cross-project references, dependency cycles, parent cycles,
and combined hierarchy/dependency cycles are rejected with 422. Clearing a
predecessor is valid and normalizes its relationship to `FS` with zero lag.

## Summary Predecessors

A task becomes a summary when another task names it as a parent. M17.1
supports leaf tasks depending on summaries under this contract:

- A summary's effective start and finish come from all direct children.
- Nested summaries resolve from the deepest descendants outward.
- A successor waits until the summary rollup is resolved.
- FS, SS, and lag use summary start/finish dates, never summary duration.
- If any required descendant is unresolved, the summary and its successor
  remain unresolved.
- A summary cannot have its own predecessor because shifting descendants from
  a summary-level constraint is not an implemented scheduling rule.

Summary `duration` intentionally remains the count of directly scheduled
children for display compatibility. It is not elapsed workdays and is never
used in predecessor date math.

## Scheduling Algorithm

The calculator builds one directed graph:

- predecessor-to-leaf edges represent task dependencies;
- child-to-summary edges represent hierarchy rollup prerequisites.

A deterministic topological pass resolves every node at most once. Leaves
calculate dates from their manual/root or predecessor anchor. Summaries roll
up only after their direct children resolve. Nodes outside the topological
order are cyclic and remain unscheduled in the pure domain result; API
validation rejects those structures before persistence.

Graph construction and topological scheduling are `O(V + E)`, excluding
calendar-day iteration required to add durations and lag. Hierarchy depth and
rollup use memoized parent paths and adjacency lists, also `O(V + E)` for a
valid hierarchy. The CPM backward pass is topological over scheduled leaf
dependencies and is `O(V + E)` plus calendar arithmetic.

## Workdays and Holidays

Durations count inclusive workdays. Saturdays, Sundays, and observed US
federal holidays are excluded. Fixed holidays use Friday/Monday observance;
the calendar also includes MLK Day, Washington's Birthday, Memorial Day,
Labor Day, Columbus Day, and Thanksgiving.

The calendar is fixed application behavior. FieldFlow does not yet support
project calendars, work weeks, shutdown periods, or custom holidays.

## Critical Path and Float

Critical-path metadata is derived on response and is not persisted. The
backward pass mirrors FS/SS and lag behavior over scheduled leaf-to-leaf
dependencies. Summary rows aggregate the most constrained child float and
whether any child is critical.

Summary-predecessor dates are correct, but CPM does not yet propagate a
summary successor edge back through all terminal descendants. Critical flags
around that particular relationship can therefore be conservative. This is
documented debt, not a date-calculation defect.

## Hierarchy Order

Server reorder validation requires a preorder traversal:

- every parent appears before each descendant;
- each subtree is contiguous;
- every project task appears exactly once;
- duplicate, missing, foreign, and lists over 2,000 IDs are rejected.

Invalid order requests return 422 before any `order_index` changes. Existing
nullable order values remain compatible; explicit reorder assigns sequential
values.

## Templates

Templates preserve names, order, duration, lag, dependencies, and parent
relationships. They are structural patterns, not source-project calendar
snapshots. Saving and applying a template does not carry absolute manual start
dates. Applied root work uses the target project's Schedule Start Date, and
the complete target schedule recalculates atomically.

Templates remain owner-scoped and cannot be applied across users.

## Dashboard and Export

The dashboard and PDF export read persisted deterministic task dates. Neither
uses the server date as a schedule anchor or exposes schedule settings.
M17.2 intentionally adds no dashboard baseline request or metric and does not
change the current-schedule PDF.

Dashboard schedule counts, planned range, attention items, and upcoming work
continue to include summary rows for compatibility. PDF export preserves the
5,000-task cap, safe text handling, bounded temporary-file lifecycle, and
project ownership checks.

## APIs

```text
GET    /projects/{project_id}/tasks
POST   /projects/{project_id}/tasks
PUT    /projects/{project_id}/tasks/reorder
PUT    /projects/{project_id}/tasks/{task_id}
DELETE /projects/{project_id}/tasks/{task_id}

GET    /projects/{project_id}/schedule-settings
PUT    /projects/{project_id}/schedule-settings

POST   /projects/{project_id}/schedule-baselines
GET    /projects/{project_id}/schedule-baselines
GET    /projects/{project_id}/schedule-baselines/{baseline_id}
POST   /projects/{project_id}/schedule-baselines/{baseline_id}/archive
PUT    /projects/{project_id}/schedule-baseline-comparison
GET    /projects/{project_id}/schedule-variance
```

The settings request accepts only:

```json
{"schedule_start_date": "2026-04-06"}
```

The response contains `project_id`, `schedule_start_date`,
`comparison_baseline_id`, `created_at`, and `updated_at`. Authentication and
`get_owned_project` apply to all routes.
Invalid dates, unknown fields, and client-supplied ownership fields return
safe 422 responses.

## Frontend Safety and Accessibility

Schedule mutations capture project identity and an operation generation at
dispatch. Project switching aborts supported requests and clears editing,
selection, template selection, and pending state. Late successes, failures,
and optimistic reorder rollbacks are ignored. Duplicate in-flight mutations
with the same key are suppressed.

The Schedule Start Date has a visible label, associated impact text,
field-specific validation, pending state, and a confirmation dialog when
tasks exist. The existing dialog traps focus, supports Escape, and restores
focus. Task-load failure retains the global feedback banner and adds one local
keyboard-accessible retry that issues one fresh request.

Baseline capture and archive use focus-managed dialogs. Comparison metrics
use explicit direction text, and the semantic desktop table becomes labeled
stacked records on narrow screens. Project switching aborts and rejects stale
baseline work and remounts local scheduler state. Automated component and
integration coverage verifies these behaviors. Browser checks at 320, 375,
768, and 1024 pixels, wide desktop, and 200% zoom were not performed in M17.2
and remain manual release verification.

## Scale Budgets

Local pure-domain probes on August 1, 2026 produced:

| Tasks | Dependency chain | Approx. serialized domain payload |
|---:|---:|---:|
| 100 | 1.71 ms | 25.7 KB |
| 500 | 8.35 ms | 129.7 KB |
| 2,000 | 32.30 ms | 522.7 KB |
| 5,000 | 80.33 ms | 1.31 MB |

A maximally deep WBS measured 1.67 ms at 100 tasks, 7.71 ms at 500, and
31.61 ms at 2,000. These are local calculation probes, not HTTP latency or
browser-render claims.

- 100 tasks: normal interaction target.
- 500 tasks: supported backend/API schedule size.
- 2,000 tasks: backend correctness and reorder-request maximum; browser
  usability is not claimed.
- 5,000 tasks: export-only cap; interactive use is not claimed.

The frontend table and Gantt render all visible tasks and dates without
virtualization or pagination. Browser interaction, response transfer, and
template-apply timing at the upper limits remain follow-up performance work.

## Database Safeguards

Tasks enforce duration and lag bounds, FS/SS relationship values,
nonnegative nullable order, 0/1 collapse state, and no direct self-parent or
self-predecessor. Duration and collapse are non-null. The migration converted
legacy null/nonpositive duration values to one workday; the audited local
database contained one zero-duration row whose stored one-day span was
preserved.

Indexes support the canonical project/order query and project-scoped
predecessor and parent validation:

- `(project_id, order_index, id)`
- `(project_id, predecessor_task_id)`
- `(project_id, parent_task_id)`

The settings primary key already supplies the unique project index, so no
redundant index is added. Baseline headers enforce project/name uniqueness,
status, and counts; snapshot rows enforce one original task ID per baseline
and index deterministic order, parent, and predecessor lookups.

## Verification and Limits

M17.2 verification passes 483 frontend tests across 71 files and 327 backend
tests, with 354 backend subtests reported separately. PostgreSQL and SQLite
migration upgrade/downgrade/re-upgrade paths pass at Alembic revision
`a2c7e9f4b610`.

Known limitations and deferred M17 work:

- one predecessor per task; FS and SS only;
- no actual dates, progress, percent complete, or data date;
- no milestones, constraints, look-ahead planning, resources, or crews;
- no configurable project calendars or timezones;
- summary duration remains direct-child count;
- summary-predecessor CPM propagation remains limited as described above;
- no baseline Gantt overlay, baseline dashboard metric, or variance export;
- no Gantt dependency arrows, timeline zoom, or schedule virtualization.

M17.3 must preserve this anchor, immutable history, transaction, hierarchy,
and deterministic graph contract when progress tracking is introduced.
