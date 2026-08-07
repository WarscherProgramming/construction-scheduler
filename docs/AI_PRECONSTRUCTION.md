# AI Preconstruction Foundation

M18.1 establishes FieldFlow's provider-neutral preconstruction review
boundary. M18.2 adds immutable source-content preparation beside the
replaceable project-search index. Neither phase extracts construction scope, compares contracts, detects
omissions, generate findings, or call a live AI provider. Existing Documents,
Drawing Revisions, extraction records, page text, relationships, and schedules
remain authoritative.

## Advisory Boundary

Preconstruction is a project-owned advisory workspace. A user deliberately
creates a **Preconstruction Review Set**, selects **Review Sources**, assigns a
controlled **Document Role**, reviews deterministic readiness, and requests an
**Analysis Run**. A finite worker claims an **Analysis Attempt** and invokes an
allowlisted provider through a validated DTO boundary.

Provider output is untrusted. It cannot mutate documents, relationships,
schedules, contracts, procurement records, or field workflows. Future
findings must remain evidence-backed and require human review; M18.1 creates no
finding or scope-assertion table.

## Authoritative Systems

- `Document` owns file identity, private storage location, checksum, version,
  and soft-deletion state.
- `DrawingRevision` owns sheet revision lineage and its backing Document.
- `DocumentExtraction` owns extraction status, checksum, and extractor
  version. `DocumentPageText` remains current searchable page content.
- `StorageProvider` owns binary access. Preconstruction does not access it.
- `EntityRelationship` remains the human-created relationship graph.
- Scheduling and dashboard calculations remain deterministic and AI-free.

## Domain Model

### Review Set

`PreconstructionReviewSet` is project-owned and records a trimmed name,
bounded description, controlled purpose, server-owned creator and timestamps,
and `draft`, `ready`, or `archived` status. Names are case-insensitively unique
per project across active and archived history. There is no hard-delete API.

A draft permits metadata and source changes. Capturing the first run locks its
sources and moves the set to ready. Ready sets preserve their run inputs and
reject metadata/source mutation. Archived sets remain viewable and read-only;
active runs must be cancelled before archival.

Purposes are bid scope review, subcontract scope review, procurement review,
submittal coverage review, revision impact review, and general scope review.

### Review Source

`PreconstructionReviewSource` references either an owned active Document or an
owned Drawing Revision and its exact backing Document. It snapshots checksum,
current extraction identity/version/status, display name, sheet/revision
metadata, role, and optional discipline/trade. It stores no object key, URL,
credential, binary, page text, or `DocumentPageText` row ID.

Sources are soft-removed only while unused in a draft. The first run stamps
`locked_at`; used rows are immutable. A partial unique index prevents two
active entries for the same logical source in one review set.

### Document Roles

| Category | Roles |
|---|---|
| Requirement | drawing, specification, addendum, schedule, equipment_schedule |
| Coverage | proposal, subcontract, purchase_order, procurement_package, submittal |
| Context | rfi, change_order, owner_directive, other_reference |

The API returns machine value, safe label, and category. Roles are selected by
the user and are never inferred in M18.1.

### Analysis Run and Attempt

`PreconstructionAnalysisRun` pins provider profile, analysis type, template
and schema versions, source count, bounded canonical manifest JSON, SHA-256
manifest hash, requester, lifecycle timestamps, attempts, safe failure fields,
and an approved result summary. Supported foundation analysis types are
`readiness_probe` and `provider_contract_validation`.

`PreconstructionAnalysisAttempt` is append-only except for lifecycle fields.
It records attempt number, safe provider/model identifiers, availability,
lease, bounded failure and result metadata, and manifest/schema identity. It
stores no prompt, document text, credentials, raw provider object, or hidden
reasoning. Unique and partial indexes enforce attempt numbering and one active
attempt per run.

## Readiness

Readiness is deterministic and makes no provider call. It verifies:

- at least one active source;
- every source still resolves inside the owned project;
- every Document is active and still matches its pinned checksum;
- requirement and coverage sources have a current searchable completed or
  warning extraction against that checksum;
- context extraction gaps are warnings rather than requirement blockers;
- purpose-specific role composition is present;
- the review set is not archived; and
- the configured provider is enabled and available.

Revision-impact review requires two Drawing Revisions. Other purposes require
a requirement source and compatible coverage role. Responses cap factual
blockers and warnings at 50 and report role/searchability counts plus safe
provider capability state. They contain no confidence score or remediation.

## Immutable Manifest

Active sources are sorted by source ID. The service resolves current checksum
and extraction lineage, builds an object containing only IDs, roles, checksums,
extraction identity/status, safe display snapshots, analysis type, provider
profile, and template/schema versions, then serializes with sorted keys and
compact ASCII JSON. SHA-256 of those exact bytes is the manifest hash.

The snapshot is size-bounded and immutable after run creation. Repeated inputs
produce the same hash, and a partial unique index makes identical active runs
idempotent. Later extraction or document changes do not rewrite prior runs.

## API

All routes authenticate and resolve `get_owned_project` before nested records.
Lists are bounded and deterministically ordered.

```text
POST/GET /projects/{project_id}/preconstruction/review-sets
GET/PUT  /projects/{project_id}/preconstruction/review-sets/{review_set_id}
POST     /projects/{project_id}/preconstruction/review-sets/{review_set_id}/archive

POST/GET /projects/{project_id}/preconstruction/review-sets/{review_set_id}/sources
PUT/DELETE /projects/{project_id}/preconstruction/review-sets/{review_set_id}/sources/{source_id}
GET /projects/{project_id}/preconstruction/source-candidates
GET /projects/{project_id}/preconstruction/review-sets/{review_set_id}/readiness

POST/GET /projects/{project_id}/preconstruction/review-sets/{review_set_id}/runs
GET  /projects/{project_id}/preconstruction/runs/{run_id}
POST /projects/{project_id}/preconstruction/runs/{run_id}/cancel
POST /projects/{project_id}/preconstruction/runs/{run_id}/retry
```

Source candidates allow only `document` and `drawing_revision`, use escaped
bounded metadata search, and expose safe route targets and extraction state.
Run status excludes manifest JSON, raw provider output, prompts, and content.

## Provider Boundary

`PreconstructionAIProvider` receives a focused immutable DTO containing the
manifest hash, analysis/profile/template/schema identifiers, and bounded
source descriptors. It has no database, ownership, storage, or routing access.
Results pass strict Pydantic validation and configured byte limits before
persistence.

- `DisabledPreconstructionAIProvider` is the production-safe default and
  performs no network access.
- `DeterministicFakePreconstructionAIProvider` supports success, warning,
  retryable failure, permanent failure, malformed result, and timeout modes.
  It is permitted only with an explicit non-production safeguard.

The explicit factory accepts only `disabled` and `fake_test`; there are no
dynamic imports, arbitrary class paths, real provider secrets, or SDKs.

## Frontend

`#/projects/{project_id}/preconstruction` is a lazy project route. Its local
`usePreconstruction` hook owns review-set selection, details, sources,
readiness, runs, and candidate search. AbortControllers, project identity
checks, selected-set identity checks, and keyed routing reject stale results.
No request occurs outside this route.

The workspace provides active/archived lists, create/edit/archive dialogs,
bounded source search, role controls, source links, textual readiness,
manual refresh, and request/cancel/retry run controls. It uses manual status
refresh rather than polling and does not load binaries, the PDF worker,
dashboard resources, findings, prompts, or provider/model controls.

## Security and Limits

- project ownership is inherited from each authoritative source and checked at
  every route boundary;
- strict mutation schemas reject IDs, statuses, audit fields, result fields,
  and unknown properties;
- provider results are untrusted, strictly parsed, and byte-bounded;
- logs and responses must omit prompts, document text, credentials, raw
  exceptions, storage URLs, and hidden reasoning;
- source count defaults to 250, candidate results to 20 (maximum 50), and
  review/run lists use existing bounded pagination;
- M18.2 treats extracted source content as typed untrusted data, separates it
  from fixed instructions, and keeps tools, URLs, storage, and database access
  outside the provider contract. This reduces risk without claiming prompt
  injection is solved.

M18.3 adds the controlled construction scope taxonomy and evidence-backed
human-reviewed scope assertions; M18.4 adds deterministic cross-document
comparison and evidence-backed findings
(see [`AI_SCOPE_COMPARISON.md`](AI_SCOPE_COMPARISON.md)). It preserves immutable sources, provider
independence, mandatory human review, and every authoritative existing system.
See [`AI_SCOPE_ASSERTIONS.md`](AI_SCOPE_ASSERTIONS.md). Omission findings and
cross-document comparison remain deferred to later separately reviewed
milestones.

## Migration

Alembic revision `a8f4c2d6e190` follows `f7c5d0b3e826` and creates the four
preconstruction tables, project/listing and worker indexes, controlled-value
and nonnegative checks, project/name and run/attempt uniqueness, source and
attempt partial uniqueness, and explicit foreign-key cleanup behavior. It
does not alter or backfill existing application tables. Review sets, sources,
runs, and attempts cascade with project/domain deletion; authoritative source
Documents and Drawing Revisions remain restricted references, while a removed
extraction clears only the source's optional extraction pointer.

## M18.2 Immutable Content Preparation

M18.2 adds preparation runs and immutable snapshot, page, and segment records
after `DocumentExtraction`. It does not replace `DocumentPageText`, project
search, object storage, or Drawing Revision lineage. Content-dependent
analysis manifests pin snapshot lineage and hashes without embedding text;
provider DTOs receive only a bounded typed segment selection.

Preparation, status refresh, content inspection, retry, cancellation, and
reprepare remain deliberate actions in the existing lazy route. Source lists
receive batched preparation summaries and never request text per row. The
inspector returns plain text under `Cache-Control: no-store` and makes no
binary or PDF-worker request.

Alembic revision `b9e5d3f7a201` follows `a8f4c2d6e190` and adds only the four
content-preparation tables plus the controlled content-contract analysis type.
It performs no source backfill or automatic preparation. See
[`AI_CONTENT_PREPARATION.md`](AI_CONTENT_PREPARATION.md) for the data model,
lineage, sizing, citation, API, security, and M18.3 boundary.
