# AI Preconstruction Operations

M18.1 ships no live AI provider. Production should retain the disabled values
until a later milestone implements, secures, evaluates, and approves a real
adapter.

## Configuration

```dotenv
PRECONSTRUCTION_AI_ENABLED=false
PRECONSTRUCTION_AI_PROVIDER=disabled
PRECONSTRUCTION_AI_MODEL=disabled
PRECONSTRUCTION_AI_MAX_ATTEMPTS=3
PRECONSTRUCTION_AI_LEASE_SECONDS=300
PRECONSTRUCTION_AI_BATCH_SIZE=5
PRECONSTRUCTION_AI_MAX_SOURCES_PER_REVIEW=250
PRECONSTRUCTION_AI_MAX_MANIFEST_BYTES=262144
PRECONSTRUCTION_AI_MAX_RESULT_BYTES=32768
PRECONSTRUCTION_AI_RETRY_BASE_SECONDS=30
PRECONSTRUCTION_AI_RETRY_MAX_SECONDS=3600
PRECONSTRUCTION_AI_FAKE_PROVIDER_ALLOWED=false
```

All integer values are positive and bounded. Retry base cannot exceed retry
maximum. Enabled mode cannot use the disabled provider. Production rejects the
fake provider and its allow flag. Unknown providers fail startup validation.
No provider credential setting exists in M18.1.

M18.2 content preparation has no provider credential or network dependency.
It snapshots current native-PDF extraction and retains production OCR as
disabled.

## Finite Worker

The worker processes a bounded batch and exits. It is not a daemon and does
not use a FastAPI background task, Redis, Celery, or an in-process loop.

```powershell
python -m app.commands.process_preconstruction_analysis
python -m app.commands.process_preconstruction_analysis --batch-size 5 --max-jobs 10
python -m app.commands.process_preconstruction_analysis --run-id 42
python -m app.commands.process_preconstruction_analysis --retry-failed --max-jobs 5
python -m app.commands.process_preconstruction_analysis --lease-seconds 300
```

The command atomically claims pending attempts with row locking and
`SKIP LOCKED` where supported, assigns an opaque lease token, executes the
configured provider, strictly validates and bounds output, and commits a safe
terminal state or append-only retry attempt. Retry delay uses bounded
exponential backoff. Expired leases become failed attempts and are retried only
within the run's maximum attempt count.

Schedule this finite command externally only after a real provider phase has
defined provider availability, credentials, network policy, monitoring,
evaluation, and incident response. The disabled worker is safe and performs no
network call; normal HTTP run creation is blocked while the provider is
disabled.

## Monitoring

Monitor counts and ages by safe lifecycle category:

- pending attempts past `available_at`;
- processing attempts near or beyond lease expiry;
- retryable, failed, unavailable, cancelled, and completed run totals;
- repeated safe failure codes;
- manifest/result size rejection; and
- worker exit status and finite processed counts.

Never log manifest JSON, source filenames where policy forbids them, document
text, prompts, raw provider responses, lease tokens, credentials, storage
metadata, or exception internals. IDs, counts, durations, provider profile,
and approved failure codes are sufficient for operations.

## Recovery

1. Correct provider or database availability without changing stored
   manifests.
2. Run one bounded command. Expired leases recover automatically.
3. Use `--retry-failed` only for eligible failed/unavailable runs below their
   maximum attempts.
4. Confirm attempt history remains append-only and the run manifest hash is
   unchanged.
5. Cancel a pending/processing run through the owned API when it should not
   execute.

Do not update run or attempt lifecycle fields manually except during a
documented database incident. Do not copy production content into fake-provider
fixtures.

## Content Preparation Worker

Run preparation separately from analysis:

```powershell
python -m app.commands.process_preconstruction_preparation
python -m app.commands.process_preconstruction_preparation --batch-size 5 --max-jobs 10
python -m app.commands.process_preconstruction_preparation --run-id 42
python -m app.commands.process_preconstruction_preparation --retry-failed --max-jobs 5
python -m app.commands.process_preconstruction_preparation --lease-seconds 300
```

The finite command claims only preparation runs and exits. It reads
`DocumentPageText`, performs batched immutable snapshot/page/segment writes,
and makes no storage, OCR, browser, or AI request. Monitor pending age,
processing lease age, terminal safe failure codes, page/segment/character
counts, warning counts, and command exit status. Never log segment text,
search queries, filenames where policy forbids them, hashes beyond operational
need, or lease material.

Preparation limits and retry settings use the
`PRECONSTRUCTION_PREPARATION_*` and `PRECONSTRUCTION_CONTENT_*` variables in
`backend/.env.example`. Apply migration `b9e5d3f7a201` before scheduling the
command. Expired leases recover on the next bounded invocation. Reprepare a
stale source through the owned API; do not overwrite or delete its historical
snapshot.

## Production Schedule

`backend/render.yaml` schedules preparation as
`construction-scheduler-preconstruction-preparation`:

```yaml
schedule: "5,20,35,50 * * * *"
startCommand: python -m app.commands.process_preconstruction_preparation --max-jobs 10
```

The cadence is offset from the every-ten-minute document-extraction cron so
preparation observes completed extractions and the two finite jobs never
contend for the same rows. The job carries no object-storage credential
because preparation reads committed `DocumentPageText` rows and never opens a
stored object. It pins the disabled provider values so a misconfigured
environment cannot enable a provider through a background job.

The analysis worker is intentionally absent from `render.yaml`. The provider
is disabled, HTTP run creation is rejected while it is disabled, and the
release gate below governs when scheduling becomes appropriate. Do not add
that cron as part of a deployment change.

## Scope Assertion Extraction

M18.3 adds the `scope_assertion_extraction` analysis type. It reuses the
existing analysis worker and command; no additional worker or cron entry is
introduced. Because the provider remains disabled in production, scope
extraction runs cannot be created there and the analysis cron stays
unscheduled. Human-authored assertions and review remain fully available.

The taxonomy is a versioned built-in constant with no credential, no editing
API, and no database state. Changing `TAXONOMY_VERSION` is a code change that
must ship with a migration-free release note; existing assertions keep the
version they pinned.

Monitor safe scope categories only: run and assertion-set identifiers,
assertion and evidence counts, warning counts, validation failure codes
(`invalid_scope_result`, `invalid_scope_source`, `unknown_scope_concept`,
`invalid_scope_evidence`, `missing_scope_evidence`, `scope_result_too_large`,
`scope_persistence_failed`), taxonomy and schema versions, and latency. Never
log requirement text, evidence excerpts, reviewer notes, prompts, or provider
response bodies.

A structurally invalid provider result rejects the entire assertion set and
leaves no partial rows. Re-running is safe: each run creates a new immutable
set and never rewrites prior assertions or human decisions.

## Scope Comparison

M18.4 adds two analysis types: `scope_comparison` (deterministic only) and
`scope_comparison_validation` (deterministic candidates plus optional provider
validation).

**Deterministic comparison requires no AI provider and is available in
production with the provider disabled.** It runs inline because candidate
generation is bounded by configuration and touches no external system: no
storage, no OCR, no network, no provider. Provider-validated comparison is
refused rather than silently downgraded while the provider is disabled, so no
additional worker or cron entry is introduced.

Comparison plans are named and persistent. The first run locks a plan so
historical results stay reproducible; archived plans are read-only. The
comparison manifest pins exact assertion ids, the exact human review decision
that made each assertion eligible, and evidence identity, so a later review
change produces a new manifest instead of rewriting history.

Monitor safe comparison categories only: comparison plan, run, and finding-set
identifiers, candidate and finding counts, warning codes
(`assertion_limit_reached`, `stale_assertion_evidence`,
`unsupported_taxonomy_version`, `candidate_limit_reached`,
`revision_lineage_incomplete`, `duplicate_candidates_merged`,
`finding_limit_reached`), validation failure codes
(`invalid_comparison_result`, `invalid_comparison_candidate`,
`invalid_comparison_assertion`, `invalid_comparison_evidence`,
`unknown_finding_type`, `comparison_result_too_large`), taxonomy and schema
versions, and latency. Never log finding summaries or rationales, assertion
text, evidence excerpts, reviewer notes, prompts, or provider response bodies.

Findings are advisory. Accepting one records a human decision and creates no
RFI, Change Order, procurement action, relationship, or notification. Apply
migration `d5a3f9c14e28` before enabling comparison.

## Follow-Up Actions

M18.5 adds human-initiated follow-up actions raised from accepted findings. It
introduces **no analysis type, no worker, no cron entry, no provider call, and
no credential**. Every transition is a synchronous, bounded, authenticated
human action, so `render.yaml` is unchanged.

Apply migration `e2b8d4f7c103` before enabling follow-ups. It creates one table
and performs no backfill, so no existing accepted finding gains a follow-up.

Monitor safe follow-up categories only: follow-up, finding, comparison-plan,
and target identifiers, action type, status counts by category, and refusal
counts for the eligibility gate, the duplicate-action index, and the per-finding
and per-plan limits. Never log draft titles or bodies, closure notes, reviewer
notes, assertion text, or evidence excerpts.

A follow-up is advisory bookkeeping. Raising, linking, or closing one creates
no RFI, Change Order, Submittal, relationship, procurement action, or
notification, and approves nothing. If a reviewer reverses a finding's
acceptance, existing follow-ups are retained and flagged rather than rewritten;
do not delete them to "clean up" — that history is the audit trail.

Follow-up limits use the `PRECONSTRUCTION_FOLLOW_UP_*` variables in
`backend/.env.example`.

## Release Gate

Before enabling any future live adapter, require project-isolation tests,
strict result-schema evaluation, malicious-document and prompt-injection
tests, provider data-retention review, least-privilege secrets, outage and
timeout behavior, cost/rate limits, human-review enforcement, auditability,
and an explicit rollback to `disabled`.
