# Look-Ahead Planning

M17.5 adds project-scoped Look-Ahead Plans to the existing Schedule route.
The feature is a bounded operational view over the canonical task collection,
not a second schedule and not an immutable snapshot. Baselines remain the
source of historical schedule comparison.

## Architecture

```text
SchedulerPage -> useLookAheadPlans -> project look-ahead API
                                      |
                                      v
                          look_ahead service
                         /                  \
        persisted plan/item metadata    live scheduled tasks
                         \                  /
                          grouped detail response
```

The frontend loads look-ahead state only when the lazy Schedule route is
active. It reuses the canonical task collection for manual candidates and the
existing progress and CPM-planning dialogs. It does not add a dashboard
request or fetch one resource per task.

## Persistence

`LookAheadPlan` stores:

- project, creator, name, optional description;
- strict ISO anchor date and a 7-42 calendar-day window;
- `active` or `archived` status; and
- created, updated, and archived timestamps.

Names are trimmed, normalized with `casefold`, and unique per project.
Plans are ordered newest first and lists are bounded to 100 rows.

`LookAheadItem` stores only plan-specific metadata:

- stable task ID and project/plan identity;
- readiness status;
- blocker reason, allowlisted category, owner, and target date;
- commitment note;
- optional project-company assignment;
- manual include/exclude flags and an override reason; and
- creator, updater, and timestamps.

Task name, WBS, dates, duration, progress, milestone state, dependencies,
formal scheduling constraints, critical state, and float are not copied.
Item rows are sparse and unique by plan/task. The task ID deliberately has no
foreign key: deleting a task preserves historical planning metadata and the
detail response reports it as unavailable without exposing foreign data.

## Planning Window

New plans default to the project's persistent Data Date and 21 calendar days.
Creating a plan does not move the Data Date or recalculate tasks. Supported
durations are 7 through 42 days. The inclusive window end is:

```text
anchor_date + window_days - 1
```

Weekly periods are consecutive seven-day ranges. A task is assigned once to
the week containing its current forecast start. A spanning task keeps both
forecast dates and a continuation label but is not duplicated. Incomplete
work before the anchor appears once in the dedicated Carryover / Overdue
section. Manual out-of-window work appears once in a separate manual section.

## Inclusion Rules

Executable leaf tasks are automatically included when they overlap the
window, are in progress at the anchor, or are incomplete with a forecast
finish before the anchor. Milestones in the window are included. Summary
tasks, deleted tasks, completed tasks finished before the anchor, tasks wholly
after the window, and tasks explicitly excluded from the plan do not enter
executable counts.

Manual inclusion overrides the date predicate without changing task dates.
Manual exclusion removes an automatically included item without changing the
schedule. The flags cannot both be true. An out-of-window metadata update is
rejected until manual inclusion is explicit. All overrides remain scoped to
one plan.

Because plans are live, schedule date, Data Date, and progress changes are
reflected when detail is loaded again. A plan's anchor remains the date chosen
at creation; a changed project Data Date becomes the default for newly created
plans. Archived plans retain metadata but still show current task facts or an
unavailable-task marker. Use a baseline when immutable dates are required.

## Readiness and Blockers

Readiness is separate from schedule progress and uses:

- `unreviewed`
- `ready`
- `at_risk`
- `blocked`
- `committed`
- `complete`

Setting look-ahead readiness to `complete` does not complete the schedule
task. Commitments use the `committed` readiness state plus an optional bounded
note and server-controlled updater/timestamp; M17.5 does not retain commitment
revision history.

Short-term blocker categories are `predecessor_work`, `design_information`,
`submittal`, `material`, `labor`, `equipment`, `access`, `inspection`,
`permit`, `owner_decision`, `safety`, `weather`, and `other`. Blocker metadata
does not create an M17.4 CPM constraint or another construction record.

Responsible company is an optional `ProjectCompany` reference. The server
verifies that the company belongs to the same project and returns only its
safe ID, name, and trade summary. A missing assignment remains valid.

## Detail Response

Plan detail contains the plan header, current Data Date, window end, weekly
groups, carryover items, manual items, excluded items, and summary metrics.
Derived attention states include overdue, blocked, constraint due, commitment
missing, critical, out of sequence, milestone, unscheduled, and multiweek
context. Clients cannot assign these fields.

Summary counts cover total, each week, carryover, manual, ready, at risk,
blocked, committed, overdue, critical, out of sequence, milestones,
constraints due, unassigned companies, and unscheduled work. Every available
leaf task is counted at most once.

## API

```text
POST /projects/{project_id}/look-ahead-plans
GET  /projects/{project_id}/look-ahead-plans
GET  /projects/{project_id}/look-ahead-plans/{plan_id}
PUT  /projects/{project_id}/look-ahead-plans/{plan_id}
POST /projects/{project_id}/look-ahead-plans/{plan_id}/archive
PUT  /projects/{project_id}/look-ahead-plans/{plan_id}/items/{task_id}
```

All routes authenticate, resolve `get_owned_project`, validate strict schemas,
and return safe missing/foreign behavior. Creation, plan update, archive, and
item update each commit atomically and roll back on validation or database
failure. Archived plans are read-only; there is no hard-delete endpoint.

No candidate endpoint is added. The scheduler already owns one bounded
canonical task collection, so manual inclusion searches that collection
locally. No PDF endpoint is added: the grouped view has print-specific CSS and
uses the browser print dialog. This avoids a second reporting implementation,
external resources, temporary files, and another server request.

## Frontend Workflow

The Schedule page retains one route with five modes: Current Schedule,
Baseline Comparison, Look-Ahead Planning, Resource Loading, and Schedule Summary.
`useLookAheadPlans` owns plan
listing, selection, detail loading, creation, archive, item updates, filters,
retry, AbortController cancellation, project/plan generation checks, and
mutation deduplication.

The planning view provides:

- a labeled plan selector, create, print, and archive controls;
- a summary strip and deterministic text/company/trade/status filters;
- Carryover / Overdue, weekly, manual, and excluded sections;
- factual task cards with WBS, dates, progress, schedule facts, readiness,
  blockers, commitments, textual attention labels, and batched crew/equipment
  assignment labels;
- a focus-managed metadata dialog; and
- reuse of the existing Progress, CPM Planning, and Resource Assignment
  dialogs.

Create and item dialogs validate date-only and bounded fields, trap focus,
close on Escape, and restore focus. Archived plans remain selectable and
printable but expose no edit controls. Project switching clears plan detail,
filters, dialogs, and pending state; late project or plan responses are
rejected.

## Performance

The detail service loads the plan, settings, tasks/dependencies, sparse item
metadata, and referenced companies in bounded query groups, then performs
in-memory inclusion and weekly grouping. A local SQLite/TestClient probe on
August 4, 2026 measured:

| Tasks | SELECTs | Detail | Response | Metadata update plus refresh |
|---:|---:|---:|---:|---:|
| 100 | 7 | 16.48 ms | 88,110 bytes | 18.63 ms |
| 500 | 7 | 37.09 ms | 438,526 bytes | 41.44 ms |
| 2,000 | 10 | 163.52 ms | 1,756,534 bytes | 152.89 ms |

M17.7 narrows the approved item response to fields used by the UI while
preserving each task exactly once across deterministic groups. A repeat
2,000-task probe measured 7 SELECTs, 144.97 ms, and 1,403,629 bytes. This is
about 20% smaller but remains above the aspirational 1 MB target; adding
server pagination would require coordinated client-side filtering/grouping
changes and is deferred rather than silently changing this live contract.

The 2,000-task query increase comes from bounded select-in batches, not one
query per task. These figures are local regression evidence, not PostgreSQL,
network, print, or browser-render latency. Browser usability at 2,000 tasks is
not claimed. Print export has no backend query or export-generation time.

M17.6 adds one batched assignment query and bounded crew/equipment resolution
for assignment labels. It does not fetch one resource per item or calculate
the Resource Loading matrix inside look-ahead detail.

## Migration and Security

Alembic revision `e6b4c9a2d715` follows `d4e8a1c7f925`, creates the two tables,
constraints, indexes, and foreign keys, and performs no plan backfill or task,
baseline, or dependency mutation. Project deletion cascades plans and items;
plan deletion cascades items at the database boundary, although no public
hard-delete route exists. Company deletion sets the optional item reference to
null. Upgrade, downgrade, re-upgrade, one-head, and metadata-check paths are
covered on SQLite and verified against the local PostgreSQL database.

Strict request models reject ownership, creator/updater, schedule, progress,
derived metric, and unknown fields. Task, plan, and company identity are
resolved within the owned project. Server-controlled audit fields are never
accepted from clients.

## Boundaries

M17.5 intentionally has no schedule snapshot, historical commitment audit,
activation/publish state, hard delete, dashboard collection request, server PDF,
task fan-out, automatic construction-record links, notifications, resource or
crew conflict metric, cost or earned-value logic, configurable calendars, or offline
workflow. Responsive browser checks at 320, 375, 768, and 1024 pixels, wide
desktop, and 200% zoom remain manual release verification where no browser
session is available.

M17.6 resource assignments remain live metadata. Look-ahead shows their labels
and opens the shared assignment workflow, while loading, capacity overrides,
and conflict calculations stay in the separate Resource Loading mode.
