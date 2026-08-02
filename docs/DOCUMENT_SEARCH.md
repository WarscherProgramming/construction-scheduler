# Document Text Extraction and Search

M16.6 adds project-scoped native PDF text extraction, an OCR provider
boundary, page-level indexing, and full-text search for project documents and
drawing revisions. Search is lexical PostgreSQL full-text search, not AI,
semantic search, embeddings, classification, or relationship inference.

## Capability Level

Native text extraction is shipped and covered for PDFs with embedded text;
live production extraction remains subject to the M16 deployment gate.
PNG, JPEG, WebP, and image-only PDF pages enter the OCR path, but the current
production OCR provider is deliberately `disabled`. Those files report OCR
as unavailable; FieldFlow does not fabricate successful text extraction.

The runtime audit found no installed Tesseract executable and Render's native
Python runtime does not guarantee that operating-system package. M16.6
therefore uses a focused `OCRProvider` interface, a disabled provider in the
application, and deterministic providers in tests. A paid cloud OCR service
was not selected or authorized. English (`eng`) is the configured initial
language, with no automatic language detection or multilingual claim.

`pypdfium2==5.12.1` is the one new backend runtime dependency. It provides
page-level PDF text extraction and bounded in-memory page rendering without
an external PDF executable, supports the repository's Python 3.14 runtime,
and is distributed under BSD-3-Clause/Apache-2.0 terms plus its documented
PDFium dependency licenses. Pillow remains the existing raster decoder.

## Architecture

```text
Document upload or drawing revision transaction
  -> DocumentExtraction + durable pending job
  -> finite external processor claims a leased job
  -> authorized storage provider opens immutable bytes
  -> checksum verification
  -> PDF embedded text extraction by page
  -> bounded render/decode for OCR-eligible pages
  -> OCRProvider (disabled in production for M16.6)
  -> transactional replacement of page text after success
  -> PostgreSQL simple tsvector + GIN index
  -> owned-project search API
  -> lazy React search route
```

Uploads do not perform extraction in the request. Queue metadata is flushed
inside the same database transaction as the Document, including drawing
sheet and revision uploads that use `create_document(..., commit=False)`.
A failed outer drawing transaction rolls back its Document, extraction, and
job together. No FastAPI background task, daemon, Redis, Celery, or in-process
scheduler is used.

One `DocumentExtraction` row represents the current extraction lifecycle for
one Document/checksum. `DocumentPageText` stores plain normalized text by
1-based page number. `DocumentExtractionJob` stores durable attempts,
availability, lease expiry, and a random lease token. A partial unique index
prevents duplicate pending/processing jobs for one document/checksum.

The extraction statuses are:

- `pending`: durable work is queued.
- `processing`: a worker owns a current lease.
- `completed`: processing finished without warnings.
- `completed_with_warnings`: searchable text exists with a bounded warning.
- `failed`: processing ended safely after a permanent failure or retry limit.
- `unavailable`: no configured provider could produce content text.
- `cancelled`: the Document was deleted or the claim became stale.

The method values are `embedded_text`, `ocr`, `mixed`, `metadata_only`, and
`unavailable`. Image-only content is never labeled searchable when no OCR
provider ran.

## Extraction Rules

Supported content extraction formats are PDF, PNG, JPEG, and WebP. Office,
CAD, HEIC/HEIF, media, and other allowlisted upload types remain searchable
by metadata only. PDF page boundaries are preserved. Page numbers start at
1 and are unique within an extraction.

Text is normalized with Unicode NFKC, nulls and unsafe control characters are
removed, whitespace remains suitable for snippets, and only plain text is
stored. The default limits are:

- 500 PDF pages per document
- 50 OCR-eligible pages per document
- 100,000 characters per page
- 2,000,000 characters per document
- 20 meaningful alphanumeric characters before OCR fallback is considered
- 200 DPI rendering
- 40,000,000 pixels and 12,000 pixels on either image dimension
- 120 seconds cooperative document processing and 30 seconds per OCR call
- 25 MiB inherited upload/object-read limit

Limits are validated and bounded at startup. Text is truncated
deterministically and produces `text_limit_exceeded`. Raster dimensions are
checked before decode, Pillow decompression-bomb warnings are errors, EXIF
orientation is normalized, and page images are released after each call. PDF
render dimensions are checked before rendering. Blank pages are successful
empty pages and do not falsely require OCR.

Parser and OCR work currently runs inside the finite command process. The
deadline is cooperatively checked and the OCR provider receives a page
timeout contract; M16.6 does not claim an operating-system sandbox or hard
process kill for PDFium.

## Jobs and Reprocessing

Run a bounded processor invocation from an external scheduler:

```bash
python -m app.commands.process_document_extractions
python -m app.commands.process_document_extractions --batch-size 10 --max-jobs 25
python -m app.commands.process_document_extractions --document-id 42
python -m app.commands.process_document_extractions --retry-failed --max-jobs 10
python -m app.commands.process_document_extractions --prune-completed
```

The command exits after its bounded work. Render invokes it as a cron job
every ten minutes. It atomically claims rows with `FOR UPDATE SKIP LOCKED` on
PostgreSQL, increments attempts, assigns a lease token, and recovers expired
leases. A worker can finalize only while its token still matches, preventing
an expired process from overwriting a newer claim. Retryable storage/parser
failures use bounded exponential backoff, three attempts by default, and safe
failure categories. Terminal job history is retained for 30 days by default.

Completed extraction is tied to the Document SHA-256 checksum and a
deterministic extractor version. Normal enqueue skips current completed work.
Explicit reprocessing creates a new durable job. Existing page rows remain
searchable while reprocessing; replacement rows become visible in one
transaction only after success. A failed reprocess retains prior searchable
rows while exposing the new failure state. Soft deletion cancels active jobs,
and active search always filters through the nondeleted Document.

## Configuration

`DOCUMENT_EXTRACTION_ENABLED` is the top-level switch. OCR requires both
`DOCUMENT_OCR_ENABLED=true` and an implemented provider; M16.6 accepts only
`DOCUMENT_OCR_PROVIDER=disabled`, so startup rejects configuration that would
misrepresent OCR availability. `DOCUMENT_OCR_LANGUAGE` defaults to `eng`.

Resource controls are grouped by purpose:

- `DOCUMENT_EXTRACTION_MAX_PAGES`, `DOCUMENT_OCR_MAX_PAGES`,
  `DOCUMENT_EXTRACTION_MAX_CHARS_PER_PAGE`, and
  `DOCUMENT_EXTRACTION_MAX_CHARS_PER_DOCUMENT` bound persisted work.
- `DOCUMENT_EXTRACTION_EMBEDDED_TEXT_THRESHOLD`, `DOCUMENT_OCR_DPI`,
  `DOCUMENT_OCR_MAX_PIXELS`, and `DOCUMENT_OCR_MAX_DIMENSION` control OCR
  eligibility and rendering.
- `DOCUMENT_EXTRACTION_TIMEOUT_SECONDS` and
  `DOCUMENT_OCR_PAGE_TIMEOUT_SECONDS` define cooperative deadlines.
- `DOCUMENT_EXTRACTION_MAX_ATTEMPTS`, retry base/maximum seconds, lease
  seconds, batch size, and retention days control durable processing.
- `DOCUMENT_EXTRACTION_REPROCESS_RATE_LIMIT` and its window bound manual
  requests. This reuses the repository's process-local limiter; deployments
  with multiple API instances still need the deferred distributed limiter.

The command must receive the same `DATABASE_URL`, storage provider, S3
credentials, size/chunk limits, and production-mode settings as the API.
`render.yaml` supplies those settings to a finite cron invocation rather than
starting a resident worker.

## PostgreSQL Search

Production uses page-level `tsvector` values with the PostgreSQL `simple`
text-search configuration and a GIN index. `simple` deliberately preserves
construction abbreviations, sheet numbers, product codes, and model numbers
without aggressive English stemming. User text is bounded to 200 characters
and converted with `websearch_to_tsquery`; raw `tsquery` syntax and regex are
not exposed.

Ranking is deterministic:

1. exact display-name or sheet-number match
2. display-name or sheet-number prefix match
3. drawing/document metadata full-text rank
4. page-content `ts_rank_cd`
5. updated time, document ID, and page number as stable tie-breakers

Metadata matches return one result per Document. Useful content matches may
return more than one page. Snippets are generated in application code from
the matching row, capped at 320 characters, and return plain text plus
validated match ranges. The React client creates text nodes and `<mark>`
segments; it never uses `dangerouslySetInnerHTML`.

SQLite is used only by repository integration and migration tests. Its
fallback performs escaped deterministic term matching and application-side
ranking; it does not claim PostgreSQL FTS semantics or concurrency behavior.

A finite local PostgreSQL verification created 10,000 temporary page vectors,
confirmed a GIN `Bitmap Index Scan`, and executed a synthetic product-code
lookup in 0.097 ms on the verification machine. A separate rolled-back probe
through `search_project_documents` returned only the owned project's expected
page and safe snippet. These figures validate the query path and index, but
are not a production latency guarantee or a substitute for corpus-specific
load testing.

## API

Every endpoint requires authentication and `get_owned_project`:

- `GET /projects/{project_id}/documents/{document_id}/extraction`
- `POST /projects/{project_id}/documents/{document_id}/extraction/reprocess`
- `GET /projects/{project_id}/search`

Status returns lifecycle metadata, counts, warnings, safe failure category,
source-current state, and retry eligibility. It never returns page text,
storage keys, checksums, provider details, traces, or OCR debug output.
Reprocess accepts only `{}`, rejects client lifecycle fields, does no parsing
in the request, deduplicates active jobs, and is limited to five requests per
user/project per hour by default.

Search requires `q` and supports `all`, `documents`, or `drawings` scope;
document type; drawing set; allowlisted discipline; current-only drawing
revisions; extraction method; and bounded limit/offset. Results contain safe
metadata, rank, one bounded snippet, match ranges, extraction method, and a
structured route target. Current revisions are the default. Superseded
revisions are available only when requested. Archived sheets/sets and deleted
Documents are excluded.

## Frontend

`#/projects/{project_id}/search` is a protected lazy route. It owns page-level
query/filter state and does not put search text in the URL. `useDocumentSearch`
makes no request before explicit submit, aborts replaced requests, rejects
stale project/query responses, and supports retry, clear, filters, and bounded
pagination. Search does not load a PDF worker, document bytes, attachments,
relationships, or dashboard resources.

The Project Document Explorer receives batched extraction summaries in its
existing explorer/recent responses, so it creates no status request per row.
Document details can queue controlled reprocessing and open Document Search.
Replacing currently searchable text requires an accessible confirmation.

The Drawing Viewer requests one status payload for the exact revision's
existing Document ID. Metadata labels distinguish `Viewer search` (the
currently loaded PDF's embedded text in the browser) from `Project index`
(persisted backend extracted/OCR content). Opening status or project search
does not refetch the authorized PDF Blob.

The search page has one page-level heading, labeled query and filter controls,
semantic result lists, announced loading/error/result states, labeled
pagination, keyboard-reachable actions, and non-color-only extraction labels.
Plain snippets and long identifiers wrap, controls stack at narrow widths,
and content-driven heights avoid fixed-result clipping. Automated DOM and CSS
coverage exercises these contracts; manual 320/375/768/1024/wide layouts and
200% zoom remain unverified in the command-only environment.

The production build keeps the route lazy at 9.91 kB raw / 2.84 kB gzip,
with separate 1.70 kB raw / 0.80 kB gzip search utilities and 1.88 kB raw /
0.75 kB gzip extraction-state hook chunks. Relative to M16.5, main gzip grows
0.26 kB, CSS gzip 0.63 kB, and the drawing viewer gzip 0.25 kB; the existing
PDF worker remains 1,262.39 kB raw / 374.85 kB gzip.

## Security and Operations

- Ownership is enforced before status, reprocess, ranking, or result exposure.
- Stored text and snippets are untrusted plain text with no HTML, Markdown,
  formulas, automatic links, or external resource loads.
- Logs contain IDs and safe categories, never document text, query content,
  storage keys, tokens, or temporary paths.
- Reads are bounded and re-hashed before parsing; silent object replacement
  cannot produce a current extraction.
- No rendered images, derivatives, temporary OCR files, or page canvases are
  persisted.
- Search limits, page/pixel/text limits, leases, attempts, batch sizes, and
  reprocess rate limits reduce queue and CPU abuse.
- The dashboard and relationship graph issue no extraction or search requests.
- Extracted content never creates or suggests an EntityRelationship.

Operators must configure the cron service with the same PostgreSQL and private
S3 credentials as the API, apply Alembic revision `e4b7c2d9f651`, monitor
failed/pending job counts, and invoke reindexing deliberately after an
extractor upgrade. OCR remains unavailable until a production provider,
deployment isolation, credentials/cost policy if external, and provider tests
are approved.

## Troubleshooting

- A long-lived `pending` state means the finite processor is not being
  invoked, cannot reach the database/storage provider, or the job's
  `available_at` has not arrived. Check cron execution and safe category logs.
- An expired `processing` lease is reclaimed on a later processor run. Do not
  edit lease tokens manually.
- `unavailable` with `ocr_unavailable` is expected for raster or image-only
  content while the production provider is disabled.
- `checksum_mismatch` means stored bytes no longer match the immutable Document
  checksum. Investigate object replacement before reprocessing.
- `encrypted_pdf`, `page_limit_exceeded`, and `text_limit_exceeded` are
  bounded factual outcomes, not retryable infrastructure failures.
- Searchable text from a prior completed run remains active if a reprocess
  fails. The status payload reports the failure and whether retry is allowed.
- After changing extractor behavior, queue deliberate reprocessing; the
  application does not automatically reindex the full corpus.

## Verification and Limits

Automated verification covers text, image-only, mixed, blank, corrupt, and
encrypted PDFs; raster/pixel/page/text limits; disabled/fake/timeout OCR;
checksums; queueing; drawing transactions; leases; retries; status/reprocess;
project isolation; snippets; filters; current and superseded revisions;
migration lifecycle; API helpers; stale hooks; accessible page states; exact
navigation; explorer/viewer integrations; and App lazy routing.

The M16.7 complete verification passes 287 backend tests plus 317 separately
reported subtests and 433 frontend tests across 62 files. ESLint, production
build, `pip check`, Alembic current/head/check, the finite processor smoke,
and the production frontend dependency audit pass. The full frontend
development tree retains two pre-existing high advisories in build tooling;
`pip-audit` is not installed, so no Python advisory scan is claimed.

Local PostgreSQL confirms the page-vector GIN index and required partial
constraints. A transactional service smoke returned one project-scoped page
result while excluding same-term deleted and foreign-project Documents. A
100,000-row temporary `simple`-configuration probe used a Bitmap Index Scan
and matched synthetic sheet/product codes. The local database contained no
persisted page rows before that rolled-back probe, so this is correctness and
plan evidence rather than production-corpus benchmarking.

M16.6 does not include production OCR, Office/CAD extraction, HTTP range
search, semantic search, embeddings, AI summaries, classification, automatic
relationships, drawing comparison, annotations, offline indexing, signed
search URLs, or cross-project search. Manual browser, production-corpus load,
and OCR-provider verification remain operational follow-up rather than
automated claims. Recovery steps are in
[`DOCUMENT_OPERATIONS.md`](DOCUMENT_OPERATIONS.md), and the unexecuted live
matrix remains checkable in [`DOCUMENT_QA.md`](DOCUMENT_QA.md).
