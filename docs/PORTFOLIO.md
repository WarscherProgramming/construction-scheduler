# FieldFlow — Portfolio Copy

Ready-to-use descriptions for resumes, portfolio sites, and LinkedIn.
Keep the metrics in sync with the repo (currently **523 primary tests: 295
frontend across 44 files + 228 backend**, with 271 backend subtests reported
separately).

---

## Resume

### One-liner

> FieldFlow — full-stack construction scheduling and field-management SaaS
> (React 19, FastAPI, PostgreSQL) with a drag-and-drop CPM-style scheduler,
> executive dashboard, enhanced project-scoped Change Order, RFI, Submittal,
> and Punch List workflows, reusable Document Management across six resource
> types, hardened rotating-session authentication, and 523 automated tests.

### Resume bullets

> **FieldFlow — Construction Planning & Field Management SaaS** · React 19,
> FastAPI, PostgreSQL, SQLAlchemy, Vite · [live demo](https://construction-scheduler-eight.vercel.app)
>
> - Built a spreadsheet-style scheduling engine with FS/SS dependencies, lag,
>   workday/holiday-aware date math, task hierarchy, and keyboard-accessible
>   drag-and-drop reordering, plus Gantt visualization and PDF export.
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
>   cleanup across database and object-storage failures.
> - Hardened authentication with memory-only access JWTs, rotating opaque
>   refresh sessions, replay-family revocation, CSRF and exact-Origin
>   enforcement, route-wide tenant isolation, and bounded abuse controls;
>   verified the complete platform with 523 automated tests (Vitest/RTL +
>   pytest).

### Portfolio-site paragraph

> FieldFlow is a full-stack construction planning platform I designed and
> built end-to-end: a React 19 SPA over a FastAPI/PostgreSQL backend. The
> centerpiece is a spreadsheet-fast scheduler — inline cell editing,
> Finish-to-Start/Start-to-Start dependencies with lag, workday and federal
> holiday calendars, task hierarchy, and drag-and-drop reordering that works
> from the keyboard — rendered as both an editable grid and a Gantt chart with
> PDF export. Around it sits a complete field-management suite (daily logs,
> inspections, delays, enhanced Change Orders, RFIs, Submittals, Punch Lists)
> and an aggregate Project Dashboard that answers
> a superintendent's first question of the day: what needs my attention? The
> project emphasizes production polish: a token-based accessible design
> system, first-run onboarding that seeds a realistic demo project,
> production-hardened rotating-session authentication, reusable secure
> attachments across six construction workflows, and 523 automated tests
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
Submittals, Punch Items, and Change Orders. PostgreSQL stores metadata and
SHA-256 checksums while opaque binary objects stream to local development
storage or private S3-compatible production storage. A shared React
`AttachmentPanel` and `useAttachments` hook provide multiple-file upload,
partial-success feedback, authenticated preview/download, deletion, stale
response protection, and accessible mobile interaction without duplicating
resource-specific upload code or growing dashboard requests.

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

- Six integrated resource types through one attachment API, model, storage
  abstraction, hook, and panel
- 25 MiB per-file limit with PDF, image, text, Word, and Excel support
- Private authenticated delivery with no public object keys or credentials
- 295 frontend tests across 44 files and 228 backend tests, for 523 primary
  tests passed; 271 backend subtests are tracked separately
- Lazy per-record panel mounting with no dashboard attachment preloading

---

## LinkedIn

### Launch post

> 🏗️ I shipped FieldFlow — a construction planning and field-management
> platform built for how superintendents actually work.
>
> Construction teams run the schedule in one tool, daily logs in another, and
> change orders over email. FieldFlow puts them behind one login:
>
> 📅 A spreadsheet-fast scheduler — inline editing, FS/SS dependencies with
> lag, workday/holiday-aware dates, hierarchy, and drag-and-drop reordering
> ▦ A Gantt view and one-click PDF export
> 📊 An executive dashboard that answers "what needs my attention today?"
> 📝 Daily logs, inspections, delays, and project-scoped Change Order, RFI,
> Submittal, and Punch List workflows with dashboard workflow metrics
> 📎 Secure project documents and record attachments across six workflows,
> backed by private object storage and durable cleanup
>
> Under the hood: React 19 + Vite, FastAPI + SQLAlchemy + PostgreSQL, hardened
> rotating-session auth, an accessible component design system, and 523
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
> workflows, secure Document Management across six resource types, accessible
> design system, 523 automated tests. Live demo seeds a complete sample
> project in seconds.

---

## Interview talking points

1. **Timezone-safe scheduling.** Dates are handled as local `YYYY-MM-DD`
   values end-to-end (no UTC drift), with workday math that skips weekends
   and federal holidays — a classic real-world bug class, designed out.
2. **Honest aggregate metrics.** Tasks have no completion field, so the
   dashboard reports planned-finish attention and upcoming starts instead of
   pretending to know percent complete. One authenticated aggregate endpoint
   computes bounded project summaries and lists, while the frontend focuses
   on accessible presentation, cancellation, and stale-response protection.
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
