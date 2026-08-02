# Construction Drawing Management

M16.3 adds construction-specific metadata and workflow around the existing
document storage foundation. Drawing files remain ordinary project-owned
`Document` records and use the configured local or private S3-compatible
provider. M16.4 adds a secure, lazy-loaded PDF viewer without creating a
second file path or changing drawing persistence. M16.5 adds explicit links
between drawing context, Documents, and construction records while preserving
the specialized drawing lifecycle.

## Domain Model

- `DrawingSet` groups sheets and has `draft`, `active`, or `archived` status.
- `DrawingSheet` is a logical sheet within one set. Its status is `active`,
  `void`, or `archived`, and it points to the current revision.
- `DrawingRevision` links one sheet to one `Document`, stores its immutable
  revision metadata and sequence, and records superseding lineage.
- `DrawingIssue` represents a formal `draft`, `issued`, or `void` issuance.
- `DrawingIssueRevision` links an exact historical revision to an issue.

Sheet-number uniqueness is scoped to a drawing set. Comparison applies NFKC,
uppercase conversion, and removal of whitespace and hyphens, so `A-101`,
`A101`, and `a 101` conflict while the entered display value is retained.
Revision-code comparison applies NFKC, uppercase conversion, and whitespace
removal.

Disciplines are allowlisted as `G`, `C`, `L`, `A`, `I`, `S`, `M`, `P`, `FP`,
`E`, `T`, `FA`, `K`, `Q`, `V`, and `X`. Extending the list requires matching
schema, frontend-label, database, and migration review.

## Revision Transaction

Initial sheet creation and later superseding uploads are atomic from the API
perspective. The service authorizes the project-owned set or sheet, validates
PDF metadata and content, locks the parent row where supported, calculates
the next sequence, uploads through the document service without committing,
updates the prior current revision and sheet pointer, and commits once.

A partial unique index permits only one current revision per sheet. Sheet-row
locking serializes allocation on PostgreSQL, while unique sheet/code,
sheet/sequence, and current-revision constraints provide a final conflict
backstop. If metadata commit fails, the database rolls back and the uploaded
object is removed. SQLite tests prove rollback and constraints but cannot
prove PostgreSQL lock scheduling.

Old revisions remain downloadable and show their superseded timestamp,
successor, and issue memberships. Direct revision deletion and unrestricted
current-revision mutation are not exposed.

## Drawing Issues

Draft issue metadata and membership may change. An issue may include any
historical revision from a sheet in the same set, but only one revision from
that sheet. Issuing explicitly freezes membership; repeated issue requests
are idempotent. An issued issue can only be voided, repeated void requests are
idempotent, and history remains intact. Draft deletion is soft deletion.

## API

- `GET|POST /projects/{project_id}/drawing-sets`
- `GET|PATCH|DELETE /drawing-sets/{drawing_set_id}`
- `GET|POST /drawing-sets/{drawing_set_id}/sheets`
- `GET|PATCH|DELETE /drawing-sheets/{sheet_id}`
- `GET|POST /drawing-sheets/{sheet_id}/revisions`
- `GET /drawing-sheets/{sheet_id}/current-revision`
- `GET /drawing-revisions/{revision_id}/download`
- `GET|POST /drawing-sets/{drawing_set_id}/issues`
- `GET|PATCH|DELETE /drawing-issues/{issue_id}`
- `POST /drawing-issues/{issue_id}/revisions`
- `DELETE /drawing-issues/{issue_id}/revisions/{revision_id}`
- `POST /drawing-issues/{issue_id}/issue`
- `POST /drawing-issues/{issue_id}/void`
- `GET /projects/{project_id}/drawings`

The register searches bounded sheet number, title, current revision code, and
set name metadata with escaped SQL wildcards. It supports allowlisted set,
discipline, status, sorting, direction, limit, and offset parameters with
stable secondary ordering. Responses contain safe document IDs and display
metadata, never provider keys, buckets, paths, checksums, or internal state.

## Frontend Workflow

The lazy project route `#/projects/{projectId}/drawings` adds a Drawings item
to the existing project navigation. `useDrawings` owns project-keyed sets,
register, selected-set details, revisions, issues, mutations, cancellation,
and stale-response protection.

The page supports drawing-set creation, editing, and archival; sheet and first
revision registration; searchable/filterable/sortable pagination; controlled
revision upload; newest-first history and authenticated download; and draft,
issue, and void actions with confirmations. Mobile uses stacked register
records rather than page-level horizontal scrolling.

Dialogs use semantic headings, labeled controls, focus trapping, Escape
handling, and focus restoration. Current and superseded states and issue
membership are visible as text rather than color alone.

## Secure PDF Viewer

The protected route
`#/projects/{project_id}/drawings/sheets/{sheet_id}/revisions/{revision_id}/view`
opens the exact current or historical revision. The client fetches safe sheet
metadata, a bounded newest-first history, active sheets in the same set, and
one authenticated PDF Blob. It verifies project, sheet, and revision IDs
before requesting bytes. Browser Back/Forward uses the existing hash router;
no token, object key, provider URL, or filename appears in the route.

`useDrawingViewer` owns cancellation, stale-response rejection, PDF lifetime,
page, zoom, search, retry, and revision identity. The route is lazy loaded.
`pdfjs-dist` `6.2.108` renders the active page and selectable text; its worker
is emitted by Vite from `pdf.worker.min.mjs` and loaded same-origin. XFA and
eval support are disabled, and the UI does not render annotations, links,
forms, embedded files, launch actions, or PDF JavaScript.

The viewer supports first/previous/next/last and direct page navigation,
25%-400% zoom, 100% reset, fit width, fit page, native scrolling, revision
selection, active-set previous/next sheet navigation, metadata, and explicit
download. Scoped shortcuts apply only inside the viewer workspace: arrows or
PageUp/PageDown change pages, Home/End jump boundaries, `+`/`-` zoom, `0`
resets, and `f` fits width. Input controls ignore shortcuts.

At most one full-size page is rendered. The page rail contains at most 31
page controls and renders thumbnail canvases only for the current page and
two neighbors. Search extracts existing PDF text sequentially only after a
trimmed, literal, case-insensitive query (maximum 200 characters); image-only
drawings remain viewable and state that in-viewer searchable text is
unavailable. This browser search does not perform OCR.

M16.6 adds a separate project content index over each revision's existing
Document. Native embedded PDF text is extracted durably by page; image-only
pages enter an OCR provider boundary that is disabled in production. Viewer
metadata names these capabilities separately as `Viewer search` and `Project
index`, exposes the exact revision's extraction state, and links to the lazy
project search route. Opening index status or search does not refetch the
authorized PDF Blob.

The revision download route remains the binary endpoint. It streams from the
configured provider with `Content-Length`, PDF content type, safe attachment
disposition, `nosniff`, sandbox CSP, and `Cache-Control: private, no-store`.
Range requests are not implemented or claimed; the browser downloads the PDF
once per viewer session, and page rendering, zooming, searching, and explicit
download reuse that Blob. The optional open-in-new-tab action is omitted to
keep Blob URL lifetime deterministic.

Metadata, download, parsing, page rendering, thumbnail, search, revision
switch, corrupt PDF, worker failure, and encrypted-PDF states are handled
without exposing storage details. Password-protected/encrypted PDFs are not
opened and no password is requested or stored; an already authorized Blob
may still be downloaded. Source-PDF accessibility depends on the uploaded
file and is not claimed by the application.

### Performance and Verification

The existing 25 MiB drawing upload limit is unchanged. Revision history is
bounded at 100 records, navigation uses the active sheets from one drawing
set, the page rail mounts at most 31 controls, and only five thumbnail
canvases are eligible to render at once. Text extraction is not part of
initial load and proceeds one page at a time only after search begins. Full
page rendering remains limited to the selected page and caps device-pixel
ratio at 2.

The M16.4 production build emits a 447.92 kB raw / 133.39 kB gzip lazy viewer
chunk and a 1,262.39 kB raw / 374.85 kB gzip PDF worker. Main JavaScript is 275.87 kB raw /
84.62 kB gzip and CSS is 64.34 kB raw / 12.26 kB gzip. Relative to M16.3,
main gzip grows 0.42 kB and CSS gzip grows 1.24 kB; the PDF implementation is
otherwise isolated behind the viewer route. `pdfjs-dist` `6.2.108` is
Apache-2.0 licensed. The production dependency audit reports zero
vulnerabilities; the full development tree retains two high advisories in
existing build tooling (`brace-expansion` and `postcss`).

The M16.5 production build keeps the drawing viewer lazy at 448.85 kB raw /
133.62 kB gzip and adds a separate 17.96 kB raw / 5.45 kB gzip relationship
chunk. Relative to M16.4, viewer gzip changes by +0.23 kB, main gzip by +0.27
kB, and CSS gzip by +0.64 kB. Automated verification passes 433 frontend
tests across 62 files and 287 backend tests, plus 317 separately reported
backend subtests. Manual browser, responsive, large-fixture, and source-PDF
security checks remain explicitly unverified in the command-only
environment.

The M16.6 build keeps the viewer lazy at 450.07 kB raw / 133.87 kB gzip and
the PDF worker unchanged at 1,262.39 kB raw / 374.85 kB gzip. The separate
project document-search route is 9.91 kB raw / 2.84 kB gzip. Relative to
M16.5, viewer gzip grows 0.25 kB, main gzip 0.26 kB, and CSS gzip 0.63 kB.

## Drawing Relationships

The Drawing Register can open one relationship panel for the selected
Drawing Sheet. The viewer metadata area exposes an opt-in Related Records
section for the exact `drawing_revision`, including superseded historical
revisions. Relationships load only when that panel is opened; they do not add
a request per register row or PDF page. Creation and deletion refresh only
relationship state, so the authenticated PDF Blob is not fetched again.

Related drawing revisions navigate to the exact sheet/revision viewer route.
Drawing sets, sheets, and issues use the existing Drawing Register route.
Archived drawing records remain factual and viewable where the drawing domain
permits, while unavailable records cannot receive new links.

Generic relationships provide broader construction context. They do not
replace `DrawingIssueRevision` membership, `DrawingRevision` superseding
lineage, current-revision pointers, Document version lineage, or Folder
placement. The allowed matrix, resolver rules, and API are documented in
[`DOCUMENT_RELATIONSHIPS.md`](DOCUMENT_RELATIONSHIPS.md).

## Explorer and Retention

Drawing documents appear in the project explorer independently of drawing
classification. Explorer deletion of a referenced document returns `409`;
sets and sheets archive; revisions are retained; issued issues are voided.
This prevents dangling revision references and silent historical loss.

## Limitations

Drawings remain PDF-only and cannot be assigned from existing explorer
documents. The viewer does not provide HTTP range delivery, offline caching,
password entry, OCR, annotations, links/forms, measurements, overlays,
revision comparison, markups, or AI analysis. M16.6 project search is
server-side lexical search, not a replacement for the viewer's current-PDF
search, and production OCR remains unavailable.
Generic record relationships are now available, but relationship overlays,
automatic suggestions, and graph visualization are not. Manual visual and
source-PDF accessibility verification remains necessary in a working browser
environment.
