# AI Preconstruction Performance, Evaluation, and Cost

## Purpose

M18.6 makes the M18.1–M18.5 preconstruction stack measurable and safe at
project scale. It adds no analysis capability and changes no analytical result:
every optimization here is required to produce byte-identical output to the
code it replaced.

It introduces no embedding, no vector store, no autonomous decision, no
automatic record creation, no live provider requirement, and no second copy of
any evidence, finding, or review.

## What changed, and why each change is output-neutral

### Memoized tokenization

Coverage matching is O(requirements × coverages), and `compare_assertions`
previously re-tokenized the same subject and requirement strings once per pair.
`tokenize` is now memoized with a bounded LRU cache.

Tokenization is a pure function of its argument, so caching changes cost and
nothing else — the same input still yields the same token set, the same score,
and the same match class. Measured on local hardware:

| Pairs | Memoized | Un-memoized | Speed-up |
|---|---|---|---|
| 625 | 3.8 ms | 13.4 ms | 3.5× |
| 2,500 | 12.2 ms | 55.2 ms | 4.5× |
| 10,000 | 48.2 ms | 226.7 ms | 4.7× |

### One resolution per comparison request

A comparison request previously resolved the plan's eligible assertion
population twice: once for readiness and once for candidate generation. The
route now resolves once and hands the same `ResolvedPopulation` to both. The
manifest, ordering, and pinned review ids are identical either way; a test
asserts `resolve_eligible_assertions` is called exactly once per run.

### One grouped scan for finding summaries

`finding_summary_counts` ran three aggregate queries over the same rows.
Grouping by status, finding type, and origin together and folding the result in
Python produces identical numbers from **one** query, asserted by test.

### Bounded persistence

Finding, link, and evidence rows are written in configurable chunks
(`PRECONSTRUCTION_EXECUTION_PERSIST_CHUNK_SIZE`, default 500) so a large
finding set never builds one unbounded statement. A test runs a comparison with
a chunk size of 1 and asserts every row is written exactly once.

## Pair budget

`estimate_pair_budget` computes the **exact** number of comparisons a run would
perform — `left × right` — and checks it against
`PRECONSTRUCTION_EXECUTION_MAX_COMPARISON_PAIRS`. This is arithmetic, not a
heuristic.

Exceeding the budget blocks readiness with a plain-language blocker and
**refuses the run with 422**. It deliberately does not truncate the population:
silently comparing part of a plan the reviewer believes was compared in full
would be the worst possible failure mode for a scope review.

## Manifest reuse

The comparison manifest already pins the plan, its configuration hash, the
exact assertion ids, the exact review that made each eligible, and evidence
identity. An identical manifest hash therefore means identical inputs, so a
re-run would reproduce the same findings byte for byte.

`reuse_identical_manifest` is an **opt-in** run flag. When set and a completed
set with the same manifest hash exists, that set is returned and the response
reports `manifest_reused: true`. Nothing is written, rewritten, superseded, or
deleted.

The default is off, so M18.4's contract is unchanged: a re-run still creates a
new immutable finding set. A changed human review changes the manifest, so
reuse correctly declines and a new set is produced — asserted by test.

## Execution metrics and cost accounting

`preconstruction_execution_metrics` is the single canonical place for *how an
execution behaved*. One row per execution, written once, never updated.

It deliberately restates nothing. Candidate, finding, warning, page, and
segment counts stay on the records that own them; a test asserts the metrics
table has no such column. What it does hold is timing by controlled phase,
query and byte counts, billable units, cost, manifest reuse, and any budget
stop reason.

Four controlled execution kinds are recorded: `preparation_run`,
`analysis_attempt`, `scope_comparison`, and `evaluation_run`. Phase names are
allowlisted; an unknown phase or kind raises rather than being stored.

**Cost is absent, not zero, when no rate is configured.** Rates are integer
micro-units per billable unit and default to `0`, which reports
`cost_rate_configured: false` and a null cost. An operator is never shown a
fabricated figure, and no currency is implied.

Measurement never breaks the thing being measured: recording runs inside a
SAVEPOINT, a duplicate is returned rather than raised, and any failure is
logged with identifiers only and swallowed.

## Diagnostics

Comparison readiness gains a bounded `diagnostics` block: the pair budget, the
persist chunk size, the evidence limit, and whether metrics are enabled.

It contains **no measured duration**. Readiness is documented as deterministic,
so identical inputs must produce a byte-identical response; timings live on the
metric record instead. A test asserts two consecutive readiness calls are equal
and that no timing vocabulary appears in the payload.

## Response size

`evidence_limit` is now a bounded query parameter on the findings listing
(0 to the configured maximum, default 10). Evidence dominates a finding page's
bytes, so a caller that does not need it can request `evidence_limit=0`. A
value above the configured cap is clamped; a value above 50 is refused with
422.

## Evaluation framework

`backend/app/preconstruction/evaluation.py` scores the deterministic engine
against a labeled golden suite. It is pure: no ORM, no session, no
configuration, no network, no provider, no database write, and no project data.

Every case states its expected outcome explicitly, so the report answers one
question honestly — *does the documented behaviour still hold?* — rather than
producing an opaque quality score. There is no machine learning, no embedding,
no similarity model, and no threshold tuned against real projects. Each case
pins one documented rule from `AI_SCOPE_COMPARISON.md`: the weak cap without a
concept match, the strong cap on a material mismatch, quantity versus unit
mismatch, the coverage outcomes, and the excluded-requirement exemption. A test
asserts every fixture concept code exists in the real taxonomy.

The `provider_assisted` suite scores a provider result against the candidates
it was allowed to judge. It measures **agreement and refusal, never
correctness**: whether a finding is genuinely a gap is a human decision, and no
number here can accept, reject, or escalate anything.

A stable digest over the scored outcomes makes a behaviour change visible
without diffing a full report.

```powershell
python -m app.commands.run_preconstruction_evaluation
python -m app.commands.run_preconstruction_evaluation --json
python -m app.commands.run_preconstruction_evaluation --covered-minimum partial
```

The command is finite, opens no database session, and exits non-zero on
regression, so it is safe in a release check. A test asserts it issues zero SQL
statements.

## Worker scalability

Both finite workers now stop claiming new work once
`PRECONSTRUCTION_EXECUTION_WORKER_MAX_RUNTIME_SECONDS` is reached; an already
claimed attempt or run always finishes. Configuration refuses to start if that
budget exceeds either lease window, because a batch outliving its lease could
still be processing work another worker has already recovered.

The result objects gain `runtime_budget_reached`, and an analysis attempt that
stopped at the budget records `runtime_budget_exceeded` on its metric row.

No new worker, cron entry, or provider requirement is introduced.

## API

```text
GET /projects/{project_id}/preconstruction/execution-metrics
```

Project-owned, bounded, allowlisted `execution_kind` filter, read-only — there
is no create, update, or delete route, asserted by test (405 on POST, PUT, and
DELETE). Payloads carry identifiers, counts, milliseconds, units, and cost
only.

`GET .../findings` gains `evidence_limit`; `POST .../runs` gains
`reuse_identical_manifest`; readiness gains `diagnostics`.

## Security

- Metrics inherit the same ownership gate as every other preconstruction route:
  a foreign project returns 403 and an anonymous request 401.
- The metrics payload carries no assertion text, evidence excerpt, reviewer
  note, prompt, or provider output; a test asserts those substrings never
  appear.
- The `execution_id` reference is deliberately untyped, so a metric never
  restricts or cascades into the record it measures. Deleting a measured
  finding set leaves the metric intact; deleting the project cascades it.
- No configuration here can enable a provider, relax a review requirement, or
  create a construction record.

## Migration

Alembic revision `f3d6a8b2c517` follows `e2b8d4f7c103`. It creates one table
with its constraints and indexes, performs **no backfill**, alters **no
existing table**, and widens **no existing allowlist**. No historical execution
gains a synthesized metric.

## Verification

Automated release evidence is 551 backend tests with 787 separately reported
backend subtests, and 656 frontend tests across 94 files: 1,207 primary tests.
M18.6-specific coverage is 29 backend tests plus 64 subtests across
`test_preconstruction_execution.py` and `test_execution_metrics_migration.py`,
and 8 frontend tests in `ExecutionDiagnostics.test.jsx` plus extended
API-client and hook coverage. ESLint, `pip check`, `alembic check`, and the
production build pass. No dependency or lockfile change is part of M18.6.

## Deferred

Cross-project metrics, metric retention pruning, PostgreSQL query-plan
verification, provider-validated comparison worker wiring, dashboard
integration of execution metrics, and any live provider adapter remain out of
scope and require later separately reviewed milestones.
