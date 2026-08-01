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
| `dashboard.png` | Populated Project Dashboard showing Project Summary, Follow-up Indicators, Attention Required, Upcoming Schedule, Workflow Analytics, and Recent Updates. Include readable RFI, Submittal, Punch Item, and Change Order states plus large Change Order values where practical. |
| `schedule-grid.png` | Schedule table view: a row selected (brand accent visible), one cell in inline-edit mode, at least one parent task with indented children. |
| `schedule-dnd.gif` | ~5 s: grab a task's drag handle, drag it two rows, drop; dates recalculate. |
| `login.png` | Logged-out landing page at desktop width: split panel with marketing copy, highlights, app preview, and the auth card. |
| `gantt.png` | Schedule → Gantt view of the demo project. |
| `first-run.gif` | ~6 s: first-run welcome screen → click "Load Sample Project" → progress bar filling → dashboard appears. Requires a fresh account. |
| `change-orders.png` | Populated Change Orders page: a generated `CO` number; create or edit workflow; proposed and approved amounts; schedule impact; lifecycle dates; multiple status badges; and, where practical, a readable legacy record. |
| `punch-lists.png` | Punch Lists page: populated Punch Items table with visible status and priority labels, an overdue indicator, and the create or edit workflow visible. |
| `drawing-register.png` | Populated Drawing Register with multiple disciplines, clear current revisions, set/filter controls, and sheet actions visible. |
| `drawing-history.png` | Revision History dialog showing one current and one superseded PDF revision, dates, successor information, issue membership, and View/Download actions. |
| `drawing-issues.png` | Drawing Issues section with a draft issue containing revisions and an issued or void issue showing frozen membership. |
| `drawing-viewer.png` | Secure Drawing Viewer showing a synthetic multipage sheet, selected thumbnail, current or superseded revision text, metadata panel, page/zoom/search controls, and no confidential drawing content. |
| `mobile.png` | Dashboard or a record page at ~390 px width: collapsed horizontal nav and stacked record cards. (Optional composite of two views side by side.) |

## Document Management captures

These are planned portfolio captures. M13.6 does not create or replace image
files.

| File | Page / workflow | State to capture | Viewport | Avoid | Portfolio value |
|---|---|---|---|---|---|
| `project-documents.png` | Project Settings → Project Documents | Populated panel with several synthetic file types and the upload target visible | 1440×900 | Real project/client names and confidential filenames | Shows the project-level document hub and reusable panel |
| `daily-log-attachments.png` | Daily Logs | One persisted log expanded with photos and a PDF; create form remains separate | 1440×900 | Faces, addresses, subcontractor details, and location metadata | Connects field reporting to supporting evidence |
| `rfi-attachments.png` | RFIs | Selected persisted RFI with a drawing and response exhibit listed | 1440×900 | Proprietary drawings and real RFI content | Demonstrates contextual document access without a new detail route |
| `submittal-attachments.png` | Submittals | Selected Submittal with product data, PDF package, and download actions | 1440×900 | Manufacturer-confidential or project-specific packages | Shows mixed document formats in a review workflow |
| `punch-item-attachments.png` | Punch Items | Selected item with synthetic JPEG/PNG evidence and its browser preview opened | 1440×900 | Faces, geolocation, unit numbers, and real deficiency photos | Highlights image evidence and authenticated preview |
| `change-order-attachments.png` | Change Orders | Selected Change Order with cost backup and drawing exhibit alongside lifecycle data | 1440×900 | Real pricing, signatures, account data, and contract exhibits | Connects financial workflow records to supporting backup |
| `attachment-upload-results.png` | Any attachment-enabled workflow | Sequential multiple-file upload showing progress or a synthetic partial-success result | 1440×900 | Local filesystem paths and sensitive error details | Demonstrates resilient multi-file UX rather than an idealized happy path |
| `attachment-delete-confirmation.png` | Any attachment-enabled workflow | Filename-specific accessible confirmation dialog with the background panel visible | 1440×900 | Sensitive filenames or document contents | Shows deliberate destructive-action and focus-management design |
| `attachment-mobile.png` | RFI, Punch Item, or Daily Log attachments | One open panel with a long synthetic filename and wrapped actions | 390×844 | Notification previews, browser account UI, and real filenames | Proves the shared attachment workflow remains usable on site-sized screens |

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
