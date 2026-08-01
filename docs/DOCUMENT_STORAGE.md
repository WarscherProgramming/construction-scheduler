# Document Storage Foundation

M16.1 establishes the backend storage and metadata layer for document
features. M16.2 adds the project-scoped explorer on that foundation. M16.3
adds construction drawing sets, sheets, revisions, issues, and a project
drawing register while retaining one `Document` per stored revision. M16.4
adds authenticated browser rendering for those PDF revisions. M16.5 adds
explicit project-scoped relationships between Documents, drawings, and
construction records without creating another file or attachment system.
OCR, AI indexing, rename, move, annotations, and comparison remain outside
the shipped scope.

## Existing Attachment System

FieldFlow already stores supporting files through one generic attachment
model and resource-neutral API. `AttachmentPanel` and `useAttachments` lazily
load one persisted parent at a time, while the backend validates project
ownership, parent identity, file content, and metadata. The attachment service
streams objects through local or private S3-compatible storage and records
durable cleanup work when metadata and object storage cannot commit together.

M16.1 promotes that mature storage adapter into a generic `StorageProvider`
contract. Existing attachment imports remain compatibility aliases, so the six
shipped attachment workflows retain their API and behavior. File allowlists,
signature checks, bounded streaming, provider configuration, error
classification, and durable rollback cleanup are reused by documents instead
of duplicated.

## Provider Contract

`StorageProvider` defines:

- `upload` and `download` for bounded streaming
- `delete` and `exists`
- `metadata`
- `generate_download_url`
- `copy` and `move`
- `health_check`

`LocalStorageProvider` is the development implementation.
`S3CompatibleProvider` remains configuration-driven and supports AWS S3 or a
compatible private object store. Local development does not construct an S3
client or require cloud credentials. The in-memory provider is test-only.

Provider-specific failures are translated into stable categories such as
missing object, authentication, connection, timeout, throttling, and
configuration. API responses expose a safe availability error rather than
provider details.

## Storage Keys

Document objects use:

```text
documents/{first-two-hex}/{next-two-hex}/{32-character-random-hex}
```

The generated key contains no project name, user name, email address, display
name, or original filename. Two shard levels avoid very large flat local
directories while preserving provider-neutral keys. Existing flat attachment
UUID keys remain valid through the same provider contract.

## Database Models

`Document` stores project ownership, optional folder membership, safe file
metadata, SHA-256, provider location metadata, uploader, timestamps, and soft
deletion. `parent_document_id`, `version`, and `is_current_version` provide the
schema foundation for later version history without exposing a versioning API
in M16.1.

`Folder` stores project ownership, an optional self-referencing parent,
display name, materialized numeric path, creator, timestamps, and soft
deletion. Paths contain folder IDs rather than user-entered names. Active root
and child names have separate partial unique indexes so sibling uniqueness is
enforced even when `parent_folder_id` is null.

Folder creation validates the entire ancestry chain. Missing, deleted, or
cross-project parents are rejected, and repeated IDs detect corrupted cycles.
Project and parent foreign keys prevent orphaned rows; project deletion
cascades folders and documents, folder deletion is reserved for a later API,
and a deleted folder would leave its documents unfiled through `SET NULL`.

## Service Flows

### Upload

1. Authenticate the user and resolve the owned project.
2. Resolve the optional active folder within that project.
3. Normalize Unicode with NFKC and validate filename and metadata bounds.
4. Enforce the existing size, extension, MIME, signature, and empty-file
   rules.
5. Generate an opaque key and stream once to the selected provider while
   calculating SHA-256.
6. Commit safe metadata only after storage succeeds.
7. If metadata persistence fails, delete the object. If that cleanup also
   fails, persist a durable cleanup job without leaking the key to the client.

### Download

The service loads the document through a project-owner join, resolves the
provider recorded with that document, and returns a bounded stream. Responses
use a sanitized and UTF-8-compatible `Content-Disposition`, declared content
length and type, `nosniff`, and a sandbox Content Security Policy. Storage
keys, buckets, filesystem paths, provider credentials, and internal URLs are
never serialized.

### Delete

Deletion is idempotent and soft-deletes metadata by setting `deleted_at`,
clearing `is_current_version`, and marking status `Deleted`. M16.1 retains the
private object so a later retention/restore policy can be implemented without
pretending recovery is possible after immediate physical deletion. Deleted
documents are excluded from list, metadata, and download routes. Permanent
purge and retention scheduling are deferred to a later document lifecycle
phase.

## API

All routes require M15 authentication and project ownership:

- `POST /documents/upload`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/download`
- `DELETE /documents/{document_id}`
- `GET /projects/{project_id}/documents`
- `GET /projects/{project_id}/documents/explorer`
- `GET /projects/{project_id}/documents/recent`
- `GET /projects/{project_id}/folders`
- `GET /projects/{project_id}/folders/tree`
- `POST /projects/{project_id}/folders`

Collection endpoints support the shared bounded `limit` and `offset`
contract. Document listing optionally scopes to one active project folder.
The frontend API layer includes matching explorer, recent, tree, upload,
metadata, download, delete, and folder helpers.

## Project Document Explorer

The protected `#/projects/{project_id}/documents` route is lazy loaded and
uses `ProjectLayout`. A dedicated `useDocumentExplorer` hook owns explorer,
tree, recent-document, upload, download, folder-creation, and deletion state.
Identity checks, request cancellation, delayed Strict Mode cleanup, and
project-keyed mounting prevent an older project or folder response from
replacing the current view.

The explorer response contains the current folder, safe breadcrumbs,
immediate child folders with grouped child/document counts, safe document
metadata, and pagination metadata. The flat folder-tree response is capped at
500 active folders and validates every ancestry chain to a maximum depth of
32. The frontend builds the visual hierarchy from parent IDs; there is no
unbounded recursive API payload.

Document search is metadata-only and limited to 200 characters. It searches
display name, original filename, extension, document type, and MIME type
case-insensitively. SQL wildcard characters are escaped and treated
literally. Explicit allowlists control sort fields and direction. Exact
document-type, MIME-type, and extension filters are supported. Document
results default to 50 per page and are capped at 100, with a stable document
ID secondary order.

Recent documents include only active current versions in active folders and
are deterministically newest first, with a maximum limit of 25. Explorer,
tree, and recent responses use `Cache-Control: no-store` and exclude
checksums, storage metadata, deleted records, cleanup state, and internal
paths.

Uploads continue through the M16.1 multipart endpoint. The explorer accepts
picker, multiple-file, and drag-and-drop input, sends files sequentially,
reports each result, preserves successful files when another fails, and can
retry only failures. Successful mutations refresh the current listing, tree
counts, and recent documents without changing location.

Folder creation targets the project root or current folder and preserves the
existing sibling-uniqueness and ancestry validation. Document deletion uses a
name-specific confirmation and the existing idempotent soft-delete endpoint.
The UI deliberately says that removal is not permanent. Downloads use the
authenticated streaming endpoint and browser Blob downloads; provider URLs
and paths never reach the UI.

The responsive desktop layout uses a folder sidebar, action/search controls,
breadcrumbs, one combined folder/document table, and recent documents. At
smaller widths the tree becomes an explicit folder browser and rows become
stacked records. Controls retain visible labels, keyboard alternatives,
focus-visible styling, modal focus traps/restoration, Escape handling, live
upload results, and non-color-only status text.

M16.2 provides metadata details and authenticated download only. It does not
render active HTML, SVG, Office documents, or a drawing/PDF annotation
viewer.

## Drawing Integration

M16.3 keeps explorer location independent of drawing classification. Every
drawing revision is one root-level `Document` with type `Drawing`, linked by
`DrawingRevision`; no second file or provider path is created. The same
authenticated explorer and revision download flows therefore read the same
stored object.

Drawing revisions initially accept PDF only and reuse the document service's
bounded streaming, MIME, extension, and signature checks. Revision creation
defers the document commit so the document metadata, drawing revision,
previous-revision superseding, and sheet current pointer commit together. A
database failure rolls back metadata and removes the newly stored object.

Ordinary explorer deletion returns a conflict when a document is referenced
by drawing history. Drawing sets and sheets archive instead of erasing
history; drawing revisions are not directly deletable; issued drawing issues
are voided rather than removed. See
[`DRAWING_MANAGEMENT.md`](DRAWING_MANAGEMENT.md) for the complete drawing
contract.

M16.4 reuses the drawing revision download route and the same stored
`Document`; it does not add a viewer object, migration, provider URL, signed
URL, or duplicate storage service. The authenticated response is private and
`no-store`. The frontend holds one Blob for the viewer session, passes bytes
to a same-origin PDF.js worker, and reuses that Blob for explicit download.
HTTP range delivery is deferred, so local and S3-compatible providers keep
the same full-stream behavior.

## Relationship Integration

M16.5 adds one generic `EntityRelationship` table and an explicit resolver
registry for Documents, drawing sets, sheets, revisions and issues, RFIs,
Submittals, Punch Items, Change Orders, and Daily Logs. Relationships point
to existing metadata records; they do not copy files, change Attachment
parent identity, alter Document folder placement, or expose provider data.

The reusable frontend panel loads only for one explicitly selected persisted
record. Document details, selected drawing sheets, exact viewer revisions,
and the five construction-record pages share this workflow. There is no
relationship field in explorer list responses, no request per document row,
and no dashboard relationship loading.

Relationship history is retained when a Document is soft-deleted or a
drawing record is archived. The resolver then supplies a factual archived or
unavailable summary and blocks new links to unavailable records. Formal
drawing issue membership, revision supersession, Document version lineage,
Attachment ownership, and Folder hierarchy remain authoritative specialized
models. See
[`DOCUMENT_RELATIONSHIPS.md`](DOCUMENT_RELATIONSHIPS.md) for the matrix,
direction rules, API, lifecycle, and UI contract.

## Security and Validation

Ownership is inherited from the project. Direct document routes join through
the owning project and return the same not-found response for missing,
deleted, and foreign documents. Project collection routes reuse
`get_owned_project`. Nested folder references must belong to the same project.

Document filenames reject path separators, traversal names, null bytes,
control characters, Windows reserved stems, missing or overlong extensions,
empty names, trailing spaces or dots, and names over 255 characters. Display
names, document types, and folder names are normalized and bounded. Folder
names additionally reject traversal markers and path separators. Existing
backend file rules remain authoritative; browser validation is advisory.

## Migration and Tests

Migration `a6d3e9f1b742` creates only `folders` and `documents`, with project,
user, folder, and version-lineage foreign keys; checks for nonnegative sizes
and positive versions; unique opaque keys and folder paths; sibling-name
constraints; and project listing indexes. It supports a fresh upgrade,
upgrade from the prior head, downgrade, and re-upgrade while preserving
existing records and one Alembic head.

Migration `d9a2f5c8e173` later adds only the generic relationship table. It
uses project and creator foreign keys, controlled type and positive-ID
checks, lookup indexes, and partial active-pair uniqueness while leaving
Document, Folder, Attachment, and drawing storage rows unchanged.

Coverage includes provider contracts, unsafe keys, upload/download/list
behavior, safe responses, ownership, folder hierarchy and cycles, validation,
checksums, metadata rollback, durable cleanup fallback, soft-delete
idempotency, migration reversibility, explorer responses, grouped counts,
breadcrumbs, escaped search, allowlisted sorting, filters, pagination, recent
documents, stale-request protection, upload retry, dialogs, routing,
accessibility, and frontend API requests. The complete M16.5 verification
passes 412 frontend tests across 58 files and 264 backend tests, with 317
backend subtests reported separately; relationship coverage is detailed in
[`DOCUMENT_RELATIONSHIPS.md`](DOCUMENT_RELATIONSHIPS.md).

## Deferred Work

Rename, move, folder deletion, restore, permanent purge, general document
version history, duplicate detection, direct-to-cloud upload, signed-URL
delivery, explorer thumbnails, bulk operations, PDF annotation/comparison,
OCR, AI indexing, automatic relationship suggestions, relationship graph
visualization, permanent relationship purge cleanup, and antivirus
implementation remain deferred.
