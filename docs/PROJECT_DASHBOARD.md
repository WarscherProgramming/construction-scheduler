# Project Dashboard and Analytics

## Overview

The Project Dashboard is the first project-scoped view in FieldFlow. It gives
project teams a bounded summary of schedule dates and explainable health, construction workflows,
daily logs, documents, items requiring attention, upcoming work, and recent
record updates without loading each resource collection in the browser.

The dashboard is informational. M17.7 adds named schedule-health metrics and
an explainable stable/attention/critical category, but no synthetic score,
hidden weight, task collection, percent-complete KPI, or full critical-path
list. Baseline and Data Date context come from the same aggregate; detailed
variance and progress remain Schedule-route concerns.

## Architecture

The dashboard route remains lazy-loaded through `AppRouter`.

```text
ProjectDashboardPage
|-- DashboardHeader
|-- ScheduleHealthCard
|-- DashboardSummaryGrid
|-- DashboardActionGrid
|   |-- AttentionRequired
|   `-- UpcomingSchedule
`-- DashboardInsightsGrid
    |-- WorkflowAnalytics
    `-- RecentUpdates
```

Data flows through one project-specific path:

```text
AppRouter
  -> ProjectDashboardPage
  -> useProjectDashboard
  -> fetchProjectDashboard
  -> GET /projects/{project_id}/dashboard?as_of=YYYY-MM-DD
  -> routes_dashboard.get_dashboard
  -> dashboard.get_project_dashboard
  -> SQLAlchemy aggregate queries
  -> DashboardResponse
  -> summary, action, workflow, and recent-update components
```

`ProjectDashboardPage` owns page-state selection: no project, loading, error,
or loaded dashboard. Formatting and defensive numeric handling live in
`dashboardSummary.js`; presentation components do not recalculate backend
aggregates.

## Aggregate API

### Request

```http
GET /projects/{project_id}/dashboard?as_of=YYYY-MM-DD
Authorization: Bearer <token>
```

Purpose:

- Return one project-owned aggregate snapshot for the requested calendar date.
- Replace dashboard-specific resource collection loading.
- Keep attention, upcoming, document, and recent-update lists bounded.

Parameters:

| Parameter | Location | Required | Contract |
|---|---|---:|---|
| `project_id` | Path | Yes | Integer project identifier |
| `as_of` | Query | Yes | Valid date-only string in `YYYY-MM-DD` format |

Authentication and ownership:

- A valid JWT is required.
- `get_owned_project` requires the project to belong to the authenticated user.
- Missing or inaccessible projects return `403`.

Validation and errors:

- Missing, malformed, timestamp-shaped, or impossible `as_of` values return
  `422`.
- Unauthenticated requests return `401`.
- Internal failures use the existing FastAPI error handling contract.

### Response

Top-level fields:

| Field | Type | Purpose |
|---|---|---|
| `as_of` | date | Requested dashboard date |
| `generated_at` | aware datetime | UTC-aware generation timestamp |
| `project` | object | `id`, `name` |
| `schedule` | object | Schedule date and task counts |
| `schedule_health` | object | Explainable category, reasons, metrics, baseline/Data Date, executive summary, and bounded attention |
| `rfis` | object | RFI workflow counts |
| `submittals` | object | Submittal workflow counts |
| `punch_items` | object | Punch Item workflow counts |
| `change_orders` | object | Change Order counts and monetary totals |
| `daily_logs` | object | Daily Log counts and manpower |
| `documents` | object | Document counts and recent metadata |
| `attention_items` | array | Bounded action list |
| `upcoming_tasks` | array | Bounded upcoming schedule list |
| `recent_updates` | array | Bounded cross-workflow update list |

Summary fields:

| Section | Fields |
|---|---|
| `schedule` | `task_count`, `planned_start`, `planned_finish`, `past_planned_finish_count`, `upcoming_start_count` |
| `rfis` | `total`, `open`, `overdue`, `due_soon` |
| `submittals` | `total`, `pending`, `overdue`, `due_soon` |
| `punch_items` | `total`, `open`, `overdue`, `completed_last_7_days` |
| `change_orders` | `total`, `active`, `approved`, `rejected`, `unknown_status`, `active_value`, `approved_value` |
| `daily_logs` | `total`, `latest_log_date`, `today_count`, `today_manpower`, `last_7_days_count` |
| `documents` | `total`, `uploaded_last_7_days`, `recent` |
| `schedule_health` | `category`, `summary`, `reasons`, `metrics`, `thresholds`, `baseline`, `data_date`, `schedule_start_date`, `executive_summary`, `top_attention_items` |

`change_orders.active_value` and `change_orders.approved_value` are
fixed-precision decimal strings. The frontend formats them as USD without
performing monetary aggregation.

Bounded collections:

| Collection | Limit | Item fields |
|---|---:|---|
| `attention_items` | 10 | `resource_type`, `record_id`, `identifier`, `title`, `due_date`, `reason`, `severity`, `target_page` |
| `upcoming_tasks` | 8 | `id`, `name`, `start_date`, `end_date`, `duration` |
| `documents.recent` | 8 | `id`, `parent_type`, `parent_id`, `filename`, `file_size`, `created_at` |
| `recent_updates` | 8 | `resource_type`, `record_id`, `identifier`, `description`, `updated_at`, `target_page` |

Text selected for attention and recent updates is bounded to 500 characters
by the service.

### Metric Rules

- Schedule: past planned finish counts tasks ending before `as_of`; upcoming
  starts include tasks from `as_of` through seven days after it. These metrics
  continue to include summary rows and read dates persisted by deterministic
  recalculation against the project's Schedule Start Date.
- RFIs: Open and Pending are open; overdue and due-soon counts use `due_date`.
- Submittals: Draft, Submitted, and Under Review are pending; date counts use
  `required_by_date`.
- Punch Items: Open and In Progress are open; Completed and Verified can count
  toward `completed_last_7_days`.
- Change Orders: Draft, Pending, Submitted, and Under Review are active;
  Approved and Executed are approved; Rejected and Void are rejected.
  Nonstandard statuses are counted in `unknown_status`.
- Daily Logs: today and trailing-seven-day counts use the requested date.
- Documents: trailing-seven-day counts use UTC boundaries derived from
  `as_of`.
- Schedule Health: uses the persisted project Data Date and selected active
  baseline; critical/attention rules and caps are documented in
  [`ADVANCED_SCHEDULING.md`](ADVANCED_SCHEDULING.md).
- Attention Required combines overdue RFIs, Submittals, and Punch Items with
  schedule tasks past planned finish.
- Recent Updates combines RFIs, Submittals, Punch Items, Change Orders, and
  attachments in descending update order.

## Request Lifecycle

`useProjectDashboard` generates `as_of` from the browser's local calendar and
does not request data without a selected project.

For each project/date identity it:

1. Clears previous dashboard data before loading.
2. Suppresses duplicate in-flight requests during React Strict Mode replay.
3. Uses `AbortController` when a request is superseded or the component
   unmounts.
4. Requires both the current identity and current request record before
   accepting a success or failure.
5. Ignores stale successes, stale failures, and intentional abort errors.
6. Clears settled request records so retry always starts a fresh request.

An A-to-B-to-A project switch cannot allow the first A request to replace the
newer A lifecycle. Retry affects only the dashboard and does not reload the
application bootstrap.

## Rendering States

- No project: a factual selection prompt.
- Loading: one announced status and non-interactive, assistive-technology
  hidden skeletons that approximate the final layout.
- Error: no zero-value substitutes; one safe error message and a keyboard
  accessible retry button.
- Empty data: section-specific factual wording without health claims.
- Loaded data: summary metrics, attention and upcoming lists, workflow
  analytics, and recent updates.

The existing application feedback banner also receives dashboard request
failures. Aborted and stale request failures remain silent.

## Accessibility and Responsive Behavior

- The page has one `h1`, section `h2` headings, and item/card `h3` headings.
- Sections are named with native headings and `aria-labelledby`.
- Attention, upcoming, workflow, and recent-update groups use semantic lists.
- Links retain concise visible labels and add bounded contextual accessible
  names where repeated labels would otherwise be ambiguous.
- Status and severity remain visible as text and are not communicated only by
  color.
- Dates and timestamps use semantic `time` elements.
- Retry and navigation controls use native buttons and links.
- Empty dashboard subsections avoid unnecessary live-region announcements.
- Skeleton animation is disabled when reduced motion is requested.

The summary grid, action grid, insights grid, and nested workflow grid use
`minmax(0, 1fr)`, wrapping, and `min-width: 0` to prevent content-driven
overflow. The layout reduces summary columns below 1100px, stacks action and
insight sections below 760px, and stacks summary and workflow cards below
620px. Long project names, identifiers, descriptions, timestamps, and
currency values wrap rather than relying on fixed heights.

These practices are tested and manually reviewed, but are not presented as a
formal WCAG certification.

## Routing and Request Map

Dashboard links use existing project hash routes and do not add query strings,
anchors, or record deep links. A fresh authenticated dashboard load performs:

```text
GET /projects
GET /templates
GET /projects/{project_id}/dashboard?as_of=YYYY-MM-DD
```

The first two requests are application bootstrap. The dashboard adds exactly
one aggregate request and does not request task, company, Daily Log,
inspection, delay, Change Order, RFI, Submittal, Punch Item, or attachment
collections. It also makes no Document Explorer, drawing, relationship-list,
or relationship-candidate request. There is no dashboard polling, hover
prefetch, or background refresh. M16.7 reconfirms that extraction status,
reprocess, project content search, and every other M16 workflow remain absent
from dashboard loading. M17.5 likewise adds no look-ahead plan list, detail,
candidate, metadata, or print request to dashboard loading.
M17.6 adds no crew, equipment, assignment, availability, or resource-loading
request or metric. Resource planning remains isolated to the lazy Schedule
route, preserving the single aggregate dashboard request.
M17.7 computes `schedule_health` inside that aggregate. It returns only
bounded metrics, reasons, baseline/Data Date context, executive summary, and
attention items; it does not call the health HTTP route or load underlying
collections. Query count is exactly 23 for empty, mixed, and large fixtures.

## Testing

The frontend suite currently passes 567 tests across 86 files. Dashboard
coverage includes:

- API URL and required `as_of` behavior
- no-project, loading, loaded, empty, and failure states
- retry and global feedback
- aggregate request counts and absence of collection requests
- Strict Mode request deduplication
- project switching, aborts, stale success, stale failure, and A-to-B-to-A
  switching
- local dates, aware timestamps, invalid values, counts, currency, and
  proportional-width clamping
- headings, semantic roles, contextual link names, keyboard focus, and routes
- Attention Required, Upcoming Schedule, Workflow Analytics, and Recent
  Updates rendering
- explainable Schedule Health rendering, textual state, and Scheduler link

The backend suite currently passes 404 primary tests, with 407 subtests
reported separately. `test_dashboard_api.py` covers authentication, ownership,
query validation, aggregate definitions, bounded ordering, aware timestamps,
legacy statuses, and query behavior.

## Performance

Production builds were measured directly at each M14 commit and again through
M17.6 with the installed Vite toolchain:

| Phase | Dashboard raw/gzip | Main raw/gzip | CSS raw/gzip |
|---|---:|---:|---:|
| M14.1 | 19.24 / 5.25 kB | 265.43 / 81.95 kB | 41.32 / 8.78 kB |
| M14.2 | 8.03 / 2.60 kB | 263.98 / 81.45 kB | 36.47 / 8.01 kB |
| M14.3 | 13.23 / 3.79 kB | 264.10 / 81.49 kB | 38.77 / 8.30 kB |
| M14.4 | 20.15 / 4.97 kB | 264.10 / 81.48 kB | 42.18 / 8.68 kB |
| M14.5 | 21.06 / 5.22 kB | 264.10 / 81.50 kB | 41.21 / 8.61 kB |
| M16.5 | 21.07 / 5.24 kB | 277.10 / 84.89 kB | 69.36 / 12.90 kB |
| M16.6 | 21.07 / 5.23 kB | 278.29 / 85.15 kB | 74.45 / 13.53 kB |
| M16.7 | 21.07 / 5.23 kB | 278.29 / 85.15 kB | 74.45 / 13.53 kB |
| M17.1 | 21.07 / 5.23 kB | 280.82 / 85.81 kB | 74.79 / 13.55 kB |
| M17.2 | 21.07 / 5.23 kB | 288.19 / 87.65 kB | 80.91 / 14.36 kB |
| M17.3 | 21.07 / 5.23 kB | 289.84 / 88.09 kB | 85.97 / 15.04 kB |
| M17.4 | 21.07 / 5.23 kB | 291.27 / 88.49 kB | 88.81 / 15.59 kB |
| M17.5 | 21.07 / 5.23 kB | 297.51 / 89.63 kB | 94.69 / 16.44 kB |
| M17.6 | 21.07 / 5.23 kB | 305.88 / 91.26 kB | 98.96 / 17.14 kB |
| M17.7 | 22.54 / 5.58 kB | 306.85 / 91.41 kB | 100.95 / 17.48 kB |

M14.2 replaced the previous client-derived dashboard and removed obsolete
dashboard utilities. M14.3 added action lists, M14.4 added workflow analytics
and recent updates, and M14.5 added accessibility and request hardening while
removing duplicate CSS. At M14 closeout the main and CSS bundles remained
below the M14.1 baselines. The M16.5 build still keeps the dashboard below its
5.25 kB gzip budget; later document and drawing features account for the
application-wide main and CSS growth. M16.6 keeps the dashboard unchanged
and lazy, with no extraction or search request; its document-search UI is a
separate 9.91 kB raw / 2.84 kB gzip route chunk.
M16.7 is documentation and release verification only, so no dashboard, main,
CSS, or document route chunk changes.
M17.1 keeps the dashboard chunk and request contract unchanged. Its persistent
schedule-settings resource and stale-mutation safeguards add 2.53 kB raw /
0.66 kB gzip to main and 0.34 / 0.02 kB to CSS versus M16.7. The lazy
Scheduler route is 62.66 kB raw / 20.07 kB gzip.
M17.2 also leaves the dashboard chunk and one-request contract unchanged.
Focused baseline state loads only on the Schedule route; the table-first
comparison raises the lazy Scheduler chunk to 79.45 kB raw / 23.90 kB gzip.
M17.3 also leaves the dashboard request and presentation unchanged. Progress,
Data Date, and status-aware Gantt work remain in the lazy Scheduler route.
That route is 93.81 kB raw / 26.85 kB gzip, up 14.36 / 2.95 kB from M17.2.
Main grows 1.65 / 0.44 kB and CSS grows 5.06 / 0.68 kB; the Dashboard chunk
does not change.
M17.4 again leaves the dashboard chunk, metrics, and one-request contract
unchanged. Milestone, constraint, dependency, and Gantt enhancements remain
inside the lazy Schedule route. That route is 105.53 kB raw / 29.61 kB gzip;
main grows 1.43 / 0.40 kB and CSS grows 2.84 / 0.55 kB from M17.3.
M17.5 also leaves the dashboard chunk, metrics, and one-request contract
unchanged. Look-ahead plans load only on the lazy Schedule route; no plan list,
detail, task-candidate, or per-item request is made by the dashboard. The lazy
Scheduler chunk is 129.92 kB raw / 34.56 kB gzip. Main grows 6.24 / 1.14 kB
and CSS grows 5.88 / 0.85 kB from M17.4.

M17.6 preserves that dashboard boundary. Crew, equipment, assignment,
availability, and loading requests occur only on the lazy Schedule route; the
project health formula and aggregate contract remain unchanged. The lazy
Scheduler chunk is 153.73 kB raw / 39.35 kB gzip; main grows 8.37 / 1.63 kB
and CSS grows 4.27 / 0.70 kB from M17.5, while Dashboard is unchanged.

M17.7 adds the bounded Schedule Health card to the existing aggregate and a
fifth summary mode to the lazy Scheduler route. Dashboard grows 1.47 / 0.35
kB, main grows 0.97 / 0.15 kB, CSS grows 1.99 / 0.34 kB, and Scheduler is
159.65 / 40.97 kB. No dashboard request fan-out is introduced.

No chart or date dependency was added, no duplicate shared utility chunk is
emitted, and the dashboard remains route-level lazy-loaded. M16.5 adds no
relationship request to dashboard loading.

## Release Verification

Final automated verification:

| Check | Result |
|---|---|
| Frontend tests | Pass: 567 tests across 86 files |
| ESLint | Pass: no errors or warnings |
| Production build | Pass: 159 modules transformed |
| Dashboard bundle | 22.54 kB raw / 5.58 kB gzip; the intentional health card exceeds the historical 5.25 kB gzip budget by 0.33 kB |
| Aggregate request count | Pass: one dashboard request |
| Resource, attachment, relationship, extraction, and search requests | Pass: zero on dashboard load |
| Semantic DOM and keyboard tests | Pass |

Bounded browser verification was attempted on July 28, 2026 with the installed
Chrome and Edge binaries against a temporary Vite server. Both browsers
terminated in the Chromium GPU process before rendering a page, including a
retry with GPU, software rasterizer, Skia renderer, and Vulkan features
disabled. The temporary server and browser profiles were removed afterward.
This is a verification-environment failure, not an observed application
failure.

Browser matrix:

| Check | Result |
|---|---|
| Chrome/Edge page startup | Fail: browser process terminated before render |
| 320px, 375px, 768px | Not Verified |
| 1024px, 1280px, 1600px | Not Verified |
| 200% browser zoom | Not Verified |
| Horizontal scrolling and visual overlap | Not Verified |
| Visible focus and focus clipping | Not Verified |
| Browser Back | Not Verified |
| Retry and project switching in a real browser | Not Verified |
| Loading, empty, and error visuals | Not Verified |
| Workflow Analytics and Recent Updates visuals | Not Verified |
| Browser console errors and warnings | Not Verified |

The same states, navigation paths, request counts, stale-response cases,
heading hierarchy, accessible names, and keyboard reachability pass
deterministic Vitest and React Testing Library coverage. Before merge, the
remaining manual task is a bounded visual pass in a working browser
environment at the listed viewports and 200% zoom.

## Deferred Work

The following work is intentionally outside M14:

- historical trends, charts, exports, notifications, and background refresh
- project timezone settings; `as_of` currently follows the browser's local
  calendar
- critical-path and total-float presentation, which are not returned by the
  aggregate schema
- project health scoring or percent-complete claims
- record-level dashboard deep links
- audit history and portfolio-level analytics

These are future possibilities, not committed scope.
