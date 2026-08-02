# M16 Manual QA Guide

Use synthetic projects, users, records, filenames, PDFs, and images. Never use
customer documents or production credentials in captures or defect reports.
Record each item as Pass, Fail, or Not Verified with browser, viewport,
environment, release commit, and UTC time.

Automated closeout verification passed, but the live workflow, responsive,
and cross-browser items below were not executed during M16.7 because no
controlled authenticated browser harness or test deployment was available.

## Setup

- [ ] Apply Alembic through `e4b7c2d9f651`; expected: one head, current=head,
  and no schema drift.
- [ ] Configure a private storage namespace and both finite schedules;
  expected: API, extraction, and cleanup jobs share database/provider values.
- [ ] Create User A with Project A and User B with Project B; expected: no
  shared project access.
- [ ] Prepare a one-page text PDF, multipage text PDF, image-only PDF, mixed
  PDF where practical, long PDF, corrupt PDF, encrypted PDF, PNG, JPEG, and
  WebP; expected: every file is synthetic and below configured limits unless
  explicitly testing rejection.

## Storage

- [ ] Upload to local or configured private S3 storage; expected: safe metadata
  and opaque provider key, with no public object access.
- [ ] Exercise `upload`, `download`, `exists`, `metadata`, and `delete` on a
  disposable object; expected: content type/checksum metadata are retained and
  already-missing deletion is idempotent.
- [ ] Upload two files with the same display filename; expected: both persist
  under distinct opaque keys.
- [ ] Try traversal, path separators, reserved names, controls, empty files,
  bad signatures, MIME/extension mismatch, and oversized content; expected:
  bounded safe rejection with no object leak.
- [ ] Simulate metadata commit failure and provider cleanup failure; expected:
  no active Document and one durable cleanup job.
- [ ] Run bounded attachment cleanup; expected: object removal or safe retry,
  no provider metadata in client responses or logs.

## Project Document Explorer

- [ ] Open `#/projects/{project_id}/documents`; expected: one page heading,
  root breadcrumbs, tree, recent list, and bounded table with no row fan-out.
- [ ] Create two nested folders and move through tree/breadcrumbs; expected:
  correct active location, counts, Back/Forward behavior, and no stale folder.
- [ ] Attempt duplicate active sibling names; expected: controlled conflict.
- [ ] Upload one file by picker; expected: progress/result announcement and
  refreshed listing, tree counts, and recent files.
- [ ] Upload multiple files and use drag-and-drop; expected: sequential per-file
  results and no page-level shift or inaccessible drop-only action.
- [ ] Force one file in a batch to fail and retry it; expected: successful files
  remain and only failed files retry.
- [ ] Search literal `%`/`_`, filter type/MIME/extension, sort every allowlisted
  field/direction, and paginate; expected: deterministic bounded results.
- [ ] Open details, download, close with Escape, and restore focus; expected:
  safe metadata and filename, no provider fields, and authenticated Blob flow.
- [ ] Soft-delete an unreferenced document; expected: explicit confirmation,
  removal from active explorer/search/download, and retained object policy.
- [ ] Try deleting a drawing revision Document; expected: `409` and intact
  drawing history.
- [ ] Switch projects during a delayed request; expected: old data clears and
  the stale response cannot render.
- [ ] Expire the session and simulate network failure; expected: existing auth
  recovery/global feedback behavior and usable unrelated navigation.

## Drawing Sets and Sheets

- [ ] Open `#/projects/{project_id}/drawings`; expected: sets and one bounded
  register request, visible empty/loading/error states, and no revision fan-out.
- [ ] Create and edit a set, try a duplicate active name, then archive it;
  expected: strict validation, safe conflict, and factual archived state.
- [ ] Create `A-101` with the first PDF revision; expected: one Document, one
  sheet, one current revision, and explorer visibility.
- [ ] Try `A101` or `a 101` in the same set; expected: normalized duplicate
  rejection while entered display values otherwise remain intact.
- [ ] Try an unsupported discipline or non-PDF file; expected: controlled
  rejection with no partial sheet/Document.
- [ ] Upload revision 2; expected: prior revision superseded once, exact one
  current revision, updated sheet pointer, and retained history/downloads.
- [ ] Force storage/database failure during revision upload; expected: rollback,
  object cleanup, and unchanged prior current revision.
- [ ] Search, filter, sort, and paginate the register; expected: stable bounded
  rows with no storage/checksum fields.

## Drawing Issues

- [ ] Create a draft issue; expected: editable metadata and empty membership.
- [ ] Add exact current and historical revisions from the same set; expected:
  at most one revision per sheet and retained exact identities.
- [ ] Remove draft membership; expected: issue remains and revision is unchanged.
- [ ] Try a cross-set revision or duplicate sheet membership; expected: safe
  rejection.
- [ ] Issue the draft and repeat the action; expected: frozen membership and
  idempotent issued state.
- [ ] Try editing membership after issue; expected: lifecycle conflict.
- [ ] Void an issued issue and repeat; expected: idempotent void with history
  retained.

## Secure PDF Viewer

- [ ] Open the exact current and historical viewer hashes; expected: project,
  sheet, and revision identities validate before one authenticated PDF request.
- [ ] Test first/previous/next/last, direct page entry, thumbnails, Home/End,
  arrows, and PageUp/PageDown; expected: bounded navigation with no page fetch.
- [ ] Test zoom out/in, 100% reset, fit width, fit page, `+`, `-`, `0`, and `f`;
  expected: 25%-400% bounds and shortcuts ignored inside form controls.
- [ ] Search literal embedded text and navigate matches; expected: sequential
  in-Blob search with no server extraction request.
- [ ] Open an image-only PDF; expected: viewable page and factual no-searchable-
  text message.
- [ ] Open corrupt and encrypted PDFs; expected: safe error, metadata and
  authorized download retained, no password collection.
- [ ] Switch sheet/revision and use Back/Forward; expected: exact route history,
  stale Blob/request cleanup, and one binary request per revision session.
- [ ] Inspect network/security behavior; expected: same-origin worker, no token,
  key, provider URL, external resource, annotation/form/script execution, or
  page-level binary request.
- [ ] Download after viewing; expected: loaded Blob reuse and object URL cleanup.

## Relationships

- [ ] Create RFI references Drawing Revision; expected: directional forward and
  reverse labels and exact viewer navigation.
- [ ] Create Submittal references Drawing Sheet; expected: register navigation.
- [ ] Create Punch Item located on Drawing Revision; expected: exact revision
  navigation.
- [ ] Create Change Order originated from RFI; expected: direction retained.
- [ ] Create Daily Log documents Punch Item; expected: perspective-aware labels.
- [ ] Create Document associated with Submittal; expected: symmetric behavior.
- [ ] Search candidates by metadata with keyboard listbox interaction; expected:
  bounded same-project results only.
- [ ] Try self, disallowed, duplicate/reverse-duplicate, unavailable, and
  cross-project pairs; expected: strict safe rejection.
- [ ] Delete a relationship; expected: target unchanged and link removed.
- [ ] View an archived drawing or unavailable target; expected: factual status,
  no leaked fields, and navigation only where the domain permits.
- [ ] Confirm opening relationships does not refetch a PDF or add dashboard,
  list-row, or per-result requests.

## Extraction and Search

- [ ] Upload a text PDF and run one bounded processor; expected: queued claim,
  native page text, completed/searchable status, and no content in logs.
- [ ] Upload image-only PDF, PNG, JPEG, and WebP with production OCR disabled;
  expected: factual unavailable/warning state, not searchable OCR content.
- [ ] Exercise mixed, blank-page, corrupt, encrypted, long, and limit-exceeding
  files; expected: completed-with-warning, unavailable, or safe failure matching
  the bounded parser contract.
- [ ] Interrupt a processor and wait for lease expiry; expected: a new token can
  recover it and the stale token cannot finalize.
- [ ] Force retryable and terminal failures; expected: bounded attempts/backoff,
  max-attempt stop, and safe category-only logs.
- [ ] Reprocess a supported file; expected: `202`, duplicate/rate-limit guards,
  checksum-current result, and transactional page replacement.
- [ ] Search exact filename, sheet number, drawing title, revision code, product
  code, and embedded content; expected: stable lexical ranking and safe snippets.
- [ ] Test no results, page filters, scope, set, discipline, method,
  current/superseded, and pagination; expected: bounded correct results.
- [ ] Open document and exact drawing result targets; expected: correct project
  route and page context without a search-time binary or PDF worker request.
- [ ] Search text containing HTML/script-like content; expected: plain text only,
  bounded match ranges, no unsafe HTML or full-page response.

## Authorization and Session Matrix

- [ ] As User A, exercise upload/list/explorer/metadata/download/delete/folders,
  extraction status/reprocess, all drawing workflows, relationships/candidates,
  search, and result navigation; expected: owned success.
- [ ] As User B, repeat with Project A IDs and guessed direct IDs; expected:
  project denial or safe not found with no metadata/byte/search leakage.
- [ ] Pair User A project IDs with User B document/drawing/relationship IDs;
  expected: no cross-project nested access or relationship creation.
- [ ] Expire access then refresh sessions during JSON and binary requests;
  expected: one bounded refresh/retry, memory-only access token, and no token URL.
- [ ] Test missing/mismatched CSRF and foreign Origin on mutation/refresh;
  expected: rejection while exact configured Origin succeeds.

## Accessibility

- [ ] Confirm one `h1` per explorer, drawings, viewer, and search page with
  logical section/dialog headings and semantic tables/lists.
- [ ] Operate all controls by keyboard with visible focus; expected: no keyboard
  trap except intentional modal focus containment.
- [ ] Open/close every M16 dialog with keyboard and Escape; expected: initial
  focus, containment, and restoration to the trigger.
- [ ] Inspect labels/names for upload, folder, filters, viewer toolbar, page,
  zoom, relationship, search, retry, download, and delete controls.
- [ ] Confirm loading, upload, mutation, extraction, and search status updates
  are announced and never communicated by color alone.
- [ ] Use 200% browser zoom; expected: reachable actions, legible content, and
  no text/control overlap. Do not claim accessibility of source PDFs.

## Responsive Matrix

- [ ] At 320, 375, 768, 1024, 1280, and 1600 px, inspect explorer, register,
  sheet/revision forms, issues, viewer, relationship dialogs, and search.
- [ ] Use long synthetic filenames, sheet titles, revision lists, and snippets;
  expected: wrapping or internal scrolling with no page-level horizontal
  overflow.
- [ ] Verify toolbar wrapping, viewer internal scroll, dialog fit, reachable
  actions, visible focus, and practical touch targets at every narrow viewport.

## Browser and Production Matrix

- [ ] Chromium: PDF worker, Blob download/revoke, canvas/text layer,
  drag-and-drop, dialogs, cookies, binary auth, and Back/Forward pass.
- [ ] Firefox: repeat the same matrix; record any worker/Blob differences.
- [ ] Safari/WebKit: repeat the same matrix, especially cross-site cookies,
  authenticated binary requests, and object URL cleanup.
- [ ] Confirm production frontend headers, exact credentialed CORS, CSRF,
  refresh cookies, API health, private S3 behavior, extraction cron, cleanup
  schedule, migration current/head, and live search/extraction before approval.
- [ ] Confirm browser network logs contain no provider URLs/keys, tokens in URLs,
  external PDF resources, row fan-out, search binaries, or duplicate PDF loads.

## Closeout

- [ ] Remove synthetic objects, temporary schemas/databases, browser profiles,
  generated PDFs/images/text dumps, logs, screenshots not intended for the
  repository, build output, and coverage artifacts.
- [ ] Run full suites, lint, build, audits, Alembic current/heads/check, command
  smokes, secret/content scan, `git diff --check`, and repository status.
- [ ] Record merge readiness separately from production verification; expected:
  unexecuted live items remain `Not Verified`, never inferred from unit tests.
