# FieldFlow

**Construction planning and field management, in one place.**

FieldFlow gives superintendents, project managers, and project engineers a
single source of truth for the schedule, the field, and the paper trail —
a spreadsheet-fast scheduler, an executive dashboard, and complete field
records (daily logs, inspections, delays, change orders).

![React 19](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white&labelColor=20232a)
![FastAPI](https://img.shields.io/badge/FastAPI-0.1x-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169e1?logo=postgresql&logoColor=white)
![Tests](https://img.shields.io/badge/tests-91%20passing-2ea44f)
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
3. You land on the **executive dashboard**: Today's Focus, a project-health
   gauge, schedule health, and an activity feed.

### The 90-second tour

1. **Dashboard** — scan Today's Focus ("4 items need your attention"), the
   health gauge, and KPI tiles.
2. **Schedule** — click any cell to edit inline (Enter saves, Escape cancels),
   select a row, **drag to reorder**, indent/outdent to build a hierarchy.
3. Toggle the **Gantt** view, then **Export Schedule as PDF**.
4. **Change Orders** — filter by status, delete a record, and meet the
   accessible confirmation dialog.
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
- **JWT authentication** with expiry-aware session handling (stale API errors
  are suppressed and replaced by a single "session expired" notice).
- **Interactive scheduler**: spreadsheet-style inline editing, Finish-to-Start
  and Start-to-Start dependencies with lag, workday/holiday-aware date math,
  parent/child hierarchy, and keyboard-accessible drag-and-drop reordering
  (dnd-kit).
- **Dynamic Gantt chart** rendered from the same task data, plus one-click PDF
  export.
- **Executive dashboard** of derived insights — project-health gauge,
  timeline-elapsed schedule health, attention lists, and a merged activity
  feed — computed client-side from existing APIs (no bespoke endpoints).
- **Accessible design system**: tokens, reusable UI primitives (Button, Card,
  Sidebar, PageHeader, Icon, ConfirmDialog, Skeleton), skip links, focus
  management, `aria-current` navigation, and screen-reader-labeled loading
  states.
- **Responsive UI** from desktop rail navigation down to stacked mobile record
  cards.
- **Client-side onboarding**: first-run detection seeds a realistic demo
  project through the public API with visible progress — the app is never
  empty.
- **Automated testing: 91 tests** — 70 frontend (Vitest + React Testing
  Library, behavior- and accessibility-focused) and 21 backend (pytest,
  covering the scheduling engine, services, migrations, and CORS).

## Architecture at a Glance

```text
┌────────────────────┐        HTTPS / JSON        ┌─────────────────────┐
│   React 19 SPA     │  ───── REST + JWT ─────▶   │   FastAPI (Python)  │
│   Vite · dnd-kit   │  ◀──── JSON responses ──   │   api → services →  │
│   Recharts         │                            │   domain → models   │
│   (Vercel)         │                            │   (Render)          │
└────────────────────┘                            └──────────┬──────────┘
        │                                                    │ SQLAlchemy
        │  localStorage: JWT, onboarding flag                │ + Alembic
        ▼                                                    ▼
  hash-based routes                               ┌─────────────────────┐
  (refresh-safe, no                               │     PostgreSQL      │
  rewrite rules)                                  └─────────────────────┘
```

**How data flows:** the SPA authenticates against `/auth` and stores a JWT;
every request carries it via a small fetch wrapper that also centralizes
401 handling. Page containers call REST endpoints (`/projects/{id}/tasks`,
`/daily-logs`, `/inspections`, `/notes-delays`, `/change-orders`, …); the
FastAPI service layer applies the scheduling rules (dependencies, lag,
workday/holiday calendars) and persists through SQLAlchemy models managed by
Alembic migrations. Responses return the full recalculated task set, so the
grid, Gantt, and dashboard always render from one consistent source. Dashboard
insights (health score, attention lists, activity feed) are **derived
client-side** in pure, unit-tested functions — no duplicate reporting API.

## Features

**Scheduling**
- Spreadsheet-style schedule editing with full keyboard support
- Finish-to-Start and Start-to-Start dependencies with lag (`12`, `12+3`, `12SS+4`)
- Workday scheduling that skips weekends and federal holidays
- Parent/child task hierarchy with indent/outdent and collapse
- Drag-and-drop ordering (pointer and keyboard)
- Gantt visualization and PDF schedule export
- Reusable schedule templates

**Executive dashboard**
- Today's Focus: activities starting today, inspections due, delays, pending COs
- Project-health gauge (green / amber / red) from a transparent heuristic
- Schedule health, attention list, upcoming tasks and inspections
- Unified project activity feed with "what changed since yesterday" markers

**Field records**
- Daily logs, inspections, notes & delays, and change orders
- Search, filtering, status badges, and responsive record cards
- Project-company management

**Product quality**
- Branded landing/login, first-run onboarding with demo seeding
- Icon system, confirmation dialogs, toast notifications, loading skeletons
- WCAG-minded semantics: skip links, focus traps, `aria-live` announcements

## Screenshots

| | |
|---|---|
| ![Executive dashboard](docs/screenshots/dashboard.png) *Executive dashboard — Today's Focus, health gauge, KPIs* | ![Schedule grid](docs/screenshots/schedule-grid.png) *Spreadsheet-style schedule with hierarchy and inline editing* |
| ![Drag-and-drop reordering](docs/screenshots/schedule-dnd.gif) *Drag-and-drop task reordering* | ![Landing page](docs/screenshots/login.png) *Split-panel landing and login* |
| ![Gantt view](docs/screenshots/gantt.png) *Gantt visualization* | ![First-run onboarding](docs/screenshots/first-run.gif) *First-run onboarding seeds a full sample project* |
| ![Change orders](docs/screenshots/change-orders.png) *Change orders — filters, badges, confirm dialog* | ![Responsive layout](docs/screenshots/mobile.png) *Responsive rail and record cards* |

*(Capture checklist: [docs/screenshots/README.md](docs/screenshots/README.md))*

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, dnd-kit, Recharts, Inter (self-hosted) |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic |
| Database | PostgreSQL |
| Auth | JWT (OAuth2 password flow) |
| Testing | Vitest + React Testing Library (70), pytest (21) |
| Hosting | Vercel (frontend) · Render (API + migrations) |

## Testing

**91 automated tests.**

- **Frontend (70)** — Vitest + React Testing Library. Tests target behavior
  and accessibility: roles and names, keyboard flows (Enter/Escape editing,
  focus traps), derived dashboard metrics, demo-seeding orchestration, and
  loading/empty/error states.
- **Backend (21)** — pytest. Covers the workday scheduling engine
  (dependencies, lag, holidays), task services, relationship migrations, and
  CORS configuration.

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
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
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

Set `VITE_API_URL` when pointing at a deployed API.

## Deployment

- **Frontend — Vercel.** Hash-based routes keep every module refresh-safe with
  zero rewrite configuration. Live at
  [construction-scheduler-eight.vercel.app](https://construction-scheduler-eight.vercel.app).
- **Backend — Render.** [`backend/render.yaml`](backend/render.yaml) defines
  the web service, runs Alembic migrations on deploy, sets the health check,
  and pins the production CORS origin.

## Roadmap

**Shipped**
- ✅ Design system, tokens, and reusable UI component layer
- ✅ Persistent project navigation shell with active-page state
- ✅ Executive dashboard with derived health/attention insights
- ✅ Branded landing page and first-run demo seeding
- ✅ Icon system, confirmation dialogs, notifications, loading skeletons

**Next**
- Scheduler showcase: critical-path highlighting, inline validation, today marker
- Engineering hardening: state decomposition, chart code-splitting
- RFIs and submittals, punch lists, document management
- Weather-delay integration and resource loading

## Author

Built by [**WarscherProgramming**](https://github.com/WarscherProgramming) —
[construction-scheduler](https://github.com/WarscherProgramming/construction-scheduler).
