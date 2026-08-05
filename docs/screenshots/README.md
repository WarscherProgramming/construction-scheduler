# Screenshot capture checklist

The root README references the primary captures below. Use these exact names
for both referenced and planned module screenshots.

## Setup (all captures)

- Load the live app (or `npm run dev`) in a clean browser window, **~1440×900**
  viewport, 100% zoom, light theme.
- Sign in and use the seeded demo project **Riverside Medical Center —
  Phase 2** (First-run → "Load Sample Project") so every view has data.
- Prefer PNG for stills; GIFs ≤ 8 seconds, ≤ 5 MB (record with e.g. ScreenToGif
  or Kap).
- Use synthetic project, company, user, and filenames. Never capture
  credentials, tokens, private endpoints, bucket names, or real customer
  documents.

## Manifest

| File | View / state to capture |
|---|---|
| `dashboard.png` | Populated Project Dashboard showing textual Schedule Health with baseline/Data Date context, Project Summary, Follow-up Indicators, Attention Required, Upcoming Schedule, Workflow Analytics, and Recent Updates. Include readable RFI, Submittal, Punch Item, and Change Order states plus large Change Order values where practical. |
| `schedule-grid.png` | Schedule table view: visible Schedule Start Date and Data Date, leaf-task status and percent complete, remaining duration, actual dates, one milestone, one explicit constraint, multiple predecessor labels, one visible out-of-sequence reason, a selected row, and at least one parent task with indented children. |
| `schedule-settings.png` | Schedule sidebar with independent persisted Schedule Start Date and Data Date controls and the accessible Data Date recalculation confirmation open over synthetic task data. |
| `schedule-baseline-create.png` | Accessible Capture Schedule Baseline dialog showing a synthetic name, optional description, Schedule Start Date, task count, server-generated timestamp note, and immutable-snapshot explanation. |
| `schedule-baseline-comparison.png` | Baseline Comparison view with a selected named baseline, capture time, project-finish direction, slipped/improved/added/removed/newly-critical metrics, filters, and readable current-versus-baseline task rows. |
| `schedule-baseline-mobile.png` | Baseline Comparison at ~390 px with the selector, textual summary metrics, filters, and one stacked task comparison record fully reachable without page-level horizontal overflow. |
| `look-ahead-create.png` | Focus-managed Create Look-Ahead Plan dialog with the project Data Date anchor and 21-day default visible over the factual no-plan state. |
| `look-ahead-planning.png` | Populated three-week Look-Ahead Planning view with summary metrics, filters, Carryover / Overdue, three weekly groups, and readable blocked and committed task states. |
| `look-ahead-item.png` | Look-Ahead Item dialog showing readiness, company/trade, blocker category/reason/owner/target, commitment, and manual override controls while schedule dates remain read-only. |
| `look-ahead-archived.png` | Selected archived Look-Ahead Plan with preserved metadata, factual task availability, and no edit controls. |
| `look-ahead-mobile.png` | Populated Look-Ahead Planning view at ~390 px with selector, summary, one weekly task card, long blocker text, and reachable actions without page-level overflow. |
| `look-ahead-print.png` | Browser print preview of a populated three-week plan with project/plan identity, date window, textual statuses, weekly groups, blockers, and commitments. |
| `resource-loading-empty.png` | Resource Loading mode before crews or equipment exist, with factual empty guidance and resource-management actions. |
| `resource-crews.png` | Populated Crews tab with synthetic names, trades, optional company associations, worker capacities, and active/archive actions. |
| `resource-equipment.png` | Populated Equipment tab with synthetic equipment types, identifiers, unit capacities, and active/archive actions. |
| `resource-availability.png` | Inclusive dated capacity override dialog with a synthetic zero-capacity unavailable period. |
| `task-resource-assignment.png` | Task Resource Assignment dialog showing one crew and one equipment allocation for a persisted leaf task. |
| `resource-loading.png` | Populated Resource Loading view with filters, date range, summary, textual demand/capacity/utilization, and the bounded matrix. |
| `resource-conflict.png` | Over-allocated resource with a written conflict reason and contributing task names visible. |
| `resource-unavailable.png` | Equipment demand against a zero-capacity override, labeled unavailable without relying on color. |
| `resource-unassigned.png` | Unassigned scheduled-work section with synthetic leaf tasks and dates. |
| `resource-loading-mobile.png` | Resource Loading at ~390 px with filters, one compact resource/conflict record, and reachable management actions. |
| `resource-loading-print.png` | Browser print preview with project, date range, demand, capacity, utilization, conflicts, and unassigned work in text. |
| `look-ahead-resources.png` | Populated look-ahead item/card with batched crew and equipment labels plus the accessible Assign Resources action. |
| `schedule-summary.png` | Fifth Scheduler mode with category text, baseline and Data Date context, executive metrics, at least two factual health reasons, top attention items, and both named PDF controls. |
| `schedule-summary-mobile.png` | Schedule Summary at ~390 px with wrapped mode controls, readable metrics/reasons, and reachable report actions without page-level overflow. |
| `schedule-executive-report.png` | Open synthetic executive schedule PDF showing project/schedule dates, health, baseline variance, progress, field-planning/resource summaries, and bounded attention without confidential data. |
| `dashboard-schedule-health.png` | Dashboard Schedule Health card showing textual category, reason context, finish variance, blockers, resource conflicts, and the Schedule link. |
| `schedule-dnd.gif` | ~5 s: grab a task's drag handle, drag it two rows, drop; dates recalculate. |
| `login.png` | Logged-out landing page at desktop width: split panel with marketing copy, highlights, app preview, and the auth card. |
| `gantt.png` | Schedule → Gantt view with textual progress, milestone diamonds, constraint markers, distinguishable FS/SS/FF/SF connectors with signed lead/lag labels, an in-progress bar, one completed task, out-of-sequence context, and the Data Date marker visible. |
| `first-run.gif` | ~6 s: first-run welcome screen → click "Load Sample Project" → progress bar filling → dashboard appears. Requires a fresh account. |
| `change-orders.png` | Populated Change Orders page: a generated `CO` number; create or edit workflow; proposed and approved amounts; schedule impact; lifecycle dates; multiple status badges; and, where practical, a readable legacy record. |
| `punch-lists.png` | Punch Lists page: populated Punch Items table with visible status and priority labels, an overdue indicator, and the create or edit workflow visible. |
| `drawing-register.png` | Populated Drawing Register with multiple disciplines, clear current revisions, set/filter controls, and sheet actions visible. |
| `drawing-set-workflow.png` | Drawing-set create or edit dialog with bounded fields, visible set context, and synthetic values. |
| `drawing-history.png` | Revision History dialog showing one current and one superseded PDF revision, dates, successor information, issue membership, and View/Download actions. |
| `drawing-issues.png` | Drawing Issues section with a draft issue containing revisions and an issued or void issue showing frozen membership. |
| `drawing-viewer.png` | Secure Drawing Viewer showing a synthetic multipage sheet, selected thumbnail, current or superseded revision text, metadata panel with Related Records open, page/zoom/search controls, and no confidential drawing content. |
| `drawing-viewer-mobile.png` | Secure Drawing Viewer at ~390 px with wrapped toolbar, reachable page/zoom controls, internal canvas scrolling, and visible revision identity. |
| `mobile.png` | Dashboard or a record page at ~390 px width: collapsed horizontal nav and stacked record cards. (Optional composite of two views side by side.) |

## Resource Planning captures

M17.6 does not create or replace image files. Use synthetic crews, equipment,
companies, task names, and capacities. Capture the empty state before seeding,
then the populated Loading, Crews, and Equipment states listed in the manifest.
The portfolio set should show one over-allocation, one unavailable date,
unassigned work, the task assignment dialog, a look-ahead item with batched
resource labels, mobile structure, and browser print. Do not imply employee
tracking, actual Daily Log manpower synchronization, resource leveling, cost
loading, or automatic task rescheduling.

## Document Management captures

These are required M16 portfolio captures. M16.7 does not create or replace
image files, and none of the M16 captures below was recorded during the
command-only closeout.

| File | Page / workflow | State to capture | Viewport | Avoid | Portfolio value |
|---|---|---|---|---|---|
| `project-documents.png` | Project Documents root | Populated root with folder tree, breadcrumbs, recent documents, multiple synthetic file types, extraction labels, and upload target visible | 1440×900 | Real project/client names and confidential filenames | Shows the project-level explorer and storage workflow |
| `project-documents-nested.png` | Project Documents nested folder | Two breadcrumb levels, active folder in the tree, child folder counts, and a populated nested listing | 1440×900 | Real folder names, stale root data, or provider paths | Demonstrates safe hierarchy and navigation |
| `document-details.png` | Project Document details | Safe metadata, download/delete actions, extraction status, reprocess state where appropriate, and Related Records collapsed or open | 1440×900 | Storage keys, bucket, checksum, credentials, raw errors, or extracted text | Shows the selected-record workflow without a new detail route |
| `daily-log-attachments.png` | Daily Logs | One persisted log expanded with photos and a PDF; create form remains separate | 1440×900 | Faces, addresses, subcontractor details, and location metadata | Connects field reporting to supporting evidence |
| `rfi-attachments.png` | RFIs | Selected persisted RFI with a drawing and response exhibit listed | 1440×900 | Proprietary drawings and real RFI content | Demonstrates contextual document access without a new detail route |
| `submittal-attachments.png` | Submittals | Selected Submittal with product data, PDF package, and download actions | 1440×900 | Manufacturer-confidential or project-specific packages | Shows mixed document formats in a review workflow |
| `punch-item-attachments.png` | Punch Items | Selected item with synthetic JPEG/PNG evidence and its browser preview opened | 1440×900 | Faces, geolocation, unit numbers, and real deficiency photos | Highlights image evidence and authenticated preview |
| `change-order-attachments.png` | Change Orders | Selected Change Order with cost backup and drawing exhibit alongside lifecycle data | 1440×900 | Real pricing, signatures, account data, and contract exhibits | Connects financial workflow records to supporting backup |
| `attachment-upload-results.png` | Any attachment-enabled workflow | Sequential multiple-file upload showing progress or a synthetic partial-success result | 1440×900 | Local filesystem paths and sensitive error details | Demonstrates resilient multi-file UX rather than an idealized happy path |
| `attachment-delete-confirmation.png` | Any attachment-enabled workflow | Filename-specific accessible confirmation dialog with the background panel visible | 1440×900 | Sensitive filenames or document contents | Shows deliberate destructive-action and focus-management design |
| `attachment-mobile.png` | RFI, Punch Item, or Daily Log attachments | One open panel with a long synthetic filename and wrapped actions | 390×844 | Notification previews, browser account UI, and real filenames | Proves the shared attachment workflow remains usable on site-sized screens |

## Relationship captures

M16.7 does not create or replace image files. Recapture these views with
explicit, synthetic links; do not imply automatic relationship discovery.

| File | Page / workflow | State to capture | Viewport | Avoid | Portfolio value |
|---|---|---|---|---|---|
| `record-relationships.png` | RFI, Submittal, Punch Item, Change Order, or Daily Log | One persisted record with its Related Records panel open; show forward and reverse wording, identifiers, statuses, and navigation actions | 1440x900 | Real record text, pricing, client names, and unavailable private records | Shows reusable cross-workflow context without row-level request fan-out |
| `drawing-relationships.png` | Drawing Register or Secure Drawing Viewer | Selected sheet or exact revision with Related Records open and a link to a synthetic RFI, Submittal, or Document | 1440x900 | Proprietary drawings, provider details, tokens, and claims of drawing annotations | Shows exact revision context while keeping formal revision and issue workflows intact |
| `relationship-dialog.png` | Any supported persisted record | Create Relationship dialog with relationship type, related entity type, bounded search results, and one selected candidate | 1440x900 | Raw IDs, storage metadata, and cross-project records | Demonstrates the controlled matrix and accessible metadata-only candidate flow |
| `relationship-mobile.png` | RFI, Punch Item, or Daily Log | One Related Records panel with a long synthetic title and reachable actions | 390x844 | Browser account UI and sensitive record text | Verifies narrow-screen wrapping and action access |

## Document search captures

M16.7 does not create or replace image files. Use synthetic PDFs and plain
search terms; do not imply semantic search or production OCR.

| File | Page / workflow | State to capture | Viewport | Avoid | Portfolio value |
|---|---|---|---|---|---|
| `document-search.png` | Project Document Search | Populated page-level results with safe snippets, match emphasis, metadata, extraction method, and one exact drawing-revision result | 1440x900 | Real document text, storage metadata, AI claims, or unavailable OCR shown as successful | Demonstrates project-scoped content discovery and contextual navigation |
| `document-search-empty.png` | Project Document Search | Submitted factual no-results state with filters visible | 1440x900 | Empty initial state presented as a failed search | Shows clear query and filter feedback |
| `document-search-mobile.png` | Project Document Search | Results, wrapping snippets, filters, and pagination at a narrow viewport | 390x844 | Clipped metadata, horizontal scrolling, or browser account UI | Demonstrates responsive search usability |
| `document-extraction-status.png` | Project Document Explorer details | Searchable, processing, warning, failed, or OCR-unavailable status with the controlled reprocess action | 1440x900 | Provider credentials, checksums, raw errors, or extracted page text | Shows honest lifecycle and recovery behavior |

## M16.7 capture status

No screenshot image is currently stored in this directory and M16.7 captures
none. Before portfolio or production closeout, capture at minimum:

- project root, nested folder, upload results, and document details
- drawing register, drawing-set workflow, revision history, and drawing issue
- secure viewer at desktop and mobile widths
- one relationship panel and the create-relationship dialog
- extraction status, populated project search, and search at mobile width

Use the exact filenames above where defined; do not add placeholders.

## Tips

- Crop out the browser chrome (or use a clean device frame consistently).
- Take captures after data loads — no skeletons visible unless intentional.
- Re-capture `dashboard.png` whenever the dashboard design changes; it is the
  first image recruiters see.
- M14 replaces the prior health-gauge dashboard with aggregate summary,
  attention, schedule, workflow, and recent-update sections, so
  `dashboard.png` and the dashboard version of `mobile.png` need recapturing.
- M13 adds Document Management across six workflows. Capture the listed
  attachment images above and recapture `change-orders.png` or
  `punch-lists.png` when their attachment controls should be visible in the
  primary module story.
- M16.3 adds the Drawing Register and controlled revision workflow. Capture
  `drawing-register.png`, `drawing-history.png`, and `drawing-issues.png`;
  this phase does not generate or replace image files.
- M16.4 adds the Secure Drawing Viewer. Capture `drawing-viewer.png` at desktop
  and include its mobile layout in `mobile.png`; use a synthetic PDF and keep
  storage URLs, tokens, and real project drawings out of the frame.
- M16.5 adds explicit construction-record relationships. Recapture
  `project-documents.png`, `drawing-viewer.png`, and at least one persisted
  RFI, Submittal, Punch Item, Change Order, or Daily Log with its Related
  Records panel visible. Add the four relationship captures above where the
  portfolio needs the complete creation, navigation, and responsive story.
- M16.6 adds native PDF extraction and project content search. Capture the
  search page, recapture `project-documents.png` with extraction status in the
  selected details, and recapture `drawing-viewer.png` with the distinct
  Viewer search and Project index labels. Production OCR must remain labeled
  unavailable unless a provider is deployed and verified.
- M16.7 consolidates the release set. The required root/nested explorer,
  upload, details, set, issue, history, viewer desktop/mobile, relationships,
  extraction, and search desktop/mobile captures all remain outstanding.
- M17.1 adds the deterministic project schedule anchor and summary-predecessor
  rollups. Recapture `schedule-grid.png`, add `schedule-settings.png`, and
  recapture `gantt.png` after changing the anchor so all displayed dates tell
  one consistent synthetic schedule story.
- M17.2 adds immutable schedule baselines and table-first variance analysis.
  Capture the create dialog, a populated desktop comparison with slipped,
  improved, added, removed, and critical-change context, and the stacked
  mobile comparison. Do not imply a dashboard baseline KPI, export comparison,
  or a Gantt baseline overlay.
- M17.3 adds live schedule progress and an independent Data Date. Recapture
  `schedule-grid.png`, `schedule-settings.png`, and `gantt.png`; also capture
  the focus-managed progress dialog with its conditional actual-date and
  remaining-duration fields. Keep progress off the dashboard and do not imply
  earned value, strict transition history, or resource loading.
- M17.4 adds milestones, eight standard constraints, multiple predecessors,
  signed lead/lag, and FS/SS/FF/SF relationships. Recapture
  `schedule-grid.png` and `gantt.png`, and capture the focus-managed planning
  dialog with synthetic dependencies and a dated constraint. Keep these
  planning features off the dashboard and do not imply resource loading,
  earned value, configurable calendars, or strict workflow transitions.
- M17.5 adds live schedule-derived Look-Ahead Plans. Capture the no-plan/create
  flow, a populated three-week view with carryover and filters, one blocked and
  one committed item, the metadata dialog, an archived read-only plan, mobile
  layout, and print preview. Do not imply frozen schedule snapshots,
  historical commitment audit, dashboard look-ahead metrics, notifications,
  server PDF generation, resources, or crews.
- M17.6 adds project-owned crews and equipment, task assignments, dated
  capacity, and current-forecast loading. Capture every Resource Planning view
  listed above and recapture `look-ahead-planning.png` with concise crew and
  equipment labels. Keep demand and capacity readable as text, and do not
  imply automatic leveling, individual employees, cost loading, dashboard
  resource KPIs, or planned-versus-actual manpower analytics.
- M17.7 adds explainable Schedule Health and executive reporting. Recapture
  `dashboard.png`, add the summary/dashboard-health/executive-report captures,
  and capture the summary at mobile width. Keep category and reasons textual;
  do not imply an opaque score, earned value, cost loading, resource leveling,
  exact-task dashboard deep links, or production verification. No screenshot
  image is created or replaced by M17.7.
