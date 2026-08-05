# Scheduling Architecture

This document defines the deterministic scheduling contract established in
M17.1, immutable baselines and variance from M17.2, progress and Data Date
semantics from M17.3, and milestones, constraints, and advanced dependencies
from M17.4, live Look-Ahead Planning from M17.5, and crew and equipment loading
from M17.6. It describes shipped behavior only; automatic resource leveling
and configurable calendars are not implemented.

## Architecture

```text
SchedulerPage / schedule, baseline, look-ahead, and resource hooks
        |
        v
project-scoped task, settings, baseline, look-ahead, and resource APIs
        |
        v
FastAPI routers -> scheduling/validation services
        |
        v
pure scheduling domain -> scheduling services -> SQLAlchemy schedule models
```

`backend/app/domain/scheduling.py` is a pure calculation layer. It receives
tasks, an explicit project start date, and an explicit Data Date and has no
database, authentication, or server-clock access. Routers own project
authorization and transaction boundaries. Services translate ORM tasks into
immutable domain values and persist calculated dates.

The frontend loads tasks, schedule settings, and focused baseline state only
on the lazy Schedule route. It does not add any of those requests to the
project dashboard. Baseline lifecycle, snapshot contents, variance formulas,
and deliberate deferrals are documented in
[`SCHEDULE_BASELINES.md`](SCHEDULE_BASELINES.md).
The live progress contract is documented in
[`SCHEDULE_PROGRESS.md`](SCHEDULE_PROGRESS.md).
The live short-term planning contract is documented in
[`LOOK_AHEAD_PLANNING.md`](LOOK_AHEAD_PLANNING.md).

## Schedule Start Anchor

Every project owns exactly one `ProjectScheduleSettings` row:

- `project_id` is both the primary key and project foreign key.
- `schedule_start_date` is a non-null ISO `YYYY-MM-DD` string.
- `data_date` is the independent non-null progress boundary in the same
  format.
- `comparison_baseline_id` is the nullable project comparison pointer.
- `created_at` and `updated_at` are timezone-aware timestamps.
- deleting a project cascades to its settings row.

New project creation chooses the server's local date once and persists it in
the same transaction as the project. Scheduling never falls back to the
current date. Recalculating identical task inputs against the same settings
therefore produces identical dates on every day.

New projects initialize Data Date from Schedule Start Date. M17.3 backfills
existing Data Dates from the already-persisted Schedule Start Date without
using planned dates as actual dates.

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

Task create, update, delete, reorder, template apply, settings update,
progress update, and baseline capture serialize on the same project row.
Each mutation uses one transaction:

1. Authenticate and resolve the owned project.
2. Validate input, ownership, references, hierarchy, and graph structure.
3. Flush the intended mutation without committing.
4. Load the persistent Schedule Start Date and Data Date.
5. Recalculate the complete project task collection.
6. Commit once, or roll back settings, task fields, and calculated dates
   together on any failure.

Task responses continue to return the complete recalculated collection for
create, update, and delete. Reorder and template apply preserve their existing
message responses.

## Dependencies

Each leaf task supports up to 50 ordered `TaskDependency` rows with a stable
task-ID predecessor, relationship type, and signed lag:

- `FS`: successor start from predecessor finish;
- `SS`: successor start from predecessor start;
- `FF`: successor finish from predecessor finish;
- `SF`: successor finish from predecessor start;
- `lag_days`: -36,500 through 36,500 workdays; negative values are lead.

The most restrictive boundary across every predecessor controls the forward
pass. The normalized collection is authoritative. The original
`predecessor_task_id`, `dependency_type`, `lag_days`, and compact
`predecessor` response remain as a first-dependency compatibility projection.
Existing syntax such as `12`, `12+3`, and `12SS+4` remains accepted and now
also supports values such as `12FF-2` and `12SF+1`.

Duplicate predecessors, self links, cross-project references, dependency
cycles, parent cycles, combined hierarchy/dependency cycles, and dependencies
on summary rows are rejected with 422. Clearing dependencies normalizes the
legacy projection to null/`FS`/zero. Deleting a predecessor removes its links
and promotes the next stable dependency into that projection.

## Milestones and Constraints

Milestones are leaf tasks with `is_milestone = true`, zero duration, zero
remaining duration, and identical start/finish dates. They participate in
dependencies, CPM, templates, and baselines. They may be Not Started or
Completed; In Progress is invalid because there is no remaining duration.

Tasks support `ASAP`, `ALAP`, `SNET`, `SNLT`, `FNET`, `FNLT`, `MS`, and `MF`.
All dated constraints require an ISO date that is a workday. Precedence is:

1. Completed actual dates and in-progress Actual Start remain factual.
2. Mandatory Start/Finish place unstarted work on the exact constraint date;
   conflicts with dependencies, manual dates, or Data Date are reported.
3. Dependencies, manual/root dates, Data Date, SNET, and FNET determine the
   earliest normal boundary.
4. SNLT and FNLT constrain the late pass, producing negative float and a
   visible violation when the forecast is late.
5. ALAP moves unstarted work to its late start within the remaining project
   network. ASAP retains the normal forward-pass result.

Constraint violations and reasons are derived response fields, not client
controlled state. Progress is never rewritten to satisfy a planning
constraint.

## Summary Predecessors

A task becomes a summary when another task names it as a parent. M17.1
supports leaf tasks depending on summaries under this contract:

- A summary's effective start and finish come from all direct children.
- Nested summaries resolve from the deepest descendants outward.
- A successor waits until the summary rollup is resolved.
- FS, SS, FF, SF, and signed lag use summary dates, never summary duration.
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

A deterministic topological pass resolves every node at most once. Completed
leaves use actual dates, in-progress leaves forecast remaining work from the
Data Date and retained dependency boundary, and not-started leaves calculate
from their manual/root or predecessor anchor no earlier than the Data Date.
Summaries roll up only after their direct children resolve. Nodes outside the
topological order are cyclic and remain unscheduled in the pure domain
result; API validation rejects those structures before persistence.

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
backward pass mirrors FS/SS/FF/SF and signed-lag behavior over scheduled
leaf-to-leaf dependencies. Upper-bound and mandatory constraints participate
in late-start bounds, so missed deadlines can produce negative float. Summary
rows aggregate the most constrained child float and whether any child is
critical.

Completed tasks are excluded from the remaining CPM network, report zero
float, and are not critical. In-progress CPM uses remaining duration and its
forecast calculation boundary rather than treating Actual Start as remaining
work.

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

Templates preserve names, order, duration, milestone state, constraints,
every normalized dependency, and parent relationships. They are structural
patterns, not source-project calendar snapshots. Saving and applying a
template does not carry absolute manual start dates. Applied root work uses
the target project's Schedule Start Date, and the complete target schedule
recalculates atomically.

Templates also remain progress-free: apply initializes Not Started, zero
percent, remaining duration equal to planned duration, and null actual dates.

Templates remain owner-scoped and cannot be applied across users.

## Dashboard and Export

The dashboard and PDF export read persisted deterministic task dates. Neither
uses the server date as a schedule anchor. M17.3 intentionally adds no
dashboard task request or progress visualization. The current-schedule PDF
now identifies Data Date and includes status, percent, remaining duration,
current forecast dates, and actual dates.

Dashboard schedule counts, planned range, attention items, and upcoming work
continue to include summary rows for compatibility. PDF export preserves the
5,000-task cap, safe text handling, bounded temporary-file lifecycle, and
project ownership checks.

M17.5 adds no dashboard request or metric. Look-ahead data loads only in the
lazy Schedule route. Look-ahead output uses a print-specific frontend layout;
the existing PDF endpoint remains the current-schedule export and no second
server reporting path is introduced.

M17.6 likewise adds no dashboard request or metric. Resource Loading consumes
the live forecast only on the lazy Schedule route and uses browser print. It
does not change CPM inputs, task dates, baselines, or the server PDF contract.

## APIs

```text
GET    /projects/{project_id}/tasks
POST   /projects/{project_id}/tasks
PUT    /projects/{project_id}/tasks/reorder
PUT    /projects/{project_id}/tasks/{task_id}
PUT    /projects/{project_id}/tasks/{task_id}/progress
DELETE /projects/{project_id}/tasks/{task_id}

GET    /projects/{project_id}/schedule-settings
PUT    /projects/{project_id}/schedule-settings

POST   /projects/{project_id}/schedule-baselines
GET    /projects/{project_id}/schedule-baselines
GET    /projects/{project_id}/schedule-baselines/{baseline_id}
POST   /projects/{project_id}/schedule-baselines/{baseline_id}/archive
PUT    /projects/{project_id}/schedule-baseline-comparison
GET    /projects/{project_id}/schedule-variance

POST   /projects/{project_id}/look-ahead-plans
GET    /projects/{project_id}/look-ahead-plans
GET    /projects/{project_id}/look-ahead-plans/{plan_id}
PUT    /projects/{project_id}/look-ahead-plans/{plan_id}
POST   /projects/{project_id}/look-ahead-plans/{plan_id}/archive
PUT    /projects/{project_id}/look-ahead-plans/{plan_id}/items/{task_id}
```

The settings request accepts only:

```json
{"schedule_start_date": "2026-04-06", "data_date": "2026-04-13"}
```

The partial settings request may include either date; omitted values are
unchanged. The response contains `project_id`, `schedule_start_date`,
`data_date`, `comparison_baseline_id`, `created_at`, and `updated_at`.
Authentication and `get_owned_project` apply to all routes.
Invalid dates, unknown fields, and client-supplied ownership fields return
safe 422 responses.

## Frontend Safety and Accessibility

Schedule mutations capture project identity and an operation generation at
dispatch. Project switching aborts supported requests and clears editing,
progress/planning selection, template selection, and pending state. Late
successes, failures, and optimistic reorder rollbacks are ignored. Duplicate
in-flight mutations with the same key are suppressed.

Schedule Start Date and Data Date have visible labels, distinct help text,
field-specific validation, pending state, and focused confirmation where the
change affects existing work. Leaf progress uses a task-specific dialog with
conditional fields, correction confirmation, focus trapping, Escape, value
preservation after failure, and focus restoration. Summary progress remains
derived. A separate focus-managed planning dialog edits milestone state,
duration, constraints, and ordered predecessor rows without introducing a
second task collection. The table names milestone and constraint states, and
the Gantt uses labeled milestone diamonds, constraint markers, and an SVG
overlay with visible dependency type/lead/lag labels. Task-load failure
retains the global feedback banner and adds one local keyboard-accessible
retry that issues one fresh request.

Baseline capture and archive use focus-managed dialogs. Comparison metrics
use explicit direction text, and the semantic desktop table becomes labeled
stacked records on narrow screens. Project switching aborts and rejects stale
baseline work and remounts local scheduler state. Automated component and
integration coverage verifies these behaviors. Browser checks at 320, 375,
768, and 1024 pixels, wide desktop, and 200% zoom were not performed in M17.5
and remain manual release verification.

Look-Ahead Planning is the third Schedule mode. Its focused hook clears state
on project and plan changes, aborts supported requests, rejects stale results,
deduplicates mutations, and reuses the canonical task collection and existing
progress/planning dialogs. Create and item dialogs trap and restore focus,
support Escape, and expose textual readiness, blocker, commitment, schedule,
and attention states. Archived plans are read-only.

Resource Loading is the fourth Schedule mode. Focused hooks batch project
crews and equipment, lazy-load the bounded loading matrix, reject stale
project/range responses, and keep assignment and availability metadata outside
the canonical task collection. Its full contract is documented in
[`RESOURCE_PLANNING.md`](RESOURCE_PLANNING.md).

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

M17.3 repeated three pure-domain runs per case on August 2, 2026 and recorded
the median for a linear FS chain through progress rollup, out-of-sequence
analysis, and critical-path annotation:

| Tasks | Planned | First task in progress | Data Date moved |
|---:|---:|---:|---:|
| 100 | 3.06 ms | 2.97 ms | 2.94 ms |
| 500 | 15.22 ms | 15.34 ms | 15.43 ms |
| 2,000 | 62.84 ms | 61.41 ms | 69.44 ms |

These bounded measurements are local calculation evidence only. They do not
claim PostgreSQL, network, PDF, or browser-render latency.

M17.4 repeated three mixed-network runs on August 4, 2026. Each case cycles
FS/SS/FF/SF, signed lag, periodic milestones, and dated lower constraints:

| Tasks | Median |
|---:|---:|
| 100 | 4.36 ms |
| 500 | 20.99 ms |
| 2,000 | 86.04 ms |

M17.5 local SQLite/TestClient detail probes on August 4, 2026 measured live
task loading, inclusion, weekly grouping, response serialization, and a
metadata update followed by detail refresh:

| Tasks | SELECTs | Detail | Response | Metadata update |
|---:|---:|---:|---:|---:|
| 100 | 7 | 16.48 ms | 88,110 bytes | 18.63 ms |
| 500 | 7 | 37.09 ms | 438,526 bytes | 41.44 ms |
| 2,000 | 10 | 163.52 ms | 1,756,534 bytes | 152.89 ms |

The 2,000-task SELECT count reflects bounded select-in batches, not N+1
loading. These are local regression figures, not PostgreSQL, network, print,
or browser-render claims.

- 100 tasks: normal interaction target.
- 500 tasks: supported backend/API schedule size.
- 2,000 tasks: backend correctness and reorder-request maximum; browser
  usability is not claimed.
- 5,000 tasks: export-only cap; interactive use is not claimed.

The frontend table and Gantt render all visible tasks and dates without
virtualization or pagination. Browser interaction, response transfer, and
template-apply timing at the upper limits remain follow-up performance work.

## Database Safeguards

Tasks enforce milestone-aware duration, signed lag bounds, all four
relationship values, valid constraint/date pairs, nonnegative nullable order,
0/1 collapse state, and no direct self-parent or self-predecessor. Duration
and collapse are non-null. M17.1 converted legacy null/nonpositive duration
values to one workday; M17.4 introduces zero only for explicit milestones.

M17.3 additionally enforces progress status, percent and remaining-duration
ranges, actual-date ordering, complete state consistency, updater ownership,
and a project/status lookup index.

M17.4 adds project-owned normalized dependency tables for live tasks,
templates, and baseline snapshots. Each prevents duplicate and self links,
checks relationship and lag values, cascades with its owner, and indexes task
and predecessor lookups. One data-preserving migration backfills every legacy
live, template, and baseline predecessor while retaining the compatibility
columns.

M17.5 adds project-owned plan headers and sparse task-metadata rows. Database
checks bound status, readiness, window duration, and mutually exclusive manual
flags. Project/name and plan/task uniqueness are enforced. Plans cascade with
projects, item rows cascade with plans, and optional project-company deletion
sets the assignment to null. Task IDs intentionally remain non-FK historical
references so deleted task metadata remains factual and unavailable.

M17.6 adds project-owned crew, equipment, assignment, and availability tables.
Checks enforce positive whole-number capacities and allocations, nonnegative
dated overrides, ordered ranges, supported statuses, and exactly one typed
resource reference. Composite indexes support project lists, task/resource
assignment joins, and availability range reads without per-task queries.

Indexes support the canonical project/order query and project-scoped
predecessor and parent validation:

- `(project_id, order_index, id)`
- `(project_id, predecessor_task_id)`
- `(project_id, parent_task_id)`
- `(project_id, progress_status)`

The settings primary key already supplies the unique project index, so no
redundant index is added. Baseline headers enforce project/name uniqueness,
status, and counts; snapshot rows enforce one original task ID per baseline
and index deterministic order, parent, and predecessor lookups.

## Verification and Limits

M17.6 verification passes 554 frontend tests across 83 files and 396 backend
tests, with 407 backend subtests reported separately. PostgreSQL and SQLite
migration upgrade/downgrade/re-upgrade paths use Alembic revision
`f7c5d0b3e826`.

Known limitations and deferred M17 work:

- look-ahead plans remain live operational views, not immutable snapshots;
- no look-ahead publish state, commitment audit, dashboard metric, or server PDF;
- no automatic resource leveling, resource-driven rescheduling, cost loading,
  workforce management, or planned-versus-actual manpower analytics;
- no progress history, earned value, or strict transition graph;
- no configurable project calendars or timezones;
- summary duration remains direct-child count;
- summary-predecessor CPM propagation remains limited as described above;
- no baseline Gantt overlay, baseline dashboard metric, or variance export;
- no timeline zoom or schedule virtualization;
- no dashboard schedule-progress visualization in M17.3.
