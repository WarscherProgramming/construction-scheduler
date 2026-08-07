# AI Preconstruction Scope Assertions

## Purpose

M18.3 adds the structured scope-intelligence layer required before any
omission or cross-document comparison work. It converts prepared M18.2 content
into **evidence-backed, human-reviewed scope assertions** against a controlled
construction taxonomy.

It does not detect omissions, compare drawings against proposals, compare
proposals against contracts, perform procurement comparison, create RFIs,
Change Orders, or `EntityRelationship` rows, compute embeddings, perform
semantic search, or call a live AI provider.

The authoritative flow is:

```text
prepared ReviewSource (M18.2 snapshot)
  -> content-dependent AnalysisRun (scope_assertion_extraction)
  -> provider-neutral structured extraction
  -> immutable ScopeAssertionSet
  -> immutable proposed ScopeAssertions
  -> immutable AssertionEvidence
  -> human AssertionReview
  -> accepted advisory assertions
```

Nothing in this chain is authoritative. `Document`, `DrawingRevision`,
`DocumentExtraction`, `DocumentPageText`, M18.2 snapshots/pages/segments,
review-set manifests, `EntityRelationship`, scheduling, and every workflow
record remain unchanged and AI-independent.

## Terminology

An **assertion** is an advisory statement that a source provides evidence for
a construction scope concept. It is not a finding, an omission, a requirement
of record, a contract obligation, or approved scope. Only a human decision
makes an assertion **accepted**, and even then it remains advisory.

## Scope taxonomy

The taxonomy is a **versioned built-in constant** in
`backend/app/preconstruction/taxonomy.py`, not a database table. This was a
deliberate choice: it is deterministic, needs no admin UI, no migration for
wording changes, no database state to test against, and the same module is the
allowlist the provider is validated against.

`TAXONOMY_VERSION` is `construction-scope-1`. It defines 96 concepts (95
active, 1 deprecated) across 38 categories and 12 scope kinds, with 438
normalized aliases. Each concept carries a stable dotted `category.name` code,
human label, category, scope kind, bounded description, optional parent code,
optional canonical default unit, status, and deprecation date.

Import-time assertions enforce unique codes, unique aliases across concepts,
allowlisted categories/kinds/statuses, resolvable parent codes, canonical
default units, and consistent deprecation state. A collision fails startup.

Taxonomy v1 deliberately ships one deprecated concept (`hvac.hvac_general`) so
that deprecation handling is exercised and historically pinned codes are
provably still resolvable. Deprecated codes resolve by code but are hidden from
search by default and are refused for **new** provider or manual assertions.

The taxonomy is a bounded, opinionated set suitable for common scope
identification and later expansion. It is **not** CSI MasterFormat and does not
claim to be; no approved MasterFormat dataset exists in this repository.

## Normalization

Concept resolution is exact. Aliases are compared after NFKC normalization,
case folding, and whitespace collapse. There is no fuzzy matching, no edit
distance, and no embedding. An unknown or ambiguous term resolves to `None`
and is never silently mapped onto a nearby concept.

Units normalize through a controlled map onto 19 canonical units. An
unrecognized unit is dropped with a warning rather than guessed, and a unit is
never retained without a quantity.

Assertion text is NFKC-normalized, stripped of unsafe control and format
characters, and whitespace-collapsed. Technical identifiers keep their
punctuation and case: `Section 26 51 00.13` and `Model A-24/B` survive intact.
Blank values become `NULL`. Quantities, responsibilities, and locations are
never inferred when absent.

## Persistence

`PreconstructionScopeAssertionSet` is the immutable container for one
successful extraction. It is unique per analysis run and records the pinned
manifest hash, taxonomy and schema versions, provider profile, counts, safe
warnings, and a deterministic content hash. Only `completed` and
`completed_with_warnings` are ever persisted; a structurally invalid result
rolls the whole transaction back and remains in run/attempt history.

`PreconstructionScopeAssertion` holds one advisory statement. Provider-authored
content is immutable after creation. `status` is the server-controlled current
review state, updated only inside the same transaction that appends a review
row. A database constraint enforces origin consistency: a `provider` assertion
must belong to an assertion set and carry a provider key; a `manual` assertion
must carry neither and must have no confidence.

`PreconstructionAssertionEvidence` is an immutable citation into one M18.2
content segment, carrying the snapshot, page, segment, one-based page number,
zero-based segment index, segment text hash, and a bounded server-derived
excerpt. Evidence is unique per assertion, segment, and role.

`PreconstructionAssertionReview` is an append-only human decision log. Rows are
never updated or deleted; each references the review it superseded.

## Deterministic content hash

The assertion-set content hash is SHA-256 over stable JSON of the normalized
assertions and their citation coordinates, sorted deterministically. It is
scoped to one review set's pinned content: it includes the review source and
snapshot a citation belongs to, but never identifiers generated while
persisting the result. Re-running the same manifest over the same snapshots
reproduces the hash exactly; a different set of sources hashes differently.

## Deduplication

Deduplication is bounded to one assertion set and is fully deterministic.
Identity is `(source, concept, assertion type, normalized subject, normalized
requirement, specification section, drawing sheet, inclusion state)` —
deliberately excluding evidence, so two otherwise identical assertions merge
their citations rather than persisting twice. Duplicates are reported as a
warning. There is no fuzzy or model-based deduplication, no cross-run
deduplication, and accepted historical assertions are never rewritten.
Cross-document equivalence belongs to a later milestone.

## Provider contract

The request supplies the analysis type, manifest hash, taxonomy version, scope
schema version, the allowed concept codes, assertion types and inclusion
states, source descriptors, bounded prepared segments with citation
coordinates, content totals, truncation metadata, and a fixed system
instruction. Taxonomy and enumerations come from trusted code; a provider
selects from them and can never introduce its own.

The result schema forbids unknown fields and bounds every string and list.
Each assertion requires at least one evidence reference. There is deliberately
no field for review state, project identity, database identity, assertion-set
membership, excerpt text, or free-form model reasoning. Chain-of-thought is
never requested.

**Rejection policy:** any structural or evidence-identity failure rejects the
**entire** result. `completed_with_warnings` is reserved for non-structural
issues such as deterministically merged duplicates or a dropped unrecognized
unit.

Server-side validation independently re-checks every provider claim: the source
must belong to the manifest, the concept must be active in the pinned taxonomy,
each evidence coordinate must match a segment that was actually supplied in the
request, and the segment text hash must match. Excerpts are always derived
server-side from stored segment text and are never accepted from the provider.

## Deterministic fake provider

`DeterministicFakePreconstructionAIProvider` adds eight scope modes —
`scope_success`, `scope_warning`, `scope_duplicate`, `scope_unknown_concept`,
`scope_invalid_evidence`, `scope_missing_evidence`, `scope_oversized`, and
`scope_malformed` — alongside the existing `retryable_failure` and
`permanent_failure`. Output is derived deterministically from the manifest hash
and the request's real segments, uses synthetic construction fixtures
containing no real project data, performs no network call, and remains
forbidden in production.

## Orchestration

Scope extraction reuses the existing analysis worker; no second worker was
added. The claimed attempt validates the run and manifest, retrieves only
manifest-pinned segments, builds a bounded request, executes the provider,
strictly validates the result, resolves taxonomy codes, validates every
evidence reference, normalizes, deduplicates, and then persists the assertion
set, assertions, and evidence **in the same transaction that completes the
attempt and the run**. Bulk inserts are used throughout; there is no
per-assertion commit. Failure rolls back every write and records a safe failure
code. Cancellation and lease ownership are revalidated before commit.

Run and attempt history store only a compact safe summary — counts, versions,
content hash, and warnings — never the assertion payload, evidence text, or a
raw provider response.

## API

```text
GET  /projects/{id}/preconstruction/scope-taxonomy
GET  /projects/{id}/preconstruction/review-sets/{review_set_id}/assertion-sets
GET  /projects/{id}/preconstruction/assertion-sets/{assertion_set_id}
GET  /projects/{id}/preconstruction/review-sets/{review_set_id}/assertions
GET  /projects/{id}/preconstruction/assertions/{assertion_id}
POST /projects/{id}/preconstruction/review-sets/{review_set_id}/assertions/manual
POST /projects/{id}/preconstruction/assertions/{assertion_id}/reviews
POST /projects/{id}/preconstruction/assertions/{assertion_id}/supersede
```

Every route resolves ownership through `get_owned_project` before any nested
identifier. Filters are allowlisted: review status, concept code, category,
assertion type, source, document role, discipline, trade, inclusion state,
origin, confidence range, bounded metadata search, assertion set, and
current-set-only. Unknown filter values are refused with 422 rather than
silently ignored.

Listing order is review priority (proposed, needs review, accepted, rejected,
superseded), then concept code — whose `category.name` form groups concepts by
category — then source, then assertion id. Page size defaults to 25 and is
capped by configuration.

Search covers bounded assertion metadata only. It never searches content
segments and is not semantic.

## Query budget

One assertion page costs a fixed number of queries regardless of page size:
one listing query, one count, one batched source lookup, one batched evidence
query, one batched drawing-sheet lookup, one batched latest-review query, and
one summary aggregate. Concept metadata comes from constants and costs no
query. There is no per-assertion, per-evidence, or per-review query.

## Human review

Provider assertions begin as `proposed`. Permitted transitions are
proposed → accepted/rejected/needs_review, needs_review → accepted/rejected,
and accepted/rejected → needs_review. A direct accepted → rejected move is
refused; it must pass through needs_review.

A reviewer note is required for rejection, for reversing a settled decision,
and whenever the reason code is `other`. Reviewer identity comes from the
session and is never client-supplied. History is append-only and rejected
assertions remain historically visible. Archived review sets are read-only:
they remain fully viewable but refuse new decisions.

There is no bulk acceptance, no "approve all", and no confidence threshold that
can accept an assertion. Review is deliberate, one assertion at a time.

## Manual assertions

Humans can author assertions directly for scope that deterministic extraction
misses. A manual assertion carries `origin = manual`, no confidence, no
provider key, and no assertion-set membership, and starts as `accepted`
because a person is explicitly authoring it. It is recorded with a review event
naming the author and is visually labelled "Human authored" throughout the UI.
Human work is never dressed up as model output.

Evidence must come from the selected source's current completed snapshot. The
client submits segment identifiers only; the server derives the excerpt from
stored segment text. Arbitrary page identifiers, foreign segments, and
client-supplied excerpt text are all refused.

## Frontend

The existing lazy `#/projects/{id}/preconstruction` route gains a Scope
Assertion Workspace inside the selected review set. There is no top-level "AI
findings" route and no comparison UI.

The workspace shows the assertion-set selector (latest and historical), textual
summary counts, allowlisted filters, a bounded paginated list, and an
expandable detail panel with metadata, evidence excerpts, review history, and
links into the Content Inspector or drawing viewer. Review status, origin, and
confidence are always rendered as text; colour is never the only signal.

Evidence excerpts render as plain text with preserved wrapping. No Markdown or
HTML is interpreted. The workspace issues no binary, PDF-worker, dashboard, or
provider request, and no per-row evidence request.

Refresh is manual. There is no polling, no auto-open of assertions after a run,
and no automatic acceptance.

## Security

- Ownership is enforced at every route before any assertion, set, evidence, or
  review identifier is resolved.
- Mutation schemas forbid unknown fields and reject client-supplied project
  identity, origin, status, confidence, provider keys, taxonomy versions,
  content hashes, evidence excerpts, reviewer identity, and review timestamps.
- Provider output cannot set review state, create project records, reference
  foreign sources or segments, or introduce taxonomy entries.
- Logs may contain identifiers, counts, provider profile, safe failure codes,
  latency, versions, and a manifest hash prefix. They must never contain
  requirement text, evidence excerpts, segment content, prompts, provider
  response bodies, reviewer notes, credentials, or storage material.
- Prepared source text remains typed untrusted data separated from fixed
  instructions, with no tools, browsing, storage access, database access, or
  URL retrieval in the provider contract.

Test fixtures include hostile source content — instruction override attempts,
forged system messages, fabricated taxonomy codes, forged source and segment
identifiers, HTML and script markup, SQL, shell commands, URL-fetch requests,
and auto-approval instructions — and assert that all of it remains inert data
or fails validation. **This reduces risk; it does not claim prompt injection is
solved.**

## Migration

Alembic revision `c1f7b4e28d35` follows `b9e5d3f7a201`. It creates the four
scope tables with their constraints and indexes and widens the analysis-type
allowlist to admit `scope_assertion_extraction`. It performs no assertion,
review, or run backfill and alters no existing application table. Existing
review sets receive no assertions automatically.

## Verification

Automated release evidence is 462 backend tests with 500 separately reported
backend subtests, and 609 frontend tests across 91 files: 1,071 primary tests.
Scope-specific coverage is 27 backend tests plus 80 subtests across
`test_preconstruction_scope.py` and `test_scope_assertion_migration.py`, and 17
frontend tests in `ScopeAssertionWorkspace.test.jsx` plus extended API-client
and hook coverage. ESLint and the production build pass. No dependency or
lockfile change is part of M18.3.

Measured listing behaviour at 10, 100, and 500 assertions keeps the page
bounded at the configured size, the response under 400 KB, and the request
under five seconds on local SQLite. These are local SQLite/TestClient
measurements, not production PostgreSQL, network, or browser-render claims.

The production build keeps the preconstruction route lazy at 50.05 kB raw /
11.64 kB gzip (from 26.50 kB / 6.61 kB at M18.2). Main JavaScript is 311.62 kB
raw / 92.27 kB gzip and CSS is 111.11 kB raw / 18.88 kB gzip. No other route
chunk gains weight and the PDF worker is unchanged.

## Deferred

M18.4 adds deterministic cross-document comparison and evidence-backed
findings on top of accepted assertions; see
[`AI_SCOPE_COMPARISON.md`](AI_SCOPE_COMPARISON.md). Automatic RFI or Change
Order creation, automatic relationship creation, embeddings, semantic search,
live provider adapters, production OCR, and autonomous acceptance remain out of
scope and require later separately reviewed milestones.
