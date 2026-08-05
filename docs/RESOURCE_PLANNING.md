# Resource Planning

M17.6 adds project-owned crews, equipment, task assignments, dated capacity,
and bounded resource loading to FieldFlow's canonical live schedule. It does
not create a second schedule, change task dates, or perform resource leveling.

## Architecture

```text
Task forecast working dates
  -> TaskResourceAssignment
  -> Crew or EquipmentResource
  -> default capacity plus dated ResourceAvailability
  -> bounded daily loading, utilization, and conflict response
```

The backend follows the existing router -> service -> model/schema structure.
`resource_resolver.py` is an explicit allowlist for the two supported resource
types; it is not a generic CRUD framework. The frontend keeps the canonical
task collection in `SchedulerPage`, loads project resources through
`useProjectResources`, and loads the matrix only while the Resource Loading
mode is mounted through `useResourceLoading`.

## Resource Types

`Crew` is a named labor team with a positive default capacity measured in
workers. It may reference an existing project company, but companies remain
identity and responsibility records rather than a third assignable resource
model. No employee or payroll information is stored.

`EquipmentResource` is a named asset or equipment category with a positive
whole-unit default capacity. An optional identifier distinguishes named
equipment. FieldFlow does not track dispatch, telemetry, maintenance, or cost.

Both resource types are project-owned and use `active` or `archived` status.
Archive preserves historical assignments and availability. Archived resources
cannot receive new assignments, and their capacity records are read-only.

## Assignments

`TaskResourceAssignment` connects one leaf, non-milestone task to exactly one
crew or equipment resource in the same project. Allocation is a positive whole
number:

- crew allocation means workers required on each active task workday;
- equipment allocation means equipment units required on each active workday.

Logical duplicates are rejected. Assignment mutations never accept or alter
task dates, duration, progress, hierarchy, dependencies, or constraints. Task
deletion removes its assignment rows; resource archive retains them.

## Availability

Each resource begins with its default capacity. `ResourceAvailability`
overrides that capacity for an inclusive local `YYYY-MM-DD` range. Capacity
must be a nonnegative whole number, so zero explicitly marks a resource
unavailable. Overlapping overrides for the same resource are rejected.

The service validates project ownership, resource type, date ordering, and
overlap in one transaction. It locks the resource row where the database
supports row locking so concurrent writes serialize before overlap checking.
Availability list responses are bounded and paginated.

## Loading Calculation

The loading endpoint accepts an inclusive date window of at most 90 days. Its
default is the project Data Date through 20 days later. It batches settings,
tasks, assignments, resources, availability, and optional companies, then
expands demand in memory only over existing project workdays.

Demand uses the current forecast after dependencies, constraints, milestones,
progress, and Data Date have already been applied:

- not-started tasks use their current forecast start and finish;
- in-progress tasks begin no earlier than the Data Date and use their current
  remaining forecast;
- completed tasks, milestones, summary tasks, and unscheduled tasks add no
  demand.

Daily demand is the sum of assignment allocations. Daily capacity is the
applicable dated override or the resource default. Utilization is demand
divided by capacity when capacity is positive. Demand above capacity is
over-allocated; positive demand against zero capacity is unavailable and also
a conflict. Under-allocation is reported factually and is not treated as an
error. Conflict details include contributing tasks without changing schedule
logic.

Unassigned work is reported separately for eligible scheduled leaf tasks.
Filters support resource type, company, trade, conflict-only display, and
whether unassigned work is included. Resource and unassigned collections use
stable ordering and bounded pagination.

## API

All routes require authentication and reuse project ownership enforcement.
Client payloads forbid unknown and server-controlled fields.

- `/projects/{project_id}/crews`: create and list crews.
- `/projects/{project_id}/crews/{crew_id}`: detail and update.
- `/projects/{project_id}/crews/{crew_id}/archive`: archive.
- `/projects/{project_id}/equipment-resources`: create and list equipment.
- `/projects/{project_id}/equipment-resources/{equipment_id}`: detail and update.
- `/projects/{project_id}/equipment-resources/{equipment_id}/archive`: archive.
- `/projects/{project_id}/tasks/{task_id}/resource-assignments`: list and
  create assignments.
- `/projects/{project_id}/tasks/{task_id}/resource-assignments/{assignment_id}`:
  update allocation or delete.
- `/projects/{project_id}/resources/{resource_type}/{resource_id}/availability`:
  list and create overrides.
- `/projects/{project_id}/resources/{resource_type}/{resource_id}/availability/{availability_id}`:
  update or delete an override.
- `/projects/{project_id}/resource-loading`: return the bounded loading view.

The two-type resolver prevents arbitrary model access. Every nested ID is
resolved within the owned project, cross-project task/resource/company links
are rejected, archived resources cannot be newly assigned, and foreign names
are never exposed through conflict responses.

## Frontend Workflow

Resource Loading is the fourth mode on the existing lazy Schedule route.
Internal Loading, Crews, and Equipment tabs provide:

- crew and equipment create, edit, and archive workflows;
- inclusive availability overrides;
- date, type, company, trade, conflict, and unassigned filters;
- textual demand, capacity, utilization, and conflict summaries;
- a bounded date matrix, unassigned task list, local retry, and browser print.

Current Schedule task rows open a focus-managed assignment dialog. Look-Ahead
items display assignment labels from batched detail data and open the same
workflow. No page fetches one resource per task, and assignment changes do not
request schedule recalculation.

Hooks use AbortController, request identity, project generation checks, and
mutation deduplication. Project switches close dialogs, clear selected
resources and loading output, and reject late success or failure responses.
Loading failures remain local to Resource Loading while existing global
feedback remains available for mutations and session behavior.

## Boundaries

- Baselines remain immutable schedule snapshots and do not contain resource
  assignments or loading. Resource comparisons are current-only.
- Templates remain planning structure and never copy project-specific resource
  IDs. Assignments are added after template application.
- Daily Log manpower remains historical actual reporting. M17.6 does not infer
  actual usage or progress from planned resource demand.
- Dependencies and constraints determine task forecasts before loading; a
  resource conflict never becomes a CPM constraint.
- The dashboard adds no resource-loading request. M17.7 derives bounded
  conflict counts inside the shared health service and preserves its single
  aggregate request.
- Reporting uses the browser's print flow. No backend resource PDF endpoint is
  added.

## Database

Alembic revision `f7c5d0b3e826` follows `e6b4c9a2d715` and creates `crews`,
`equipment_resources`, `task_resource_assignments`, and
`resource_availability`. It performs no backfill and does not mutate tasks,
baselines, templates, or look-ahead plans.

Checks enforce status values, positive default capacities and allocations,
nonnegative override capacity, ordered dates, and exactly one typed resource
reference. Unique constraints protect project-scoped resource names,
equipment identifiers, and logical task assignments. Composite indexes cover
project/status/name lists, task and resource assignment lookups, and resource
availability range reads. Foreign keys cascade project and task cleanup while
resource records remain archived for history.

## Accessibility and Responsive Behavior

The UI uses semantic headings, tables and lists, explicit form labels, textual
demand/capacity/utilization, and written conflict reasons rather than color
alone. Dialogs are labeled, trap and restore focus, close with Escape, and use
explicit archive confirmation. Compact cards preserve loading and conflict
context on narrow screens; the matrix is the only intentionally scrollable
region. Print output remains textual.

Automated coverage exercises keyboard-visible controls and responsive
structure. Manual browser checks at 320, 375, 768, and 1024 pixels, wide
desktop, and 200% zoom remain release verification.

## Performance and Limits

The endpoint batches database reads and performs bounded in-memory expansion;
it does not query per task, assignment, company, resource, or day. The 90-day
cap and pagination bound response growth. Look-Ahead adds only batched
assignment/resource enrichment, not item-level fan-out.

M17.7 removes repeated task-contribution arrays from every daily cell, caps
serialized conflicts at 100 and contributing tasks per conflict at 5, and
returns exact total/count/truncation metadata. Summary counts are calculated
before caps. A local SQLite/TestClient probe on August 5, 2026 used a 21-day
window with 2,000 tasks and 200 crews:

| Tasks / resources | SELECTs | Response | Serialized conflicts | Exact conflict days |
|---:|---:|---:|---:|---:|
| 2,000 / 200 | 9 | 277.74 ms / 749,881 bytes | 100 | 3,000 |

The prior M17.6 response was 10,343,686 bytes. The query count remains bounded
ORM loading, not task or resource fan-out. These are local measurements, not
PostgreSQL, network, production latency, print, or browser-usability claims.

M17.6 intentionally excludes automatic leveling or rescheduling, cost and
earned-value loading, workforce management, individual employees, timecards,
dispatching, equipment telemetry, configurable calendars, shift scheduling,
resource baselines, planned-versus-actual manpower analytics, automatic
dashboard resource collections, server PDF export, and offline resource
workflows. M17.7 health exposes only aggregate conflict metrics.

The M17.7 production build emits the combined lazy Scheduler chunk at 159.65
kB raw / 40.97 kB gzip. Main is 306.85 / 91.41 kB, CSS is 100.95 / 17.48 kB,
and Dashboard is 22.54 / 5.58 kB.
