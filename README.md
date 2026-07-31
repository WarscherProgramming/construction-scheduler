# FieldFlow

**Construction planning and field management, in one place.**

FieldFlow gives superintendents, project managers, and project engineers a
single source of truth for the schedule, the field, and the paper trail —
a spreadsheet-fast scheduler, an executive dashboard, and complete field
records (daily logs, inspections, delays, change orders, RFIs, Submittals,
and Punch Lists) with their supporting documents.

![React 19](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white&labelColor=20232a)
![FastAPI](https://img.shields.io/badge/FastAPI-0.1x-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169e1?logo=postgresql&logoColor=white)
![Tests](https://img.shields.io/badge/tests-553%20passing-2ea44f)
![Vite](https://img.shields.io/badge/Vite-8-646cff?logo=vite&logoColor=white)

![FieldFlow executive dashboard](docs/screenshots/dashboard.png)

---

## Live Demo

**▶ [Try FieldFlow now](https://construction-scheduler-eight.vercel.app)** — no setup required.

1. Click **Explore the demo** on the landing page (credentials are prefilled),
   then **Create account**.
2. Choose **Load Sample Project** — FieldFlow seeds *Riverside Medical Center —
   Phase 2* (a 15-activity schedule, crews, logs, inspections, and change
   orders) in about ten seconds, with live progress.
3. You land on the **Project Dashboard**: aggregate project summary,
   Attention Required, Upcoming Schedule, Workflow Analytics, and Recent
   Updates.

### The 90-second tour

1. **Dashboard** — scan project KPIs, items requiring attention, upcoming
   tasks, workflow status, and recent updates.
2. **Schedule** — click any cell to edit inline (Enter saves, Escape cancels),
   select a row, **drag to reorder**, indent/outdent to build a hierarchy.
3. Toggle the **Gantt** view, then **Export Schedule as PDF**.
4. **Change Orders** — create or edit a numbered record, track cost and
   schedule impact, filter by status, and use the accessible delete flow.
5. Shrink the window — the persistent rail and record tables adapt down to
   phone widths.

## Why FieldFlow

Superintendents run the job from the field, but the schedule lives in one
tool, daily logs in another, and change orders in email. FieldFlow puts the
CPM-style schedule and the field record set behind one login, so the 6:30 AM
question — *"what needs my attention today?"* — has a one-screen answer.

## Engineering Highlights

- **React 19 + Vite SPA** with lazy-loaded routes and a hand-rolled,
  refresh-safe hash router.
- **FastAPI backend** with a layered domain/services architecture,
  SQLAlchemy ORM, and Alembic migrations on **PostgreSQL**.
- **Hardened authentication** with memory-only access JWTs, rotating opaque
  refresh sessions, replay-family revocation, CSRF and exact-Origin checks,
  database-backed user validation, single-flight refresh, cross-tab logout,
  and production configuration validation.
- **Interactive scheduler**: spreadsheet-style inline editing, Finish-to-Start
  and Start-to-Start dependencies with lag, workday/holiday-aware date math,
  parent/child hierarchy, and keyboard-accessible drag-and-drop reordering
  (dnd-kit).
- **Dynamic Gantt chart** rendered from the same task data, plus one-click PDF
  export.
- **Project Dashboard and Analytics** backed by one authenticated,
  project-owned aggregate endpoint: schedule, RFI, Submittal, Punch Item,
  Change Order, Daily Log, and document summaries; bounded Attention
  Required, Upcoming Schedule, Workflow Analytics, and Recent Updates;
  stale-response protection; and no dashboard collection fan-out.
- **Project-scoped RFI workflow** with server-assigned sequential numbering,
  Open/Pending/Closed states, responsible-company assignment, due-date and
  overdue tracking, and authenticated ownership enforcement.
- **Project-scoped Submittals workflow** with permanent sequential `SUB`
  numbering; Draft, Submitted, Under Review, Approved, Revise and Resubmit,
  and Rejected states; responsible-company and reviewer tracking; required-by,
  reviewed-date, and overdue tracking; dashboard workflow metrics; and
  authenticated ownership enforcement.
- **Project-scoped Punch Lists workflow** with permanent sequential `PUNCH`
  numbering; Open, In Progress, Completed, and Verified states; Low, Medium,
  High, and Critical priorities; location, trade, responsible-company, and
  assignee tracking; due-date, completion-date, and overdue tracking;
  dashboard workflow metrics; and authenticated ownership enforcement.
- **Enhanced project-scoped Change Orders workflow** with backend-assigned,
  permanent `CO` numbering; eight lifecycle statuses; proposed and approved
  fixed-precision amounts; schedule impact, lifecycle dates, title,
  description, reason, company, and responsible-party tracking; full
  create/edit/delete and filtering flows; legacy-record compatibility;
  dashboard workflow and cost metrics; recent updates; and authenticated
  ownership enforcement.
- **Reusable Document Management** across Projects, Daily Logs, RFIs,
  Submittals, Punch Items, and Change Orders, with multiple-file upload,
  authenticated streaming, secure validation, local or private S3-compatible
  storage, accessible previews and deletion, and durable object cleanup.
- **Document storage foundation** with a provider-neutral interface, opaque
  sharded object keys, safe metadata-only APIs, SHA-256 checksums,
  hierarchical project folders, soft deletion, and fields reserved for
  future document version history.
- **Project Document Explorer** with nested folder browsing, breadcrumbs,
  metadata search, allowlisted filtering and sorting, bounded pagination,
  recent documents, batch and drag-and-drop uploads, metadata inspection,
  authenticated downloads, and soft deletion.
- **Accessible design system**: tokens, reusable UI primitives (Button, Card,
  Sidebar, PageHeader, Icon, ConfirmDialog, Skeleton), skip links, focus
  management, `aria-current` navigation, and screen-reader-labeled loading
  states.
- **Responsive UI** from desktop rail navigation down to stacked mobile record
  cards.
- **Client-side onboarding**: first-run detection seeds a realistic demo
  project through the public API with visible progress — the app is never
  empty.
- **Automated testing: 553 tests** — 317 frontend across 46 files (Vitest +
  React Testing Library, behavior- and accessibility-focused) and 236 backend
  tests plus 274 separately reported subtests (pytest,
  covering the scheduling engine, critical path, services, migrations, CORS,
  and TestClient API integration).

## Architecture at a Glance

```text
┌────────────────────┐        HTTPS / JSON        ┌─────────────────────┐
│   React 19 SPA     │  ───── REST + JWT ─────▶   │   FastAPI (Python)  │
│   Vite · dnd-kit   │  ◀──── JSON responses ──   │   api → services →  │
│   Accessible UI    │                            │   domain → models   │
│   (Vercel)         │                            │   (Render)          │
└────────────────────┘                            └──────────┬──────────┘
        │                                                    │ SQLAlchemy
        │  memory: access JWT; storage: onboarding flag      │ + Alembic
        ▼                                                    ▼
  hash-based routes                               ┌─────────────────────┐
  (refresh-safe, no                               │     PostgreSQL      │
  rewrite rules)                                  └─────────────────────┘
```

**How data flows:** the SPA authenticates against `/auth`, keeps its
short-lived access JWT only in memory, and restores or rotates an opaque
HttpOnly refresh session through CSRF-protected cookie requests. Every
protected request carries the access token through a fetch wrapper that
centralizes one-retry 401 handling and cross-tab session events. Page
containers call REST endpoints (`/projects/{id}/tasks`,
`/daily-logs`, `/inspections`, `/notes-delays`, `/change-orders`, `/rfis`,
`/submittals`, `/punch-items`, …); the
FastAPI service layer applies the scheduling rules (dependencies, lag,
workday/holiday calendars) and persists through SQLAlchemy models managed by
Alembic migrations. Responses return the full recalculated task set, so the
grid and Gantt always render from one consistent source. The project dashboard
uses one authenticated aggregate endpoint instead of loading each resource
collection. Backend queries calculate bounded summary metrics, attention
items, upcoming tasks, and recent updates; the frontend handles formatting,
navigation, loading, retry, cancellation, and stale-response protection.

The complete dashboard hierarchy, API contract, request lifecycle, test
coverage, bundle history, and deferred work are documented in
[`docs/PROJECT_DASHBOARD.md`](docs/PROJECT_DASHBOARD.md).

The final authentication architecture, threat model, deployment checklist,
operational runbooks, manual QA guide, release notes, and deferred security
roadmap are documented in [`docs/SECURITY.md`](docs/SECURITY.md).

The provider contract, document and folder models, storage-key format,
service transactions, API boundary, retention decision, and M16 roadmap are
documented in
[`docs/DOCUMENT_STORAGE.md`](docs/DOCUMENT_STORAGE.md).

Change Orders use a focused service layer for validation and project-scoped
`CO-###` allocation. A persistent per-project sequence table prevents deleted
numbers from being reused, while a database constraint enforces number
uniqueness within each project. The enhancement migration preserves existing
rows and unique nonstandard numbers, repairs only missing or duplicate
numbers, backfills safely parseable legacy amounts into fixed-precision
`NUMERIC(14,2)` fields, and retains the original `amount` field for
compatibility.

## Document Management Architecture

FieldFlow keeps supporting documents attached to the records where teams use
them: project documents, Daily Log attachments, RFI exhibits, Submittal
packages, Punch Item evidence, and Change Order backup. Users can upload
multiple files, retain duplicate display filenames, preview supported PDFs
and images, download securely, and delete attachments. Deleting an RFI,
Submittal, Punch Item, or Change Order also schedules durable cleanup of its
stored objects.

```mermaid
flowchart LR
    UI[AttachmentPanel] --> API[Authenticated Attachment API]
    API --> VALIDATE[Ownership and File Validation]
    VALIDATE --> STORAGE[Storage Adapter]
    STORAGE --> LOCAL[Local Storage]
    STORAGE --> S3[Private S3-Compatible Storage]
    VALIDATE --> DB[(PostgreSQL Metadata)]
    DB --> LIST[List Attachment Metadata]
    API --> DOWNLOAD[Authenticated Streaming Download]
    DOWNLOAD --> STORAGE
    DB --> OUTBOX[(Cleanup Jobs)]
    OUTBOX --> COMMAND[Cleanup Command]
    COMMAND --> STORAGE
```

**Upload lifecycle**

1. The user selects one or more files; frontend size and extension checks
   provide immediate advisory feedback.
2. Each file is sent sequentially through an authenticated multipart API
   request, allowing partial success when one file fails.
3. The backend verifies project ownership and parent identity, then validates
   size, MIME type, extension, filename, and file signature or container.
4. The storage adapter streams the file to local or private S3-compatible
   storage while calculating SHA-256.
5. PostgreSQL metadata is committed only after storage succeeds. Public API
   responses never expose credentials or object keys.

**Download and preview lifecycle**

1. The browser requests an attachment through the authenticated API.
2. The backend verifies project ownership and streams content from storage.
3. PDF, JPEG, PNG, and WebP files may open inline; other supported formats
   download as attachments.
4. The frontend uses temporary Blob URLs for previews and downloads and
   revokes them after use.

**Deletion lifecycle**

- Standalone deletion records a durable cleanup job and removes attachment
  metadata transactionally. After commit, object deletion is attempted;
  provider failures remain queued for retry.
- Parent deletion first preserves every storage key in cleanup jobs, then
  removes attachment metadata and the parent in one database transaction.
  Remote cleanup runs after commit, so a provider outage does not block the
  successful deletion of the parent record.
- Missing objects are handled idempotently as completed cleanup work.

The shared authenticated API is intentionally resource-neutral:

- `GET /projects/{project_id}/attachments` lists one parent's metadata.
- `POST /projects/{project_id}/attachments` uploads multipart file content.
- `GET /projects/{project_id}/attachments/{attachment_id}/download` streams
  authenticated preview or download content.
- `DELETE /projects/{project_id}/attachments/{attachment_id}` removes one
  attachment and records durable cleanup work.

### Storage and Validation

PostgreSQL stores metadata, checksums, provider names, and opaque storage keys;
it does not store file contents. Local storage is intended for development,
lives outside the frontend source tree, uses create-only bounded writes, and
removes partial files after failures. Local files on an ephemeral production
instance may be lost during redeployment.

The `s3` adapter stores private objects in AWS S3 or an S3-compatible service.
Region, endpoint, addressing style, key prefix, transport, timeouts, and
retries are configurable. Reads and writes are streamed, no public-read ACL
is applied, and browsers never receive direct object access or storage keys.
Client construction is lazy, so importing or starting the application does
not contact S3. Persistent private object storage is recommended for
production.

The authoritative backend limit is **25 MiB per file**. Supported formats are
PDF, JPEG, PNG, WebP, HEIC/HEIF, TXT, CSV, DOC, DOCX, XLS, and XLSX.
Validation includes extension and MIME consistency, strong signatures for PDF
and supported images, OLE or ZIP container signatures for Office files,
UTF-8 and NUL-byte checks for text files, zero-byte rejection, filename
normalization, path-traversal protection, bounded streaming, and SHA-256
calculation. Browser checks are advisory; backend validation is authoritative.
FieldFlow does not currently perform antivirus scanning.

### Resource Coverage

| Resource | Parent type | Upload | Preview | Download | Attachment delete | Parent-delete cleanup |
|---|---|---:|---:|---:|---:|---:|
| Project | `project` | Yes | Yes | Yes | Yes | Not applicable until project deletion exists |
| Daily Log | `daily_log` | Yes | Yes | Yes | Yes | Not applicable until Daily Log deletion exists |
| RFI | `rfi` | Yes | Yes | Yes | Yes | Yes |
| Submittal | `submittal` | Yes | Yes | Yes | Yes | Yes |
| Punch Item | `punch_item` | Yes | Yes | Yes | Yes | Yes |
| Change Order | `change_order` | Yes | Yes | Yes | Yes | Yes |

Preview availability depends on the file type and browser; FieldFlow exposes
preview controls for PDFs and browser-renderable JPEG, PNG, and WebP images.

### Frontend Design

Shared attachment API functions support list, multipart upload, authenticated
Blob download, and delete. `useAttachments` owns request state, sequential
multiple-file uploads, partial-success reporting, stale-response protection,
Strict Mode request deduplication, `AbortSignal` cancellation, Blob URL
cleanup, and identity resets. `AttachmentPanel` supplies the reusable upload,
list, preview, download, error, empty, loading, and confirmation UI.

Each resource lazily mounts at most one active panel, so attachments are not
preloaded for every visible record or by the dashboard. Attachment state
stays out of `useProjectResource` and `useRecordForms`; changing projects or
active parents clears stale state.

Accessibility support includes associated file-input labels,
keyboard-accessible upload and expansion controls, semantic file lists,
filename-specific action labels, `aria-expanded`, `aria-controls`, live upload
and error announcements, accessible confirmation dialogs with focus
restoration, non-color-only drag feedback, and responsive wrapping for long
filenames and actions. These practices are tested, but are not presented as a
formal WCAG certification.

### Durable Cleanup

Cleanup jobs transactionally preserve storage work across the PostgreSQL and
object-storage boundary. Processing records attempts, applies bounded
exponential backoff, recovers interrupted `Processing` jobs after a lease,
treats missing objects idempotently, retains completed jobs for a configurable
period, and supports reconciliation and pruning. Jobs use the exact statuses
`Pending`, `Processing`, `Completed`, and `Failed`.

```bash
python -m app.commands.process_attachment_cleanup
python -m app.commands.process_attachment_cleanup --batch-size 50 --max-jobs 200
python -m app.commands.process_attachment_cleanup --prune-completed
```

Supported options are `--batch-size`, `--max-jobs`, and `--prune-completed`.
Production must invoke this command through an external recurring scheduled
job. FieldFlow does not include a built-in worker or scheduler, and
`render.yaml` does not currently declare a scheduled cleanup job.

## Features

**Scheduling**
- Spreadsheet-style schedule editing with full keyboard support
- Finish-to-Start and Start-to-Start dependencies with lag (`12`, `12+3`, `12SS+4`)
- Workday scheduling that skips weekends and federal holidays
- Parent/child task hierarchy with indent/outdent and collapse
- Drag-and-drop ordering (pointer and keyboard)
- Gantt visualization and PDF schedule export
- Reusable schedule templates

**Project Dashboard and Analytics**
- Aggregate project summary for schedule, RFIs, Submittals, Punch Items,
  Change Orders, Daily Logs, and documents
- Bounded Attention Required and Upcoming Schedule lists with direct
  project-workflow navigation
- Workflow Analytics for RFI, Submittal, Punch Item, and Change Order status
  counts, including exact backend-aggregated Change Order values
- Recent Updates across RFIs, Submittals, Punch Items, Change Orders, and
  attachments
- One project-owned aggregate request with loading, retry, cancellation,
  Strict Mode deduplication, and stale-response protection
- Accessible headings, semantic lists and timestamps, contextual link names,
  keyboard focus, reduced motion, and responsive mobile-to-ultrawide layouts

**Field records**
- Daily logs, inspections, and notes & delays
- Project-scoped Change Order creation, editing, and deletion with
  backend-generated permanent `CO` numbering and authenticated ownership
  enforcement
- Draft, Pending, Submitted, Under Review, Approved, Rejected, Executed, and
  Void workflow with title, description, reason, company, and
  responsible-party tracking
- Fixed-precision proposed and approved amounts, whole-day schedule impact,
  and requested, submitted, approved, and executed lifecycle dates
- Legacy Change Order compatibility, status filtering, validation, recent
  Change Order display, and merged activity-feed support
- Project-scoped RFI creation, editing, and deletion with responsible-company
  assignment and Open, Pending, or Closed workflow
- Sequential per-project RFI numbering with due-date and overdue tracking
- Project-scoped Submittal creation, editing, and deletion with
  responsible-company and reviewer tracking
- Sequential per-project `SUB` numbering; Draft, Submitted, Under Review,
  Approved, Revise and Resubmit, and Rejected workflow
- Required-by and reviewed-date tracking with overdue Submittal detection
- Project-scoped Punch Item creation, editing, and deletion with location,
  trade, responsible-company, and assignee tracking
- Sequential per-project `PUNCH` numbering; Open, In Progress, Completed, and
  Verified workflow; Low, Medium, High, and Critical priorities
- Due-date and completion-date tracking with overdue Punch Item detection
- Authenticated ownership enforcement across project Change Order, RFI,
  Submittal, and Punch Item operations
- Search, filtering, status badges, and responsive record cards
- Project-company management

**Document management**
- Project documents and attachments for Daily Logs, RFIs, Submittals, Punch
  Items, and Change Orders
- Provider-neutral document storage with local and S3-compatible adapters
- Hierarchical project folders and safe document metadata APIs
- Opaque sharded storage keys, streamed SHA-256 checksums, and version-ready
  metadata
- Project Document Explorer with folder tree, breadcrumbs, recent documents,
  metadata details, search, filtering, sorting, and pagination
- Single, multiple, and drag-and-drop uploads with per-file results, partial
  success, and retry
- Authenticated downloads and confirmed soft deletion without provider-path
  exposure
- Multiple-file upload with independent results and duplicate display
  filename support
- Authenticated PDF and image previews, streamed downloads, and attachment
  deletion
- Secure backend file validation and project ownership enforcement
- Local development storage and private S3-compatible production storage
- Durable standalone and parent-deletion object cleanup

**Product quality**
- Branded landing/login, first-run onboarding with demo seeding
- Icon system, confirmation dialogs, toast notifications, loading skeletons
- WCAG-minded semantics: skip links, focus traps, `aria-live` announcements

## Screenshots

| | |
|---|---|
| ![Project Dashboard](docs/screenshots/dashboard.png) *Project Dashboard — summary, attention, upcoming work, workflow analytics, and recent updates* | ![Schedule grid](docs/screenshots/schedule-grid.png) *Spreadsheet-style schedule with hierarchy and inline editing* |
| ![Drag-and-drop reordering](docs/screenshots/schedule-dnd.gif) *Drag-and-drop task reordering* | ![Landing page](docs/screenshots/login.png) *Split-panel landing and login* |
| ![Gantt view](docs/screenshots/gantt.png) *Gantt visualization* | ![First-run onboarding](docs/screenshots/first-run.gif) *First-run onboarding seeds a full sample project* |
| ![Change orders](docs/screenshots/change-orders.png) *Change orders — generated numbers, lifecycle, cost, schedule impact, and status workflow* | ![Responsive layout](docs/screenshots/mobile.png) *Responsive rail and record cards* |

*(Capture checklist: [docs/screenshots/README.md](docs/screenshots/README.md))*

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, dnd-kit, Inter (self-hosted) |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic |
| Database | PostgreSQL |
| Auth | Memory-only access JWT + rotating opaque refresh sessions |
| Testing | Vitest + React Testing Library (317), pytest (236) |
| Hosting | Vercel (frontend) · Render (API + migrations) |

## Testing

**553 primary automated tests passed.** Backend subtests are reported
separately rather than added to that total.

- **Frontend (317 across 46 files)** — Vitest + React Testing Library. Tests
  target behavior and accessibility: roles and names, keyboard flows
  (Enter/Escape editing,
  grid cursor navigation, focus traps), aggregate dashboard rendering,
  demo-seeding orchestration, App-level integration wiring, the HTTP
  transport layer, and loading/empty/error states. Attachment coverage
  includes API clients, advisory validation, sequential multiple-file
  uploads, partial success, stale-response protection, previews, downloads,
  Blob URL cleanup, confirmation and accessibility behavior, all six resource
  integrations, and request-count behavior. Document Explorer coverage
  includes routing, folder navigation, breadcrumbs, query controls,
  pagination, batch uploads, partial failures, stale-response protection,
  details and delete dialogs, focus restoration, status-specific failures,
  and responsive folder access.
- **Backend (236, plus 274 subtests)** — pytest. Covers the workday scheduling
  engine (dependencies, lag, federal holidays), critical path and total float,
  task services, relationship migrations, CORS configuration, and
  TestClient API integration (auth, ownership enforcement, task lifecycle,
  Change Orders, RFIs, Submittals, Punch Lists, and field records over HTTP).
  Attachment coverage includes authentication, ownership and parent
  resolution, streaming upload/download, file validation, local and S3
  adapters, S3 error classification, deletion cleanup, retries, leases,
  reconciliation, migration safety, and parent-deletion cleanup. Document
  foundation coverage includes provider contracts, folder integrity,
  authorization, secure upload/download, checksums, rollback, soft deletion,
  response exposure, migration cycles, explorer counts and breadcrumbs,
  escaped metadata search, filtering, stable sorting, pagination, recent
  documents, and project isolation. Security
  coverage includes strict JWT claims, rotating refresh sessions, replay
  revocation, CSRF, exact CORS origins, rate and body limits, route-wide
  ownership, transaction rollback, safe errors, production configuration,
  logging redaction, and health behavior.

```bash
# frontend
cd frontend && npm test && npm run lint && npm run build

# backend
cd backend && pytest
```

## Getting Started

### Backend (`backend/`)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/scheduler_db
APP_ENV=development
APP_DEBUG=false
SECRET_KEY=replace-with-a-long-random-secret
REFRESH_TOKEN_SECRET=
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
ATTACHMENT_STORAGE_PROVIDER=local
```

Run migrations and start the API (docs at `http://127.0.0.1:8000/docs`):

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend (`frontend/`)

```bash
npm install
npm run dev        # http://localhost:5173
```

Set `VITE_API_URL` when pointing at a deployed API. Authentication requests
default to a 10-second timeout; use `VITE_AUTH_REQUEST_TIMEOUT_MS` only when a
different bounded deployment value is required.

### Attachment Configuration

Local development should use `ATTACHMENT_STORAGE_PROVIDER=local` unless an
S3 integration is intentionally being tested. The following variables match
[`backend/.env.example`](backend/.env.example):

| Group | Variable | Purpose |
|---|---|---|
| Provider | `ATTACHMENT_STORAGE_PROVIDER` | `local` or `s3` |
| Local | `ATTACHMENT_LOCAL_STORAGE_ROOT` | Optional absolute or expanded local root; blank uses `backend/.attachment_storage` |
| File limits | `ATTACHMENT_MAX_UPLOAD_SIZE` | Maximum bytes per file; default `26214400` |
| File limits | `ATTACHMENT_UPLOAD_CHUNK_SIZE` | Backend streaming chunk size; default `65536` |
| S3 | `ATTACHMENT_S3_BUCKET` | Private bucket name; required in `s3` mode |
| S3 | `ATTACHMENT_S3_REGION` | Bucket region; required in `s3` mode |
| S3 | `ATTACHMENT_S3_ENDPOINT_URL` | Optional HTTPS endpoint for compatible providers |
| S3 | `ATTACHMENT_S3_ACCESS_KEY_ID` | Secret access-key identifier; required in `s3` mode |
| S3 | `ATTACHMENT_S3_SECRET_ACCESS_KEY` | Secret access key; required in `s3` mode |
| S3 | `ATTACHMENT_S3_SESSION_TOKEN` | Optional temporary session token |
| S3 | `ATTACHMENT_S3_ADDRESSING_STYLE` | `auto`, `path`, or `virtual` |
| S3 | `ATTACHMENT_S3_SECURE_TRANSPORT` | Require secure transport; default `true` |
| S3 | `ATTACHMENT_S3_KEY_PREFIX` | Optional normalized object-key prefix |
| Timeouts/retries | `ATTACHMENT_S3_CONNECT_TIMEOUT` | Connection timeout in seconds |
| Timeouts/retries | `ATTACHMENT_S3_READ_TIMEOUT` | Read timeout in seconds |
| Timeouts/retries | `ATTACHMENT_S3_MAX_RETRIES` | Provider retry limit |
| Cleanup | `ATTACHMENT_CLEANUP_BATCH_SIZE` | Jobs claimed per cleanup batch |
| Cleanup | `ATTACHMENT_CLEANUP_MAX_ATTEMPTS` | Maximum attempts before `Failed` |
| Cleanup | `ATTACHMENT_CLEANUP_RETRY_BASE_SECONDS` | Initial exponential-backoff delay |
| Cleanup | `ATTACHMENT_CLEANUP_RETRY_MAX_SECONDS` | Backoff ceiling |
| Cleanup | `ATTACHMENT_CLEANUP_LEASE_SECONDS` | Recovery age for interrupted jobs |
| Cleanup | `ATTACHMENT_CLEANUP_RETENTION_DAYS` | Completed-job retention before pruning |

Use placeholder values in local `.env` files and configure production
credentials as secret environment values. Render requires the S3 provider,
bucket, region, access-key ID, and secret access key shown in
`render.yaml`; configure an endpoint when the provider is not AWS. Never
commit production credentials.

## Deployment

- **Frontend — Vercel.** Hash-based routes keep every module refresh-safe with
  zero rewrite configuration. Live at
  [construction-scheduler-eight.vercel.app](https://construction-scheduler-eight.vercel.app).
- **Backend — Render.** [`backend/render.yaml`](backend/render.yaml) defines
  the web service, runs Alembic migrations on deploy, sets the health check,
  selects production mode and secure cross-site cookies, pins the exact CORS
  origin, and selects private S3-compatible storage.
- **Security release gate.** Follow
  [`docs/SECURITY.md`](docs/SECURITY.md) for secret preparation, migration and
  restart order, rollback, post-deployment cookie/CORS/header checks, and
  incident runbooks. Dynamic Vercel preview origins are not trusted by
  wildcard.
- **Attachment storage.** Production should use persistent object storage;
  Render's ephemeral local filesystem may be lost during deploys. Keep the
  bucket private, store credentials as secrets, and grant the application
  identity only the minimum operations needed to upload, read, delete, and
  check object existence.
- **Cleanup scheduling.** Run
  `python -m app.commands.process_attachment_cleanup` as a recurring external
  scheduled job. The current Render blueprint configures only the web service,
  so cleanup scheduling remains an explicit deployment operation.

## Roadmap

**Shipped**
- ✅ Design system, tokens, and reusable UI component layer
- ✅ Persistent project navigation shell with active-page state
- ✅ M14 Project Dashboard and Analytics with one project-owned aggregate
  endpoint, summary metrics, Attention Required, Upcoming Schedule, Workflow
  Analytics, Recent Updates, stale-response protection, accessibility,
  responsive hardening, and bounded request/bundle budgets
- ✅ M15 Authentication and Security Hardening with normalized identities,
  database-backed JWT validation, rotating refresh sessions, replay-family
  revocation, memory-only access tokens, CSRF and exact-Origin controls,
  route-wide ownership and validation hardening, request/rate limits,
  production configuration checks, and security operations documentation
- ✅ Project-scoped RFI workflow with sequential numbering, due-date tracking,
  ownership enforcement, and dashboard workflow metrics
- ✅ Project-scoped Submittals workflow with sequential numbering, complete
  review states, date validation, ownership enforcement, and dashboard
  workflow metrics
- ✅ Project-scoped Punch Lists workflow with sequential numbering, complete
  priority and status handling, date validation, ownership enforcement, and
  dashboard workflow metrics
- ✅ Enhanced project-scoped Change Orders workflow with persistent numbering,
  data-preserving legacy compatibility, fixed-precision financial fields,
  lifecycle and schedule-impact tracking, complete frontend CRUD and
  filtering, and dashboard workflow and cost metrics
- ✅ M13 Document Management across Projects, Daily Logs, RFIs, Submittals,
  Punch Items, and Change Orders:
  - M13.0 Architecture Audit
  - M13.1 Backend Foundation
  - M13.2 Production Storage and Durable Cleanup
  - M13.3 Reusable Frontend Attachment System
  - M13.4 Project and Daily Log Pilot
  - M13.5 Remaining Resource Rollout
  - M13.6 Documentation and Closeout
- ✅ M16.1 Document Storage Foundation with generic local and S3-compatible
  providers, opaque sharded keys, project-owned document metadata,
  hierarchical folders, checksums, soft deletion, secure streaming, and
  version-ready fields
- ✅ M16.2 Project Document Explorer with nested navigation, breadcrumbs,
  bounded metadata search, filtering, sorting and pagination, recent
  documents, batch uploads with retry, details, authenticated downloads,
  soft deletion, accessibility, and responsive layouts
- ✅ Branded landing page and first-run demo seeding
- ✅ Icon system, confirmation dialogs, notifications, loading skeletons
- ✅ Scheduler showcase: WBS numbering, inline validation, critical path +
  float, federal-holiday calendar, today marker, keyboard grid navigation
- ✅ Engineering hardening: dashboard bundle optimization (chart library
  removed for CSS bars), error boundaries, App decomposition into feature
  hooks + router, targeted memoization and shared date utilities, backend
  DRY cleanup with TestClient API integration coverage

**Next**
- Weather-delay integration and resource loading
- Milestone tasks, Gantt dependency arrows, and timeline zoom

**Future possibilities (not committed scope)**
- Distributed rate limiting, password reset, email verification, MFA, OAuth,
  organizations, roles, audit logs, a same-site API domain, and expanded
  browser/security scanning
- Document and attachment version history, bulk download, thumbnails, and
  image galleries
- Drawing annotations, OCR, full-text document search, antivirus integration,
  and document approvals
- Direct multipart browser uploads and bucket-wide orphan scanning
- A built-in background worker and cleanup-job administration interface
- Project and Daily Log parent-deletion workflows

## Author

Built by [**WarscherProgramming**](https://github.com/WarscherProgramming) —
[construction-scheduler](https://github.com/WarscherProgramming/construction-scheduler).
