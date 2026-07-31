# Construction Drawing Management

M16.3 adds construction-specific metadata and workflow around the existing
document storage foundation. Drawing files remain ordinary project-owned
`Document` records and use the configured local or private S3-compatible
provider.

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

## Explorer and Retention

Drawing documents appear in the project explorer independently of drawing
classification. Explorer deletion of a referenced document returns `409`;
sets and sheets archive; revisions are retained; issued issues are voided.
This prevents dangling revision references and silent historical loss.

## Limitations

M16.3 is upload-only and PDF-only. It does not assign existing documents,
render PDFs, generate thumbnails, extract metadata, compare revisions, add
markups or relationships, search file contents, or implement OCR or AI
analysis. Those capabilities are deferred beyond this phase.
