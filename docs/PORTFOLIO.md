# FieldFlow — Portfolio Copy

Ready-to-use descriptions for resumes, portfolio sites, and LinkedIn.
Keep the metrics in sync with the repo (M18.2 verified **1,025 primary tests: 590
frontend across 90 files + 435 backend**, with 420 backend subtests reported
separately).

---

## Resume

### One-liner

> FieldFlow — full-stack construction scheduling and field-management SaaS
> (React 19, FastAPI, PostgreSQL) with a drag-and-drop CPM-style scheduler,
> persistent Data Date, live progress, milestones, constraints, advanced
> dependencies, live three-week look-ahead planning, and bounded crew and
> equipment resource loading, explainable schedule health and executive PDF,
> executive dashboard, enhanced project-scoped Change Order, RFI, Submittal,
> and Punch List workflows, reusable Document Management across six resource
> types, a project document explorer, construction drawing revision
> management with a secure PDF viewer, explicit cross-record construction
> relationships, project-scoped PDF content search, hardened rotating-session
> authentication, immutable preconstruction content preparation, and 1,025 automated
> tests.

### Resume bullets

> **FieldFlow — Construction Planning & Field Management SaaS** · React 19,
> FastAPI, PostgreSQL, SQLAlchemy, Vite · [live demo](https://construction-scheduler-eight.vercel.app)
>
> - Built a deterministic spreadsheet-style scheduling engine with persistent
>   project start and Data Date anchors, multiple FS/SS/FF/SF dependencies,
>   signed lead/lag, zero-duration milestones, eight standard constraints,
>   summary-predecessor rollups, workday/holiday-aware date math, validated
>   task hierarchy, and keyboard-accessible drag-and-drop reordering; added
>   server-normalized progress, actual dates, remaining-duration forecasts,
>   out-of-sequence detection, progress-aware Gantt and PDF output, immutable
>   named baselines, workday variance, and critical/structural change analysis.
> - Added project-owned Look-Ahead Plans derived from the live schedule, with
>   Data Date anchored 7-42 day windows, weekly and carryover groups,
>   readiness, blockers, commitments, company/trade assignment, controlled
>   overrides, archival, print output, and stale-response protection without a
>   second task collection or dashboard request.
> - Added project-owned crews and equipment with whole-number task allocation,
>   optional project-company association, dated capacity overrides, live
>   progress-aware workday demand, textual utilization and over-allocation,
>   unassigned-work reporting, look-ahead labels, and browser print without
>   automatic leveling or schedule mutation.
> - Added deterministic schedule health with visible category thresholds,
>   bounded reasons and attention items, baseline/Data Date context, a fifth
>   Scheduler summary mode, one-request dashboard integration, and a safely
>   escaped authenticated executive PDF without a second analytics system.
> - Designed an accessible design system (15+ reusable components: dialogs
>   with focus traps, skeleton loading, toasts, icon system) and a
>   project-owned analytics endpoint that replaces dashboard collection
>   fan-out with bounded summary metrics, Attention Required, Upcoming
>   Schedule, Workflow Analytics, and Recent Updates.
> - Delivered a project-scoped RFI register with permanent sequential
>   numbering, Open/Pending/Closed workflow, due-date and overdue tracking,
>   responsible-company assignment, dashboard workflow metrics, and
>   authenticated ownership enforcement.
> - Shipped a project-scoped Submittals register with permanent sequential
>   `SUB` numbering, backend status and date validation, a refresh-safe
>   frontend create/edit/delete workflow, responsible-company and reviewer
>   tracking, and active, overdue, and approved dashboard metrics.
> - Shipped project-scoped Punch Lists with persistent per-project `PUNCH`
>   sequence allocation; backend priority, status, date, and ownership
>   validation; a refresh-safe frontend create/edit/delete route; location,
>   trade, responsible-company, and assignee tracking; overdue detection; and
>   open, overdue, and completed dashboard metrics.
> - Enhanced the original Change Orders register with persistent per-project
>   `CO` numbering, a data-preserving migration for legacy records,
>   fixed-precision proposed and approved amounts, lifecycle and whole-day
>   schedule-impact tracking, Draft through Void status coverage, complete
>   create/edit/delete, filtering and validation flows, and dashboard Active,
>   Approved, Rejected, Proposed Cost, Approved Cost, and Schedule Impact
>   metrics with exact decimal aggregation.
> - Designed one reusable Document Management system across Projects, Daily
>   Logs, RFIs, Submittals, Punch Items, and Change Orders: authenticated
>   streamed upload/download, 25 MiB validation, local and private
>   S3-compatible storage, accessible React attachment UI, and durable
>   cleanup across database and object-storage failures; added a responsive
>   project explorer with nested folders, metadata search, batch uploads, and
>   soft deletion.
> - Built a construction drawing register around the existing document
>   storage layer: project-owned sets, allowlisted disciplines, normalized
>   sheet identities, atomic PDF revision superseding, retained historical
>   downloads, formal issue membership, and a lazy authenticated PDF viewer
>   with page, sheet, revision, zoom, and existing-text search controls.
> - Added a secure construction-record relationship graph across ten
>   allowlisted entity types, with directional and symmetric links, bounded
>   metadata candidate search, project isolation, retained unavailable-record
>   context, exact drawing-revision navigation, and reusable lazy React panels
>   that add no dashboard or table-row request fan-out.
> - Added durable page-level PDF extraction and project-scoped PostgreSQL
>   full-text search with checksum-bound jobs, bounded plain-text snippets,
>   exact drawing-revision navigation, and a pluggable OCR boundary that
>   reports production OCR as unavailable until a provider is approved.
> - Established a provider-neutral AI preconstruction foundation with
>   project-owned review sets, controlled requirement/coverage/context roles,
>   checksum- and extraction-pinned immutable manifests, deterministic
>   readiness, durable leased attempts, strict untrusted-result validation,
>   and an isolated lazy React workspace; added deterministic preparation into
>   immutable checksum-bound snapshots, one-based pages, bounded citeable
>   segments, lineage-aware manifests, and a safe plain-text inspector.
>   Production remains disabled and no scope extraction, omission finding, or
>   live AI provider is claimed.
> - Hardened authentication with memory-only access JWTs, rotating opaque
>   refresh sessions, replay-family revocation, CSRF and exact-Origin
>   enforcement, route-wide tenant isolation, and bounded abuse controls;
>   verified the complete platform with 1,025 automated tests (Vitest/RTL +
>   pytest).

### Portfolio-site paragraph

> FieldFlow is a full-stack construction planning platform I designed and
> built end-to-end: a React 19 SPA over a FastAPI/PostgreSQL backend. The
> centerpiece is a spreadsheet-fast scheduler — persistent project anchors,
> an independent Data Date, status-aware progress and actuals,
> inline cell editing, multiple FS/SS/FF/SF dependencies with signed lead/lag,
> zero-duration milestones, eight standard constraints, live three-week
> look-ahead planning, and bounded crew/equipment loading over the current
> progress-aware forecast,
> deterministic summary rollups, workday and federal holiday calendars,
> validated task hierarchy, and drag-and-drop reordering that works
> from the keyboard — rendered as both an editable grid and a Gantt chart with
> PDF export. Around it sits a complete field-management suite (daily logs,
> inspections, delays, enhanced Change Orders, RFIs, Submittals, Punch Lists)
> and an aggregate Project Dashboard that answers
> a superintendent's first question of the day: what needs my attention? The
> project emphasizes production polish: a token-based accessible design
> system, first-run onboarding that seeds a realistic demo project,
> production-hardened rotating-session authentication, reusable secure
> attachments across six construction workflows, a responsive project
> document explorer, construction drawing revision management with secure
> browser viewing, explicit user-created relationships across construction
> records and drawing context, secure project PDF content search, immutable
> preconstruction content preparation, and 1,025
> automated tests
> across the stack.

---

## Document Management Case Study

### The problem

Construction records lose context when drawings, exhibits, photos, product
data, and cost backup live in separate inboxes or shared drives. Teams need
those documents to remain connected to the project record, protected by the
same ownership rules, and recoverable when storage providers are unavailable.

### The solution

FieldFlow uses one generic attachment metadata model and an explicit parent
resolver registry across six resource types: Projects, Daily Logs, RFIs,
Submittals, Punch Items, and Change Orders. Its project explorer adds nested
folder navigation, safe metadata search, bounded sorting and pagination,
recent documents, batch uploads, and authenticated download. PostgreSQL
stores metadata and SHA-256 checksums while opaque binary objects stream to
local development
storage or a private S3-compatible deployment target. A shared React
`AttachmentPanel` and `useAttachments` hook provide multiple-file upload,
partial-success feedback, authenticated preview/download, deletion, stale
response protection, and accessible mobile interaction without duplicating
resource-specific upload code or growing dashboard requests. A separate
project-scoped relationship model and resolver registry connect those
Documents, drawing records, and field workflows through controlled links
without duplicating storage or specialized drawing associations.
Durable extraction jobs open the same authorized objects, preserve page
boundaries, verify checksums, and index native PDF text through PostgreSQL;
the frontend returns bounded plain-text snippets and exact document or drawing
navigation without loading binaries during search.
The milestone closes with one linear, reversible five-migration chain, an
API/model inventory, explicit OCR and browser-verification limits, finite
worker and cleanup runbooks, and a checkable production QA gate rather than
claiming unexecuted cloud or browser behavior.

### The transaction-boundary challenge

PostgreSQL and object storage cannot participate in one atomic transaction.
Deleting metadata first could lose the only durable storage key; deleting the
object first could block users whenever the provider is unavailable.
FieldFlow records cleanup work transactionally before attachment metadata or
its parent commits as deleted. Remote cleanup runs after commit, retryable
failures remain queued with attempt tracking and exponential backoff, and
already-missing objects complete idempotently. This keeps user-facing deletion
available while preserving recoverable cleanup work.

### Measurable outcomes

- Six integrated resource types and one project explorer through shared
  attachment and document APIs, models, storage abstractions, hooks, and UI
- 25 MiB per-file limit with PDF, image, text, Word, and Excel support
- Private authenticated delivery with no public object keys or credentials
- 590 frontend tests across 90 files and 435 backend tests, for 1,025 primary
  tests passed; 420 backend subtests are tracked separately
- Lazy per-record panel mounting with no dashboard attachment preloading
- Ten allowlisted relationship entity types with bounded candidate search and
  no dashboard or table-row relationship preloading
- Native PDF content search with page-level results; production OCR remains an
  explicit disabled-provider boundary rather than an overstated capability
- One M16 release architecture, operations runbook, and manual QA matrix with
  merge readiness separated from production verification

---

## LinkedIn

### Launch post

> 🏗️ I shipped FieldFlow — a construction planning and field-management
> platform built for how superintendents actually work.
>
> Construction teams run the schedule in one tool, daily logs in another, and
> change orders over email. FieldFlow puts them behind one login:
>
> 📅 A deterministic spreadsheet-fast scheduler — persistent project anchor,
> inline editing, multiple FS/SS/FF/SF dependencies with signed lead/lag,
> milestones, standard constraints, summary rollups,
> workday/holiday-aware dates, hierarchy, drag-and-drop reordering,
> independent Data Date, live progress and actuals, out-of-sequence context,
> and immutable baseline comparison with workday variance
> Planned crews and equipment with dated capacity, progress-aware loading,
> textual utilization, over-allocation, and unassigned-work reporting
> A live three-week look-ahead with carryover, readiness, blockers,
> commitments, company/trade filtering, controlled overrides, and print output
> ▦ A Gantt view and one-click PDF export
> 📊 An executive dashboard that answers "what needs my attention today?"
> 📝 Daily logs, inspections, delays, and project-scoped Change Order, RFI,
> Submittal, and Punch List workflows with dashboard workflow metrics
> 📎 Secure project documents and record attachments across six workflows,
> with nested folder browsing, metadata search, private object storage, and
> durable cleanup
> Explicit links among Documents, drawings, RFIs, Submittals, Punch Items,
> Change Orders, and Daily Logs, with project isolation and contextual navigation
> Project-scoped native PDF content search with page snippets and exact drawing
> revision navigation
>
> Under the hood: React 19 + Vite, FastAPI + SQLAlchemy + PostgreSQL, hardened
> rotating-session auth, an accessible component design system, and 1,025
> automated tests.
>
> The demo seeds a full sample project in ~10 seconds — no signup friction:
> 👉 https://construction-scheduler-eight.vercel.app
> Code: https://github.com/WarscherProgramming/construction-scheduler
>
> #webdevelopment #react #fastapi #python #constructiontech #buildinpublic

### Short "Featured" blurb

> FieldFlow — full-stack construction scheduling SaaS. React 19 · FastAPI ·
> PostgreSQL. Drag-and-drop CPM-style scheduler, Gantt + PDF export, executive
> dashboard, project-scoped Change Order, RFI, Submittal, and Punch List
> workflows, secure Document Management across six resource types, a project
> document explorer, drawing revision management with a secure PDF viewer,
> explicit construction-record relationships, native PDF content search,
> immutable schedule baseline comparison, Data Date and progress tracking,
> milestones, constraints, advanced dependencies, live look-ahead planning,
> crew and equipment resource loading, explainable schedule health and
> executive reporting, accessible design system, 1,025
> automated tests. Live demo
> seeds a complete sample
> project in seconds.

---

## Interview talking points

1. **Deterministic, timezone-safe scheduling.** Each project persists separate
   local `YYYY-MM-DD` Schedule Start and Data Dates, so recalculation is
   independent of the day a request runs. A graph-based pass handles multiple
   FS/SS/FF/SF dependencies, signed lead/lag, milestones, constraints, and
   summary rollups, while workday math skips weekends and
   federal holidays. Live leaf progress preserves actual dates, forecasts
   remaining work, and surfaces retained-dependency out-of-sequence context.
   Immutable snapshots preserve stable task identity, historical hierarchy,
   dates, float, and critical state; comparison joins in memory and reports
   factual workday and structural variance without mutating the live plan.
2. **Honest aggregate metrics.** The dashboard returns factual schedule health
   from named thresholds and metrics, never an opaque score. Missing baseline
   is explicit attention, underlying schedule collections stay off the
   dashboard, and one authenticated aggregate computes bounded summaries,
   reasons, and lists while the frontend handles accessible presentation and
   stale-response protection.
3. **Client-side demo seeding.** First-run onboarding builds a realistic
   15-activity project through the same public REST endpoints users hit —
   zero backend special-casing, sequenced for a live progress bar, fully
   testable with mocked APIs.
4. **Hash-based routing as a deliberate trade-off.** Refresh-safe deep links
   on static hosting with zero rewrite rules; the router is ~50 lines and
   unit-tested, chosen over a router dependency for this app's scale.
5. **Accessibility as architecture.** Focus-trapped dialogs, skip links,
   `aria-current` navigation, screen-reader-labeled skeletons, and tests that
   query by role and accessible name — so a11y regressions fail CI, not users.
6. **Durable cleanup across two systems.** PostgreSQL and object storage
   cannot share one transaction, so attachment storage keys are persisted in
   cleanup jobs before metadata or parent deletion commits. Remote failures
   retry without blocking the user, and missing objects complete
   idempotently.
7. **Defense-in-depth sessions.** Short-lived access JWTs exist only in
   memory, while opaque refresh tokens rotate through HttpOnly cookies and are
   stored as keyed digests. Replay revokes the token family; exact Origin,
   CSRF, database-backed identity, and project-scoped queries protect the
   cross-site deployment without introducing a generic authorization layer.
8. **Polymorphic integrity without arbitrary models.** One relationship table
   connects ten construction entity types, while an explicit resolver and
   allowed-link matrix enforce project ownership, availability, display
   summaries, direction, and navigation. The tradeoff is documented because
   polymorphic IDs cannot use native foreign keys to every parent table.
9. **AI as an advisory boundary, not an authority.** Preconstruction consumes
   explicit version-pinned sources through a provider-neutral DTO and durable
   attempt lifecycle. M18.2 snapshots deterministic extracted text into
   immutable pages and bounded citeable segments without replacing project
   search. It cannot mutate source documents, schedules, relationships,
   contracts, or procurement; evidence-backed findings and mandatory review
   workflows remain future work.
