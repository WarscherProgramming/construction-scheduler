# AI Preconstruction Scope Comparison

## Purpose

M18.4 compares human-accepted M18.3 scope assertions across documents and
produces evidence-backed advisory **findings**: potential coverage gaps,
conflicts, exclusions, conditional scope, and revision impacts.

It does not create RFIs, Change Orders, Submittals, Tasks, relationships,
procurement records, cost estimates, or notifications; it does not approve
contracts or purchase orders; it computes no embeddings and performs no
semantic search; and it calls no live AI provider.

The authoritative flow is:

```text
accepted advisory ScopeAssertions (M18.3)
  -> ComparisonPlan
  -> deterministic candidate matching
  -> optional provider-neutral validation
  -> immutable FindingSet
  -> immutable Findings + assertion links + evidence
  -> human FindingReview
  -> accepted advisory findings
```

## Terminology

A **finding** is an advisory statement that two or more accepted assertions
may indicate missing, conflicting, excluded, conditional, superseded, or
otherwise mismatched scope. Findings are deliberately worded as *potential*.
They are never confirmed omissions, contract obligations, approved change
orders, or legal conclusions. There is no breach, liability, or entitlement
vocabulary anywhere in the controlled value set.

## Deterministic-first design

Deterministic comparison is the primary path and **requires no AI provider**.
It runs in production with the provider disabled, because every rule is
explainable and bounded. Provider validation is a separate, optional analysis
type that can only keep, reject, or escalate candidates that trusted code
already generated.

Two analysis types were added:

- `scope_comparison` — deterministic only; never calls a provider.
- `scope_comparison_validation` — deterministic candidates plus bounded
  provider validation; unavailable while the provider is disabled.

## Comparison types

Twelve controlled comparison types are defined in
`backend/app/preconstruction/comparison.py`, each pinning its allowed left-side
and right-side document roles and its allowed finding types:
`requirement_vs_proposal`, `requirement_vs_subcontract`,
`requirement_vs_purchase_order`, `requirement_vs_procurement_package`,
`requirement_vs_submittal`, `specification_vs_drawing`,
`drawing_vs_drawing_revision`, `proposal_vs_subcontract`,
`contract_vs_proposal`, `requirement_vs_change_order`,
`equipment_schedule_vs_purchase_order`, and `general_scope_coverage`.

`requirement_vs_rfi` is deliberately omitted: RFI is a context role, not a
coverage role, so "requirement covered by RFI" is not a meaningful coverage
relationship under the current taxonomy.

Import-time validation rejects an unknown role, an unknown finding type, a
duplicate comparison type, or a finding type without a documented default
severity.

## Finding types and severity

Fourteen finding types are defined, each with a documented deterministic
default severity:

| Finding type | Default severity |
|---|---|
| missing_coverage | high |
| partial_coverage | medium |
| conflicting_scope | high |
| explicit_exclusion | medium |
| conditional_scope | medium |
| responsibility_conflict | high |
| quantity_mismatch | medium |
| location_mismatch | medium |
| revision_added_scope | high |
| revision_removed_scope | high |
| revision_changed_scope | medium |
| duplicate_scope | low |
| unsupported_assertion | low |
| informational_difference | informational |

A provider may propose a severity but it is clamped to **one step** from the
documented default, so an informational difference can never be escalated to
critical. Severity is advisory: no confidence value and no severity ever
accepts a finding.

## Deterministic matching

`backend/app/preconstruction/matching.py` is a pure module: frozen dataclasses
in, candidates out, no ORM, session, configuration, network, or provider.

Matching uses **named match classes** — `exact`, `strong`, `partial`, `weak`,
`none` — as the authoritative outcome, always accompanied by explicit reason
codes. A documented component-weighted score (0–100) is stored for traceability
and is informational only.

Component weights are declared in one place: concept match 40, assertion-type
compatibility 10, exact subject 20, subject overlap up to 15, requirement
overlap up to 10, specification section 10, responsibility 5, discipline 5,
trade 5, drawing sheet 5, quantity 5.

Two caps make the classification honest:

- **Without a taxonomy concept match, a candidate can never exceed `weak`.**
  Lexical overlap alone never produces a strong or exact match.
- **A material mismatch caps the class at `strong`.** An exact-looking score
  never hides an inclusion, responsibility, quantity, unit, or location
  contradiction.

The only lexical signal is bounded Jaccard overlap on NFKC-normalized,
case-folded tokens of length ≥ 2. There are no embeddings, no semantic
similarity, no machine learning, and no undocumented keyword heuristics.

## Coverage-gap logic

For each eligible requirement assertion, the best coverage match is resolved
deterministically by `(score, assertion id)` so ties never depend on input
order. Then:

- best match ≥ the configured covered minimum (default `strong`) → covered;
  only material contradictions are reported (explicit exclusion, responsibility
  conflict, quantity mismatch, location mismatch, conditional scope);
- best match is `partial` → `partial_coverage`;
- best match is `weak` or nothing → `missing_coverage`, with the near miss
  still linked so the reviewer can see what was considered.

A requirement whose own inclusion state is `excluded` or `not_applicable` is
never reported as a coverage gap.

## Revision-impact logic

`drawing_vs_drawing_revision` groups assertions by drawing sheet and compares
across revision lineage, producing `revision_added_scope`,
`revision_removed_scope`, and `revision_changed_scope`. When no sheet is shared
across the two sides, a `revision_lineage_incomplete` warning is recorded
rather than silently producing nothing.

This is structured assertion comparison. It performs no visual, image, or
geometric comparison of drawing content.

## Comparison plans

Comparison plans are persistent and named, chosen over per-run configuration so
review workflows are repeatable and auditable. A plan is editable while
`draft`, is **locked by its first run** so historical results stay
reproducible, and is read-only once `archived`. Names are unique per review
set. There is no hard delete.

Plan configuration is controlled: role allowlists validated against the
comparison type, assertion-set ids validated against the review set, a manual
assertion toggle, and a minimum review state. No arbitrary filter expression or
SQL fragment is ever accepted or stored. The canonical configuration is hashed.

## Eligible assertions

Comparison operates only on human-reviewed assertions. The default minimum
review state is `accepted`; `accepted_or_needs_review` may be selected
explicitly. Proposed, rejected, and superseded assertions are always excluded,
as are assertions outside the selected assertion sets, assertions pinning an
unsupported taxonomy version, and assertions whose evidence is unavailable —
each counted and surfaced rather than silently dropped.

## Comparison manifest

The comparison manifest is a separate, versioned artifact — the M18.1 analysis
manifest formula is untouched. It pins the plan, comparison type, review set,
taxonomy version, configuration hash, provider profile, and for each side the
ordered assertion ids, **the exact review id that made each assertion
eligible**, review status, origin, concept, source, document role, source
checksum, and evidence ids.

It is canonical sorted-key compact JSON hashed with SHA-256, size-bounded, and
contains no assertion text, no segment text, no provider response, no storage
metadata, and no credentials. Changing a human review decision produces a new
manifest; prior manifests are never rewritten.

## Finding content hash

The finding-set content hash is SHA-256 over canonical JSON of the comparison
manifest hash plus, for each finding, its key, type, severity, origin,
normalized title/summary/rationale, provider disposition, sorted assertion
links with side and role, and sorted evidence identities. It excludes review
decisions and timestamps, so identical inputs reproduce the hash exactly.

## Deduplication

Deduplication is deterministic and bounded to one finding set. Identity is
finding type plus sorted requirement assertion ids, sorted coverage assertion
ids, and normalized title. Duplicates are counted in a warning. There is no
fuzzy or model-based deduplication and no cross-run rewrite; historical
finding sets are always retained.

## Provider validation contract

The request supplies the comparison type, comparison manifest hash, taxonomy
version, comparison schema version, allowed finding types and severities, the
deterministic candidates with their match class, score, and reasons, and
bounded assertion metadata with server-derived evidence excerpts as typed
untrusted text alongside a fixed system instruction.

A provider may return only `retain`, `reject`, or `needs_human_review` per
candidate, plus a proposed finding type, clamped severity, concise title,
summary, rationale, confidence, and references. It cannot introduce a
candidate, an assertion, or evidence; cannot mark a finding accepted; cannot
create project records; cannot change the manifest; and cannot request tools or
URLs. Chain-of-thought is never requested.

Any structural failure — unknown candidate key, unknown or disallowed finding
type, forged assertion id, forged or unattached evidence id, repeated
candidate, version mismatch, or oversized result — rejects the **entire**
result.

## Deterministic fake provider

Eight comparison modes were added: `comparison_success`,
`comparison_warning`, `comparison_reject_candidate`,
`comparison_unknown_finding_type`, `comparison_forged_assertion`,
`comparison_forged_evidence`, `comparison_oversized`, and
`comparison_malformed`, alongside the existing failure modes. Output is derived
deterministically from the real request, uses no random data and no real
project data, performs no network call, and remains forbidden in production.

## API

```text
POST   /review-sets/{review_set_id}/comparison-plans
GET    /review-sets/{review_set_id}/comparison-plans
GET    /comparison-plans/{id}          PUT /comparison-plans/{id}
POST   /comparison-plans/{id}/archive
GET    /comparison-plans/{id}/readiness
POST   /comparison-plans/{id}/runs
GET    /comparison-plans/{id}/finding-sets    GET /finding-sets/{id}
GET    /comparison-plans/{id}/findings        GET /findings/{id}
POST   /findings/{id}/reviews
POST   /comparison-plans/{id}/findings/manual
```

Every route resolves ownership through `get_owned_project` before any nested
identifier. Filters are allowlisted (finding set, type, severity, review
status, origin, bounded search, current-set-only); unknown values return 422
rather than being ignored.

Ordering is review priority (proposed, needs review, accepted, intentional
exclusion, rejected, superseded), then severity (critical → informational),
then finding type, then finding id.

Deterministic comparison runs inline because candidate generation is bounded by
configuration and touches no external system. Provider-validated comparison is
refused inline rather than silently downgraded.

## Query budget

One finding page costs a fixed number of queries regardless of page size: the
listing, a count, one batched assertion-link query, one batched assertion
query, one batched source query, one batched evidence query, one batched
latest-review query, and the summary aggregates. There is no per-finding,
per-assertion, per-evidence, or per-review query.

## Human review

Findings begin `proposed` (or `needs_review` when a provider escalates them).
Permitted transitions are proposed → accepted/rejected/needs_review/
intentional_exclusion, needs_review → accepted/rejected/intentional_exclusion,
and accepted/rejected/intentional_exclusion → needs_review. A direct
accepted → rejected move is refused.

A reviewer note is required for rejection, for intentional exclusion, for
reversing a settled decision, and whenever the reason code is `other`.
Reviewer identity comes from the session. History is append-only. Archived
plans and review sets are read-only. There is no bulk acceptance, no "approve
all", and no confidence threshold that can accept a finding.

**Intentional exclusion** is a first-class decision: it records that an
apparent gap or conflict is deliberate, without deleting the finding or
implying a contractual position.

## Manual findings

Humans may author findings directly. A manual finding carries
`origin = manual`, no provider confidence, no provider disposition, and no
finding-set membership, and starts `accepted` because a person is explicitly
authoring and confirming it. Linked assertions must be reviewed assertions in
the plan's review set; evidence must belong to those assertions; excerpts are
derived server-side. Human work is never presented as comparison or model
output.

## Frontend

The existing lazy `#/projects/{id}/preconstruction` route gains a Scope
Comparison Workspace beneath the assertion workspace. There is no separate
top-level "AI findings" route.

The workspace shows the plan selector, readiness with separate deterministic
and provider availability, textual summary counts by category and status, the
finding-set selector, allowlisted filters, a bounded paginated list, and an
expandable detail panel with match reasons, requirement/coverage sides, and
evidence excerpts linking into the Content Inspector.

Severity, review status, origin, and match class are always rendered as text;
colour is never the only signal. Evidence renders as plain text with preserved
wrapping and no Markdown or HTML interpretation. The workspace issues no
binary, PDF-worker, dashboard, or per-row evidence request, and there is no
one-click RFI or Change Order action anywhere.

## Security

- Ownership is enforced before any plan, run, finding set, finding, link,
  evidence, or review identifier is resolved.
- Mutation schemas forbid unknown fields and reject client-supplied project
  identity, manifest and content hashes, lifecycle status, origin, provider
  profile and confidence, match scores and reasons, evidence excerpts,
  reviewer identity, and review timestamps.
- Provider output is revalidated against the pinned manifest and candidates.
- Logs may contain plan, run, and finding-set identifiers, counts, provider
  profile, safe failure codes, versions, latency, and a manifest hash prefix.
  They must never contain finding summaries or rationales, assertion text,
  evidence excerpts, reviewer notes, prompts, or provider response bodies.

Hostile-content fixtures — instruction override, forged system messages,
fabricated finding types, forged assertion and evidence ids, auto-approval
instructions, HTML/script, SQL, shell commands, URL fetch requests, and legal
conclusions — are covered by tests asserting the content stays inert or fails
validation. **This reduces risk; it does not claim prompt injection is solved.**

## Migration

Alembic revision `d5a3f9c14e28` follows `c1f7b4e28d35`. It creates the six
comparison tables with their constraints and indexes and widens the
analysis-type allowlist for the two comparison types. It performs no plan,
finding, or review backfill and alters no existing application table. No
existing review set receives a comparison plan or finding automatically.
`RESTRICT` protects cited assertions and assertion evidence; project deletion
cascades the advisory graph.

## Verification

Automated release evidence is 497 backend tests with 601 separately reported
backend subtests, and 627 frontend tests across 92 files: 1,124 primary tests.
Comparison-specific coverage is 35 backend tests plus 101 subtests across
`test_preconstruction_comparison.py` and `test_scope_comparison_migration.py`,
and 16 frontend tests in `ScopeComparisonWorkspace.test.jsx` plus extended
API-client and hook coverage. ESLint and the production build pass. No
dependency or lockfile change is part of M18.4.

Measured listing behaviour at 10, 100, and 500 findings keeps the page bounded
at the configured size, the response under 400 KB, and the request under five
seconds on local SQLite. These are local SQLite/TestClient measurements, not
production PostgreSQL, network, or browser-render claims.

The production build keeps the preconstruction route lazy at 80.60 kB raw /
16.58 kB gzip (from 50.05 kB / 11.64 kB at M18.3). Main JavaScript is
313.24 kB raw / 92.47 kB gzip and CSS is 114.77 kB raw / 19.29 kB gzip. No
other route chunk gains weight and the PDF worker is unchanged.

## Performance and measurement

M18.6 makes comparison measurable at project scale without changing a single
analytical result: memoized tokenization, one population resolution per
request, one grouped summary scan, chunked persistence, an exact pair budget
that refuses rather than truncates, and opt-in manifest reuse. See
[`AI_PRECONSTRUCTION_PERFORMANCE.md`](AI_PRECONSTRUCTION_PERFORMANCE.md).

## Follow-up actions

M18.5 lets a human raise a follow-up from an accepted finding, keep the
evidence trail, and link the record that answers it. It still creates nothing
automatically: the human creates the RFI, Change Order, or Submittal in that
record's own workflow and links it back. See
[`AI_SCOPE_FOLLOW_UP.md`](AI_SCOPE_FOLLOW_UP.md).

## Deferred

Automatic RFI or Change Order creation, automatic procurement actions,
automatic relationship creation, contract or purchase-order approval,
autonomous finding acceptance, embeddings, semantic search, live provider
adapters, production OCR, AI-generated cost estimates, subcontractor
notifications, external portals, and cross-project comparison are all out of
scope for M18.4 and require later separately reviewed milestones.
