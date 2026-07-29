# Project Dashboard and Analytics

## Overview

The Project Dashboard is the first project-scoped view in FieldFlow. It gives
project teams a bounded summary of schedule dates, construction workflows,
daily logs, documents, items requiring attention, upcoming work, and recent
record updates without loading each resource collection in the browser.

The dashboard is informational. It does not calculate percent complete,
critical path, total float, or a synthetic project-health score because the
aggregate contract does not provide enough data to make those claims.

## Architecture

The dashboard route remains lazy-loaded through `AppRouter`.

```text
ProjectDashboardPage
|-- DashboardHeader
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
  starts include tasks from `as_of` through seven days after it.
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
collections. There is no dashboard polling, hover prefetch, or background
refresh.

## Testing

The frontend suite currently passes 275 tests across 42 files. Dashboard
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

The backend suite currently passes 136 primary tests, with 71 separately
reported subtests. `test_dashboard_api.py` covers authentication, ownership,
query validation, aggregate definitions, bounded ordering, aware timestamps,
legacy statuses, and query behavior.

## Performance

Production builds were measured directly at each M14 commit with the same
installed Vite toolchain:

| Phase | Dashboard raw/gzip | Main raw/gzip | CSS raw/gzip |
|---|---:|---:|---:|
| M14.1 | 19.24 / 5.25 kB | 265.43 / 81.95 kB | 41.32 / 8.78 kB |
| M14.2 | 8.03 / 2.60 kB | 263.98 / 81.45 kB | 36.47 / 8.01 kB |
| M14.3 | 13.23 / 3.79 kB | 264.10 / 81.49 kB | 38.77 / 8.30 kB |
| M14.4 | 20.15 / 4.97 kB | 264.10 / 81.48 kB | 42.18 / 8.68 kB |
| M14.5 | 21.06 / 5.22 kB | 264.10 / 81.50 kB | 41.21 / 8.61 kB |

M14.2 replaced the previous client-derived dashboard and removed obsolete
dashboard utilities. M14.3 added action lists, M14.4 added workflow analytics
and recent updates, and M14.5 added accessibility and request hardening while
removing duplicate CSS. The final dashboard remains below the 5.25 kB gzip
budget, the main bundle remains below the M14.1 baseline, and CSS remains
below the M14.1 baseline.

No chart or date dependency was added, no duplicate shared utility chunk is
emitted, and the dashboard remains route-level lazy-loaded.

## Release Verification

Final automated verification:

| Check | Result |
|---|---|
| Frontend tests | Pass: 275 tests across 42 files |
| ESLint | Pass: no errors or warnings |
| Production build | Pass: 99 modules transformed |
| Dashboard bundle budget | Pass: 5.22 kB gzip against a 5.25 kB limit |
| Aggregate request count | Pass: one dashboard request |
| Resource and attachment requests | Pass: zero on dashboard load |
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
