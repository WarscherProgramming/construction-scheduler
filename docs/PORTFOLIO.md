# FieldFlow — Portfolio Copy

Ready-to-use descriptions for resumes, portfolio sites, and LinkedIn.
Keep the metrics in sync with the repo (currently **266 tests: 188 frontend +
78 backend**).

---

## Resume

### One-liner

> FieldFlow — full-stack construction scheduling and field-management SaaS
> (React 19, FastAPI, PostgreSQL) with a drag-and-drop CPM-style scheduler,
> executive dashboard, enhanced project-scoped Change Order, RFI, Submittal,
> and Punch List workflows, and 266 automated tests.

### Resume bullets

> **FieldFlow — Construction Planning & Field Management SaaS** · React 19,
> FastAPI, PostgreSQL, SQLAlchemy, Vite · [live demo](https://construction-scheduler-eight.vercel.app)
>
> - Built a spreadsheet-style scheduling engine with FS/SS dependencies, lag,
>   workday/holiday-aware date math, task hierarchy, and keyboard-accessible
>   drag-and-drop reordering, plus Gantt visualization and PDF export.
> - Designed an accessible design system (15+ reusable components: dialogs
>   with focus traps, skeleton loading, toasts, icon system) and an executive
>   dashboard of client-side derived insights — health scoring, attention
>   lists, and an activity feed — without adding backend endpoints.
> - Delivered a project-scoped RFI register with permanent sequential
>   numbering, Open/Pending/Closed workflow, due-date and overdue tracking,
>   responsible-company assignment, dashboard health metrics, and
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
> - Implemented JWT authentication with expiry-aware session UX, client-side
>   demo-data onboarding through the public API, and 266 automated tests
>   (Vitest/RTL + pytest) run against every change.

### Portfolio-site paragraph

> FieldFlow is a full-stack construction planning platform I designed and
> built end-to-end: a React 19 SPA over a FastAPI/PostgreSQL backend. The
> centerpiece is a spreadsheet-fast scheduler — inline cell editing,
> Finish-to-Start/Start-to-Start dependencies with lag, workday and federal
> holiday calendars, task hierarchy, and drag-and-drop reordering that works
> from the keyboard — rendered as both an editable grid and a Gantt chart with
> PDF export. Around it sits a complete field-management suite (daily logs,
> inspections, delays, enhanced Change Orders, RFIs, Submittals, Punch Lists)
> and an executive dashboard that answers
> a superintendent's first question of the day: what needs my attention? The
> project emphasizes production polish: a token-based accessible design
> system, first-run onboarding that seeds a realistic demo project, JWT auth
> with graceful session expiry, and 266 automated tests across the stack.

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
> Submittal, and Punch List workflows with dashboard health metrics
>
> Under the hood: React 19 + Vite, FastAPI + SQLAlchemy + PostgreSQL, JWT
> auth, an accessible component design system, and 266 automated tests.
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
> workflows, accessible design system, 266 automated tests. Live demo seeds a
> complete sample project in seconds.

---

## Interview talking points

1. **Timezone-safe scheduling.** Dates are handled as local `YYYY-MM-DD`
   values end-to-end (no UTC drift), with workday math that skips weekends
   and federal holidays — a classic real-world bug class, designed out.
2. **Honest derived metrics.** Tasks have no completion field, so the
   dashboard reports *timeline elapsed* and a *needs-attention* list instead
   of pretending to know percent-complete — labels match what the data can
   actually support, and all derivations are pure, unit-tested functions.
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
