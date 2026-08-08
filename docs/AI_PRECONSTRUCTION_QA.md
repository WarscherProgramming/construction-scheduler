# AI Preconstruction Manual QA Guide

Use synthetic projects, users, documents, and PDFs. Never use customer
documents, real drawings, or production credentials in a capture or a defect
report. Record each item as **Pass**, **Fail**, or **Not Verified** with
browser, viewport, environment, release commit, and UTC time.

Automated closeout verification passed in full. The live-workflow, responsive,
and cross-browser items below were **Not Verified** during M18.7 because no
controlled authenticated browser harness or test deployment was available. They
are listed so the gap is explicit rather than implied.

---

## Setup

- [ ] Apply Alembic through `f3d6a8b2c517`; expected: one head,
  `current == head`, `alembic check` reports no drift.
- [ ] Confirm production values `PRECONSTRUCTION_AI_ENABLED=false`,
  `PRECONSTRUCTION_AI_PROVIDER=disabled`,
  `PRECONSTRUCTION_AI_FAKE_PROVIDER_ALLOWED=false`, `DOCUMENT_OCR_ENABLED=false`.
- [ ] Confirm the preparation cron is scheduled and the **analysis cron is
  not**.
- [ ] Create User A with Project A and User B with Project B; expected: no
  shared access.
- [ ] Prepare a synthetic specification PDF, a proposal PDF, two revisions of
  one drawing sheet, an image-only PDF, and an oversized PDF.

## Review sets and sources

- [ ] Create, rename, and archive a review set; expected: names unique per
  project case-insensitively, archived sets read-only.
- [ ] Add document and drawing-revision sources; expected: role and category
  shown, role never inferred.
- [ ] Change a role while draft, then after the first run; expected: editable
  while draft, 409 once locked.
- [ ] Soft-remove an unused draft source; expected: removed, and a second
  active entry for the same logical source is refused.
- [ ] Open a source link; expected: navigates to the correct document or
  drawing revision.

## Preparation and content

- [ ] Prepare each source; expected: pending → completed with page and segment
  counts, no storage or OCR request.
- [ ] Run the preparation cron with a pending run; expected: finite claim,
  clean exit, no daemon.
- [ ] Re-prepare after replacing the document; expected: source reports
  **stale**, a new snapshot is created, and the historical snapshot survives.
- [ ] Prepare the image-only PDF; expected: bounded `no_searchable_text`
  failure naming disabled OCR, no crash.
- [ ] Prepare the oversized PDF; expected: bounded page/text/segment limit
  failure.
- [ ] Open the Content Inspector; expected: plain text, `Cache-Control:
  no-store`, no PDF-worker or binary request.
- [ ] Cancel and retry a preparation run; expected: correct terminal states,
  append-only attempt history.

## Assertions

- [ ] Load the scope taxonomy; expected: categories, kinds, and version shown;
  deprecated concepts hidden from search but still resolvable.
- [ ] Author a manual assertion with evidence; expected: `origin=manual`, no
  confidence, evidence excerpt derived server-side.
- [ ] Accept, reject, and flag assertions; expected: append-only history, note
  required for rejection and reversal.
- [ ] Supersede an assertion; expected: new row, prior row retained and marked
  superseded.
- [ ] Confirm no assertion text is editable after creation.

## Comparison

- [ ] Create a comparison plan; expected: roles validated against the
  comparison type, configuration hashed.
- [ ] Review readiness; expected: deterministic — refresh twice and confirm the
  payload is identical — with separate deterministic and provider availability.
- [ ] Run a comparison with the provider disabled; expected: succeeds.
- [ ] Confirm the plan locks on first run and archived plans are read-only.
- [ ] Re-run the same plan; expected: a new finding set, identical manifest and
  content hashes, prior set untouched.
- [ ] Re-run with manifest reuse enabled; expected: the existing set is
  returned, `manifest_reused` true, no new row.
- [ ] Change one assertion review, then re-run with reuse enabled; expected:
  reuse declines and a new set is produced.
- [ ] Inspect a finding; expected: match reasons, both sides, evidence excerpts
  as inert plain text, Content Inspector links.
- [ ] Confirm severity, status, origin, and match class are readable as text
  with colour removed.
- [ ] Confirm no bulk-accept and no one-click RFI or Change Order control
  exists anywhere.

## Follow-up actions

- [ ] Expand an accepted finding; expected: follow-up panel with one button per
  available action and no bulk control.
- [ ] Expand a non-accepted finding; expected: the panel states only an
  accepted finding can raise a follow-up.
- [ ] Raise an RFI follow-up; expected: server draft prefilled, editable,
  states that nothing is created or sent.
- [ ] Create the RFI in the RFI workflow, then link it; expected: link
  succeeds, target identifier shown.
- [ ] Attempt to link User B's RFI; expected: 404 without leaking existence.
- [ ] Complete and then attempt to reopen; expected: terminal, 409.
- [ ] Cancel without a note; expected: refused.
- [ ] Reverse the finding's review; expected: the follow-up is retained and
  flagged, new follow-ups refused.

## Execution metrics

- [ ] Open the Execution panel; expected: exact pair count, budget with a
  textual within/exceeded state, last-run duration, reuse indicator.
- [ ] With no cost rate configured; expected: **"No rate configured"**, never a
  zero.
- [ ] Narrow the pair budget below the population; expected: readiness blocks
  and the run is refused, not truncated.
- [ ] Request `?evidence_limit=0`; expected: smaller payload, empty evidence
  arrays.

## Evaluation

- [ ] Run `python -m app.commands.run_preconstruction_evaluation`; expected:
  exit 0, all cases pass, digest printed.
- [ ] Run with `--json`; expected: machine-readable report.
- [ ] Confirm the command opens no database connection and requires no
  provider.

## Authorization and session matrix

- [ ] For all 49 preconstruction routes as User B against Project A; expected:
  403.
- [ ] Every nested identifier reached through User B's own project; expected:
  404, no existence leak.
- [ ] Unauthenticated; expected: 401.
- [ ] `POST`, `PUT`, `DELETE` on `/execution-metrics`; expected: 405.
- [ ] Client-supplied `status`, `origin`, hashes, or reviewer identity in any
  mutation body; expected: 422.
- [ ] Expired access token during a long review session; expected: single-flight
  refresh, no duplicate submission.

## Accessibility

- [ ] Keyboard-only path: review set → source → assertion review → comparison
  → finding review → follow-up.
- [ ] Focus traps and Escape in all seven dialogs.
- [ ] Screen-reader names for every list, group, and metric block.
- [ ] Colour removed: severity, status, origin, match class, budget state, and
  follow-up status all still readable.
- [ ] 200% zoom without horizontal scroll.

## Responsive matrix

- [ ] 1440, 1024, 768, and 375 px widths across the workspace, both panels, and
  all dialogs.

## Browser and production matrix

- [ ] Chrome, Firefox, Safari/WebKit, Edge.
- [ ] Browser Back through the lazy preconstruction route.
- [ ] Two tabs, one logout.
- [ ] Production build served from the deployed origin with exact-Origin CORS.

## Closeout

- [ ] Record every Pass/Fail/Not Verified with environment and commit.
- [ ] File defects with synthetic reproduction only.
- [ ] Confirm no capture contains customer content or credentials.

---

## Screenshot checklist

Capture at 1440 px unless stated. Use the synthetic *Riverside Medical Center —
Phase 2* demo project. **Every capture must contain synthetic data only.**

| # | File | Shot | Must show |
|---|---|---|---|
| 1 | `preconstruction-review-set.png` | Review set detail | Sources with roles, preparation states, readiness |
| 2 | `preconstruction-readiness.png` | Readiness panel | Blockers, warnings, "AI provider is disabled" |
| 3 | `preconstruction-content-inspector.png` | Content Inspector | Plain-text segments with page/segment coordinates |
| 4 | `preconstruction-assertions.png` | Assertion workspace | Concepts, evidence counts, review states |
| 5 | `preconstruction-assertion-review.png` | Review dialog | Decision options, reason codes, note field |
| 6 | `preconstruction-comparison.png` | Comparison workspace | Plan selector, readiness, summary counts |
| 7 | `preconstruction-finding-detail.png` | Finding detail | Match reasons, both sides, evidence excerpts |
| 8 | `preconstruction-follow-up.png` | Follow-up panel | Action buttons, "FieldFlow creates no RFI…" notice |
| 9 | `preconstruction-execution.png` | Execution panel | Pair budget, duration, "No rate configured" |
| 10 | `preconstruction-mobile.png` | 375 px workspace | Stacked layout, readable status text |

**Before publishing any capture:** confirm no real project name, address,
company, drawing number, or person appears; confirm no token, cookie, or URL
credential is visible; confirm the advisory framing is legible in shots 6–8, so
a reader cannot mistake a finding for a confirmed omission.
