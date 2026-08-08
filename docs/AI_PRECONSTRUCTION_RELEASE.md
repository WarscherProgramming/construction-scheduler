# AI Preconstruction — Release Architecture and Closeout

M18.7 is the release-completion review for the AI Preconstruction platform
(M18.1–M18.6). It adds no feature, route, provider, dependency, migration,
schema change, workflow, or analytical behaviour. It is the single document to
read before deploying, operating, or extending the platform.

**Release state:** migration head `f3d6a8b2c517`, 49 preconstruction routes,
20 preconstruction tables, 6 migrations, provider disabled in production.

---

## 1. What the platform does, and what it refuses to do

A user assembles a **Review Set** of project documents, prepares immutable
content from them, extracts or authors **scope assertions**, accepts the ones
they agree with, **compares** accepted assertions across documents to produce
advisory **findings**, reviews those findings, and — if they choose — records a
**follow-up** pointing at the RFI or Change Order they created in that record's
own workflow.

At no point does the platform decide anything. It has no authority to create,
approve, or modify a construction record; every state change that matters is a
human clicking a button, and the vocabulary deliberately contains no
legal-conclusion terms.

---

## 2. Data flow

```text
Document (authoritative)                        [M13/M16 — unchanged]
  └─ DocumentExtraction ─ DocumentPageText      current searchable text
       │
       ▼ read-only
  PreconstructionReviewSource                   pinned checksum + extraction
       │
       ▼ preparation worker
  ContentSnapshot ─ ContentPage ─ ContentSegment    IMMUTABLE, lineage-pinned
       │
       ▼ provider (disabled) or human authoring
  ScopeAssertionSet ─ ScopeAssertion ─ AssertionEvidence   IMMUTABLE content
       │                    │
       │                    └─ AssertionReview            APPEND-ONLY
       ▼ accepted assertions only
  ComparisonPlan ─▶ comparison manifest ─▶ FindingSet      IMMUTABLE
       │                                      │
       │                                      ├─ Finding
       │                                      ├─ FindingAssertion  (pins the
       │                                      │   authorizing review id)
       │                                      └─ FindingEvidence   (cites
       │                                          assertion evidence, never
       │                                          copies a second time)
       │                                            │
       │                                            └─ FindingReview APPEND-ONLY
       ▼ accepted findings only
  FindingFollowUp ─▶ links an EXISTING rfi / change_order / submittal
                     (created by the human in that record's own workflow)

  ExecutionMetric ── measures any of the above; restates none of it
```

**Direction is one-way.** Preconstruction reads Documents, Drawing Revisions,
and extraction output. Nothing authoritative reads preconstruction, and no
preconstruction service constructs an `RFI`, `ChangeOrder`, `Submittal`,
`PunchItem`, `EntityRelationship`, `Task`, `DrawingRevision`, or `Document` —
asserted by a release test that greps all six service modules.

---

## 3. Request flow

Every one of the 49 routes follows the same order:

```text
HTTP request
  → authentication (memory-only access JWT, database-backed user validation)
  → get_owned_project(project_id)          403 on a foreign project
  → nested resolution: finding → plan → review set   404, never a leak
  → strict MutationModel parse             422 on unknown/forbidden fields
  → service call                           owns the transaction
  → bounded, allowlist-filtered response
```

Routes never commit or roll back — verified by a release test that scans the
route module. Services own every transaction boundary.

---

## 4. Worker flow

Two finite CLI commands, both claim-and-exit, neither a daemon:

```text
cron ─▶ python -m app.commands.process_preconstruction_preparation
          recover expired leases
          while within runtime budget and batch size:
              claim one run   (FOR UPDATE SKIP LOCKED on PostgreSQL)
              prepare → immutable snapshot
              record metric
          exit

cron ─▶ python -m app.commands.process_preconstruction_analysis   [NOT SCHEDULED]
          same shape; invokes the allowlisted provider
```

The analysis cron is **deliberately absent from `render.yaml`**. The provider
is disabled, HTTP run creation is refused while it is disabled, and scheduling
it is gated behind the release gate in `AI_PRECONSTRUCTION_OPERATIONS.md`.

A third finite command is offline and touches no database:

```text
python -m app.commands.run_preconstruction_evaluation
```

Both workers stop claiming new work at
`PRECONSTRUCTION_EXECUTION_WORKER_MAX_RUNTIME_SECONDS`; work already claimed
always finishes. Startup refuses a budget longer than either lease window,
because a batch outliving its lease could still be processing work another
worker has recovered.

---

## 5. Ownership boundaries

| Boundary | Mechanism | Failure mode |
|---|---|---|
| Project isolation | `get_owned_project` before any nested id | 403 |
| Cross-project reach | project-filtered lookup on every id | 404, no existence leak |
| Unauthenticated | session dependency | 401 |
| Link targets | `resolve_relationship_entity(require_selectable=True)` | 404 / 409 |
| Mass assignment | `MutationModel` (`extra="forbid"`) | 422 |
| Archived records | explicit status guard in the service | 409 |

Server-owned and never client-supplied: project identity, lifecycle status,
origin, all hashes, provider profile and confidence, match scores and reasons,
evidence excerpts, pinned review ids, template versions, reviewer identity, and
every timestamp.

---

## 6. Provider boundary

`PreconstructionAIProvider` is an ABC reached only through an explicit factory
whose allowlist is exactly `disabled` and `fake_test`. A release test asserts
the factory source contains no `import_module`, `__import__`, `eval`, `exec`,
or `getattr` — there is no path to a live SDK.

The provider DTO carries a manifest hash, version identifiers, bounded source
descriptors, and typed untrusted content segments. It has **no** database,
session, ownership, storage, binary, URL, credential, or tool access. Results
are strictly parsed Pydantic, byte-bounded, and revalidated against the pinned
manifest; any structural failure rejects the entire result.

A provider may never introduce a candidate, assertion, or evidence record; mark
anything accepted; create a project record; or change a manifest. Severity it
proposes is clamped to one step from the documented default.

**Deterministic comparison requires no provider at all** and is the production
path.

---

## 7. Immutable records

| Record | Immutable after | Enforcement |
|---|---|---|
| ContentSnapshot / Page / Segment | preparation completes | unique lineage fingerprint; no update path |
| ScopeAssertion content | persistence | provider content never rewritten; supersede creates a new row |
| AssertionEvidence | persistence | `RESTRICT` from findings; no update path |
| Analysis manifest + hash | run creation | recomputation forbidden; formula frozen |
| AssertionSet content hash | persistence | reproducible from pinned inputs |
| Comparison manifest + hash | run execution | pins assertion ids **and** the exact authorizing review |
| FindingSet / Finding / links / evidence | persistence | new run creates a new set; prior sets retained |
| ExecutionMetric | write | one row per execution; no `updated_at` |

Three tables are append-only and carry no `updated_at` at all —
`preconstruction_assertion_reviews`, `preconstruction_finding_reviews`, and
`preconstruction_execution_metrics` — asserted by a release test.

Four independent hash formulas exist and none was ever modified after its
milestone: the M18.1 analysis manifest, the M18.2 lineage fingerprint, the
M18.3 assertion content hash, and the M18.4 comparison manifest plus finding
content hash.

---

## 8. Deterministic components

Everything below produces byte-identical output for identical input, with no
clock, randomness, iteration-order, or provider dependence:

- readiness (both review-set and comparison), including its diagnostics block —
  which deliberately carries **no measured duration**;
- the scope taxonomy (96 concepts, exact alias resolution only);
- content segmentation and lineage fingerprints;
- the matching engine — named match classes, documented component weights,
  bounded Jaccard as the only lexical signal;
- candidate generation, deduplication, and ordering;
- all four manifest and content hashes;
- follow-up draft assembly;
- the evaluation suite and its digest.

There are no embeddings, no vector store, no semantic similarity, no machine
learning, and no threshold tuned against real project data.

---

## 9. Human review points

| Gate | Who decides | Can it be bypassed? |
|---|---|---|
| Which sources enter a review set | user | no |
| Document role of each source | user | never inferred |
| Request preparation / analysis | user | no |
| Accept, reject, or flag an assertion | reviewer | no; append-only history |
| Author an assertion by hand | reviewer | starts `accepted`, `origin=manual` |
| Which assertions are comparable | reviewer | accepted-only by default |
| Accept, reject, exclude, or re-open a finding | reviewer | no bulk action exists |
| Raise a follow-up | reviewer | accepted findings only |
| Create the RFI / Change Order | user, in that workflow | preconstruction cannot |
| Link the created record | user | resolver-validated |

No confidence value, severity, score, match class, or evaluation number can
accept anything. `intentional_exclusion` is a first-class decision, and raising
follow-up work from it is refused because it contradicts a recorded judgement.

---

## 10. Final API inventory

49 routes, all under `/projects/{project_id}/preconstruction`, all
ownership-gated.

| Milestone | Count | Routes |
|---|---|---|
| M18.1 review foundation | 14 | review-sets (5), sources (4), source-candidates, readiness, runs (POST/GET), run detail/cancel/retry |
| M18.2 preparation | 5 | source prepare, preparation-run get/cancel/retry, source content |
| M18.3 assertions | 8 | scope-taxonomy, assertion-sets (2), assertions (2), manual, reviews, supersede |
| M18.4 comparison | 13 | comparison-plans (5), readiness, runs, finding-sets (2), findings (2), reviews, manual |
| M18.5 follow-ups | 6 | finding follow-ups (2), plan follow-ups, update, link, close |
| M18.6 metrics | 1 | execution-metrics (read-only) |
| **Total** | **49** | of 176 route entries app-wide |

Read-only surfaces have no write route at all: execution metrics return 405 on
POST, PUT, and DELETE.

---

## 11. Final data-model inventory

20 preconstruction tables, 366 columns, 58 indexes, 107 CHECK constraints, of
63 tables app-wide.

| Milestone | Tables |
|---|---|
| M18.1 | `review_sets`, `review_sources`, `analysis_runs`, `analysis_attempts` |
| M18.2 | `preparation_runs`, `content_snapshots`, `content_pages`, `content_segments` |
| M18.3 | `scope_assertion_sets`, `scope_assertions`, `assertion_evidence`, `assertion_reviews` |
| M18.4 | `comparison_plans`, `finding_sets`, `findings`, `finding_assertions`, `finding_evidence`, `finding_reviews` |
| M18.5 | `finding_follow_ups` |
| M18.6 | `execution_metrics` |

All are prefixed `preconstruction_`. Deletion behaviour: `CASCADE` from
`projects` throughout the advisory graph; `RESTRICT` on every reference to
authoritative content (documents, drawing revisions, snapshots, pages,
segments, assertion evidence) so cited material cannot vanish beneath a
finding; `SET NULL` only for optional pointers whose loss is not corrupting.

Every controlled value is enforced twice — once by a CHECK constraint and once
by a Python allowlist — and a release test asserts the two agree for all
eleven vocabularies.

---

## 12. Migration chain

Linear, single head, no branch, no backfill anywhere.

```text
f7c5d0b3e826  (M17 resource planning)
   └─ a8f4c2d6e190  M18.1  review foundation            +4 tables
        └─ b9e5d3f7a201  M18.2  content preparation     +4 tables, +1 analysis type
             └─ c1f7b4e28d35  M18.3  scope assertions   +4 tables, +1 analysis type
                  └─ d5a3f9c14e28  M18.4  comparison    +6 tables, +2 analysis types
                       └─ e2b8d4f7c103  M18.5  follow-ups   +1 table
                            └─ f3d6a8b2c517  M18.6  metrics  +1 table   ◀ head
```

No M18 migration altered an existing application table, and only the
analysis-type allowlist was ever widened. Every migration has a paired
`test_*_migration.py` performing a real upgrade → seed → upgrade → assert →
downgrade → re-upgrade → single-head check.

---

## 13. Production configuration

70 `PRECONSTRUCTION_*` settings. A release test asserts every setting declared
in `config.py` appears in `backend/.env.example` — the deployment contract
cannot drift from the code.

**Values production must keep:**

```dotenv
PRECONSTRUCTION_AI_ENABLED=false
PRECONSTRUCTION_AI_PROVIDER=disabled
PRECONSTRUCTION_AI_FAKE_PROVIDER_ALLOWED=false
DOCUMENT_OCR_ENABLED=false
DOCUMENT_OCR_PROVIDER=disabled
```

Startup fails fast on: an unknown provider, `enabled` with the disabled
provider, the fake provider in production, a non-positive or over-maximum
bound, a page size above its own maximum, a findings cap above the candidate
cap, a persist chunk larger than the largest possible finding set, a pair
budget below the candidate cap, and a worker runtime budget exceeding either
lease window.

Cost rates default to `0`, meaning **no rate configured** — cost is then
reported as absent rather than as zero, so an operator is never shown a
fabricated figure.

---

## 14. Deployment requirements

1. Apply migrations through `f3d6a8b2c517`. The API service already runs
   `alembic upgrade head` on start.
2. Keep the five disabled-provider/OCR values above.
3. The preparation cron is declared in `backend/render.yaml` at
   `5,20,35,50 * * * *`, offset from the every-ten-minute extraction cron so
   the two finite jobs never contend. It carries **no object-storage
   credential** because it reads committed `DocumentPageText` rows.
4. **Do not schedule the analysis cron.** It is intentionally absent.
5. No new infrastructure: no queue, no cache, no vector store, no additional
   service, no new dependency.

---

## 15. Operational procedures

**Daily/automated**
- Watch the preparation cron exit status and `runtime_budget_reached`.
  Sustained truthiness means the cadence or batch size needs revisiting.
- Watch pending preparation age and processing lease age.

**Per release**
- `python -m app.commands.run_preconstruction_evaluation` — finite, offline,
  exits non-zero on regression. A changed digest with a passing suite means the
  case set changed; a failing case means documented engine behaviour changed
  and must be either reverted or documented.
- `alembic current`, `alembic heads`, `alembic check`.

**Incident recovery**
- Expired leases recover automatically on the next bounded invocation.
- `--retry-failed` only for eligible runs below their maximum attempts.
- Re-prepare a stale source through the owned API; never overwrite or delete a
  historical snapshot.
- Never edit lifecycle fields by hand outside a documented database incident.
- Never delete a follow-up to "clean up" after a reversed finding review — that
  history is the audit trail.

**Safe to log:** identifiers, counts, durations, provider profile, versions,
approved failure and warning codes, a manifest hash prefix.
**Never log:** document or segment text, assertion text, evidence excerpts,
finding titles, summaries or rationales, draft text, reviewer or closure notes,
prompts, raw provider responses, lease tokens, credentials, storage metadata,
or exception internals.

---

## 16. Maintenance procedures

- **Taxonomy change** — `TAXONOMY_VERSION` is a code change shipped with a
  release note. Existing assertions keep the version they pinned and are
  reported as unsupported rather than silently reinterpreted.
- **Vocabulary change** — add the value to the Python map *and* the model CHECK
  *and* a migration. The release test will fail if the two disagree.
- **Hash formula change** — do not. Introduce a new version alongside.
- **Adding an analysis type** — widen the model CHECK, the migration allowlist,
  `ANALYSIS_TYPES`, and (only if clients may create it) the `AnalysisType`
  request literal. Labeling and creatability are deliberately separate.
- **Retention** — `metrics_retention_rows` is configured but no pruning job
  exists yet; rows persist until project deletion.

---

## 17. Known limitations at release

Carried forward and re-verified during closeout:

1. **Provider-validated comparison is not wired to a worker.** The contract,
   validation, and eight fake modes are complete and tested; the route refuses
   the analysis type explicitly rather than pretending. Deterministic
   comparison is the production path and is fully functional.
2. **Production OCR is disabled**; image-only PDFs yield no searchable text.
3. **Revision comparison is structural**, not visual — no image or geometric
   diff.
4. **Deterministic comparison runs inline**, bounded by the pair budget rather
   than queued.
5. **No pruning job** for execution metrics.
6. **`response_bytes` and `query_count` columns are never populated** by current
   call sites; they exist for the provider-validation worker.
7. **Manifest reuse is per-plan**, not cross-plan.
8. **Follow-up linking is by numeric identifier**, not a searchable picker, and
   carries no draft prefill into the workflow route — the hash router
   serializes identifiers only and draft wording does not belong in a URL.
9. **`evaluation_run` is a valid execution kind that nothing records**, because
   the evaluation command deliberately opens no database session.
10. **All performance evidence is local SQLite/TestClient.** PostgreSQL query
    plans, production latency, and browser rendering are Not Verified.
11. **Prompt injection is mitigated, not solved.** Content is typed untrusted
    data, separated from fixed instructions, with no tools, URLs, storage, or
    database access across the provider contract.
12. **Four high-severity npm advisories exist in dev-only transitive packages**
    (`brace-expansion`, `nanoid`, `postcss`, `undici`). `npm audit --omit=dev`
    reports **0 vulnerabilities**; nothing ships to the browser. Remediation
    requires a dependency bump, which is out of scope for a closeout milestone.

None of these is a correctness or safety defect. Each is a bounded, documented
absence.

---

## 18. Release readiness

| Gate | State |
|---|---|
| Backend tests | 564 passed / 944 subtests |
| Frontend tests | 656 across 94 files |
| Migration lifecycle | fresh → head → downgrade → re-upgrade verified |
| `alembic check` | no drift |
| `alembic heads` | single head `f3d6a8b2c517` |
| `pip check` | no broken requirements |
| ESLint | clean, zero warnings |
| Production build | passes |
| `npm audit --omit=dev` | 0 vulnerabilities |
| Ownership coverage | 49/49 routes |
| Vocabulary/CHECK agreement | 11/11 |
| Authoritative-write scan | 0 occurrences across 6 service modules |
| Config/deployment-contract drift | 0 of 70 settings |

**The AI Preconstruction platform is releasable with the provider disabled.**
Enabling a live provider remains gated behind the release gate in
`AI_PRECONSTRUCTION_OPERATIONS.md`.
