# AI Preconstruction Content Preparation

## Purpose

M18.2 converts eligible Review Sources into immutable, version-pinned plain
text that later preconstruction phases can retrieve and cite safely. It does
not classify construction scope, compare contracts, create findings, or call a
live AI provider.

The authoritative flow is:

```text
Document / DrawingRevision
  -> current DocumentExtraction and DocumentPageText
  -> PreconstructionPreparationRun
  -> immutable PreconstructionContentSnapshot
  -> one-based PreconstructionContentPage records
  -> ordered PreconstructionContentSegment records
```

`DocumentExtraction` and `DocumentPageText` remain the replaceable current
search index. Preparation copies eligible current page text into a historical
snapshot and never mutates extraction, search, drawing, Document, or object
storage records.

## Persistence

`PreconstructionPreparationRun` owns the finite pending/processing/terminal
lifecycle, source checksum, lineage fingerprint, extraction metadata,
attempt count, bounded retry timing, opaque lease-token digest, safe failure,
and warning count. Failed and unavailable work remains in run history; no
partial or failed snapshot is retained.

`PreconstructionContentSnapshot` is unique for one Review Source and lineage
fingerprint. It records the exact Document, optional Drawing Revision,
checksum, extraction method/version/completion, preparation and segmentation
versions, counts, content hash, warnings, and creating preparation run.
Completed snapshots are not replaced when extraction changes.

`PreconstructionContentPage` stores one-based page identity, an optional
authoritative drawing sheet number, character count, page-text hash,
extraction method, and factual text/visual flags. Current extraction does not
provide reliable page labels, dimensions, rotation, or bounding boxes, so
those fields remain nullable rather than fabricated.

`PreconstructionContentSegment` stores one bounded partition of one page,
its zero-based order within that page, sanitized original plain text,
normalized search text, SHA-256 hash, exact page character offsets, token
estimate, extraction method, and optional extractor confidence. M18.2 uses
only `page_text`; it does not infer headings, tables, schedules, notes, or
symbols.

## Deterministic Lineage

The canonical lineage fingerprint is SHA-256 over stable JSON containing:

- Document checksum;
- Drawing Revision ID or null;
- extraction method, extractor version, and extraction completion timestamp;
- preparation version;
- segmentation-policy version; and
- null renderer version because no layout renderer participates.

Full text is not included in the fingerprint. Snapshot content hash is
derived from ordered page numbers/page hashes and page/segment coordinates and
segment hashes, not database-generated IDs. Identical inputs produce the same
fingerprint and idempotently reuse a completed snapshot.

A snapshot becomes stale when its current fingerprint changes, its Document
is deleted or checksum-mismatched, its Drawing Revision no longer matches the
Document, or the Review Source is removed. Historical snapshots and Analysis
Run manifests remain unchanged. Reprepare creates a new run and snapshot.

## Segmentation Policy

- one page per citation boundary;
- target and hard maximum: 4,000 Unicode characters per segment;
- no overlap;
- paragraph/newline/space boundary preferred in the latter half of a segment;
- fixed-size Unicode split when no safe boundary exists;
- maximum 500 pages, 5,000 segments, and 2,000,000 characters per snapshot;
- empty pages are retained as page metadata with an `empty_page` warning;
- no empty segment and no cross-page segment.

NFKC normalization removes null bytes and unsafe control/format characters
while retaining tabs and meaningful line breaks. Segment `text` is rendered
only as plain text. Normalized text is case-folded and whitespace-collapsed
for bounded inspection search.

## Citation Coordinates

Every segment can later be cited by project, Document, optional Drawing
Revision, snapshot, one-based page, optional authoritative sheet number,
zero-based segment index, segment hash, source checksum, extraction lineage,
and preparation versions. Character offsets are page-relative. Bounding boxes
remain null because current extraction does not provide trustworthy geometry.
No `DocumentPageText` ID, storage path, signed URL, or page image is required.

## Eligibility

Preparation requires an active project-owned Review Source, active backing
Document, matching pinned checksum, matching Drawing Revision/Document pair,
supported PDF MIME type, current `completed` or `completed_with_warnings`
searchable extraction, matching extraction checksum, at least one text
character, and configured page/text limits.

Unsupported, deleted, encrypted/corrupt/failed extraction, image-only, stale,
or limit-exceeding sources receive factual safe states. Production OCR remains
disabled. The deterministic OCR fixtures remain test-only; no OCR SDK,
Tesseract, cloud vision service, or new runtime dependency is included.

## Worker And Transactions

```powershell
python -m app.commands.process_preconstruction_preparation
python -m app.commands.process_preconstruction_preparation --batch-size 5 --max-jobs 10
python -m app.commands.process_preconstruction_preparation --run-id 42
python -m app.commands.process_preconstruction_preparation --retry-failed --max-jobs 5
python -m app.commands.process_preconstruction_preparation --lease-seconds 300
```

The command is finite. It recovers expired leases, atomically claims bounded
pending work, reads current page text, inserts one snapshot plus batched pages
and segments in one transaction, validates hashes/counts, and commits one
terminal result. Failure rolls back every snapshot/page/segment write before
recording a safe run outcome. It does not read object storage, call OCR or AI,
write generated files, or run as a FastAPI background task.

## API

```text
POST /projects/{project_id}/preconstruction/review-sets/{review_set_id}/sources/{source_id}/prepare
GET  /projects/{project_id}/preconstruction/preparation-runs/{run_id}
POST /projects/{project_id}/preconstruction/preparation-runs/{run_id}/cancel
POST /projects/{project_id}/preconstruction/preparation-runs/{run_id}/retry
GET  /projects/{project_id}/preconstruction/review-sets/{review_set_id}/sources/{source_id}/content
```

Inspection accepts an optional historical `snapshot_id`, one-based `page`,
bounded segment offset/limit, and 200-character plain-text search. Responses
are `Cache-Control: no-store`, return bounded segments and page summaries, and
exclude storage metadata, URLs, leases, raw exceptions, and full-document
dumps. All nested IDs resolve after `get_owned_project`.

## Analysis Boundary

Existing readiness/provider probes remain metadata-only. The new
`content_contract_validation` type requires every active source to have a
current completed snapshot. Its immutable manifest pins snapshot ID, lineage
fingerprint, content hash, counts, extraction metadata, role, and source
identity without segment text.

Business logic selects a bounded segment DTO for the provider contract. The
DTO separates a fixed system instruction from typed `untrusted_text`; it has
no ORM objects, database session, storage access, credentials, tools, or URLs.
Document-supplied prompts, HTML, shell text, SQL, and forged JSON remain inert
data. This boundary reduces risk but does not claim prompt injection is solved.

## Frontend

The existing lazy `#/projects/{project_id}/preconstruction` route shows
extraction and preparation as separate textual states. Source preparation,
cancel, retry, reprepare, and refresh are manual. Source summaries are batched
with the existing source-list request; no per-row request is introduced.

Only one selected source can mount the focus-managed Content Inspector. It
loads bounded pages/segments on demand, supports page selection, search and
pagination, renders text with preserved wrapping, links to the owned source,
and clears/aborts on Review Set or project changes. It makes no binary,
PDF-worker, dashboard, OCR, or provider request.

## Configuration

Implemented controls are documented in `backend/.env.example`. Defaults are
500 pages, 5,000 segments, 2,000,000 characters, 4,000 characters per segment,
five jobs per worker batch, 300-second leases, three attempts, 30/3,600-second
retry bounds, 25 inspection segments, and 100,000 response text characters.

## Verification

Automated release evidence is 435 backend tests with 420 separately reported
backend subtests, and 590 frontend tests across 90 files: 1,025 primary tests.
Preconstruction-specific coverage is 31 tests plus 13 subtests across
`test_preconstruction_content.py`, `test_preconstruction_content_migration.py`,
`test_preconstruction_api.py`, `test_preconstruction_worker.py`, and
`test_preconstruction_migration.py`. ESLint and the production build pass. No
dependency or lockfile change is part of M18.2.

The migration test upgrades to `a8f4c2d6e190`, seeds real rows through raw
SQLite with foreign keys enforced, upgrades to `b9e5d3f7a201`, and asserts the
four new tables, their checks, partial and composite indexes, the widened
analysis-type constraint, absence of backfill, and a clean downgrade.

The production build keeps the preconstruction route lazy at 26.50 kB raw /
6.61 kB gzip. Main JavaScript is 310.42 kB raw / 91.96 kB gzip and CSS is
107.46 kB raw / 18.37 kB gzip. The drawing viewer remains 450.08 kB raw /
133.88 kB gzip and the PDF worker is unchanged at 1,262.39 kB. The Content
Inspector adds no PDF-worker, binary, or dashboard request, so no other route
chunk gains weight from M18.2.

These are absolute current-tree measurements from local SQLite, TestClient,
and a local production build. They are not production PostgreSQL, network,
proxy, or browser-render claims, and no per-milestone bundle delta is asserted
because M18.1 recorded no baseline figures.

## Deferred

M18.3 adds controlled construction scope assertions and evidence-backed human
review on top of these snapshots; see
[`AI_SCOPE_ASSERTIONS.md`](AI_SCOPE_ASSERTIONS.md). Findings, comparisons,
embeddings, semantic search, live providers, AI-generated RFIs, automatic
relationships, Office or CAD extraction, production OCR, and visual/layout
interpretation are not part of M18.2 or M18.3.
