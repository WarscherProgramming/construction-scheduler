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

## Release Gate

Before enabling any future live adapter, require project-isolation tests,
strict result-schema evaluation, malicious-document and prompt-injection
tests, provider data-retention review, least-privilege secrets, outage and
timeout behavior, cost/rate limits, human-review enforcement, auditability,
and an explicit rollback to `disabled`.
