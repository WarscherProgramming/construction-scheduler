# Screenshot capture checklist

The root README references the files below. Drop captures into this folder
with these exact names and the README completes itself.

## Setup (all captures)

- Load the live app (or `npm run dev`) in a clean browser window, **~1440×900**
  viewport, 100% zoom, light theme.
- Sign in and use the seeded demo project **Riverside Medical Center —
  Phase 2** (First-run → "Load Sample Project") so every view has data.
- Prefer PNG for stills; GIFs ≤ 8 seconds, ≤ 5 MB (record with e.g. ScreenToGif
  or Kap).

## Manifest

| File | View / state to capture |
|---|---|
| `dashboard.png` | Project dashboard, top of page: Today's Focus card with items, health gauge, all 5 KPI tiles visible. Hero image — make it count. |
| `schedule-grid.png` | Schedule table view: a row selected (brand accent visible), one cell in inline-edit mode, at least one parent task with indented children. |
| `schedule-dnd.gif` | ~5 s: grab a task's drag handle, drag it two rows, drop; dates recalculate. |
| `login.png` | Logged-out landing page at desktop width: split panel with marketing copy, highlights, app preview, and the auth card. |
| `gantt.png` | Schedule → Gantt view of the demo project. |
| `first-run.gif` | ~6 s: first-run welcome screen → click "Load Sample Project" → progress bar filling → dashboard appears. Requires a fresh account. |
| `change-orders.png` | Change Orders page: records visible with status badges, a filter applied, and the delete confirmation dialog open. |
| `mobile.png` | Dashboard or a record page at ~390 px width: collapsed horizontal nav and stacked record cards. (Optional composite of two views side by side.) |

## Tips

- Crop out the browser chrome (or use a clean device frame consistently).
- Take captures after data loads — no skeletons visible unless intentional.
- Re-capture `dashboard.png` whenever the dashboard design changes; it is the
  first image recruiters see.
