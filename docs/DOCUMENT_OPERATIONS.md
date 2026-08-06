# Document Management Operations

This runbook covers M16 storage, drawing delivery, relationships, extraction,
and search. Preserve project ownership, database history, and private object
keys during every incident. Logs may include aggregate job counts, safe error
categories, IDs needed for internal correlation, and duration; never log file
content, extracted text, credentials, cookies, tokens, request bodies, raw
provider URLs, or full storage keys.

## Scheduled Commands

Run both commands as finite jobs with the same `DATABASE_URL`, provider,
bucket, credentials, key prefix, limits, and production settings as the API:

```powershell
python -m app.commands.process_document_extractions --max-jobs 25 --prune-completed
python -m app.commands.process_attachment_cleanup --max-jobs 200 --prune-completed
```

Render declares document extraction every ten minutes and preconstruction
content preparation on an offset quarter-hour schedule. Attachment cleanup is
not declared in the current blueprint and requires a separate recurring
external schedule. Set scheduler timeouts above expected bounded runtime and
keep lease duration above the time between claim and completion. Overlapping
runs are supported by PostgreSQL row locking and lease tokens, but operators
should still alarm on growing pending counts, expired leases, or repeated
terminal failures.

## Object Storage Outage

**Symptoms:** upload/download `503` responses, failed existence checks, or a
growing cleanup retry queue. **Likely causes:** provider outage, DNS/TLS
failure, expired credentials, incorrect endpoint/region, or bucket policy.
**Immediate action:** pause avoidable uploads and destructive cleanup runs;
preserve metadata and queued jobs; do not remove keys manually. **Recovery:**
restore provider reachability and least-privilege credentials, then run a
small cleanup/extraction batch before normal scheduling. **Verification:**
provider health, one synthetic upload/download/exists/delete cycle, queue
counts, and safe API errors pass. **Data integrity:** PostgreSQL remains the
metadata authority; never guess or rewrite provider keys.

## Failed Upload Cleanup

**Symptoms:** upload fails after bytes were accepted or a cleanup job appears
for an object without active metadata. **Likely causes:** database commit,
connection, or compensating provider-delete failure. **Immediate action:**
retain the cleanup row and its attempt history; do not create replacement
Document metadata by hand. **Recovery:** restore database/provider health and
run `process_attachment_cleanup` with a small bound. **Verification:** the job
is `Completed`, the object no longer exists, and no active Document references
the key. **Data integrity:** cleanup metadata must commit before the object can
be forgotten; an already-missing object completes idempotently.

## Missing Object

**Symptoms:** owned metadata loads but download reports safe unavailability or
the provider returns not found. **Likely causes:** out-of-band bucket deletion,
incorrect prefix/provider migration, or incomplete restore. **Immediate
action:** stop automated deletion for the affected namespace and preserve the
Document row, audit trail, and issue/revision links. **Recovery:** restore the
exact object from backup under its recorded private key or restore a
consistent database/object-store snapshot. **Verification:** checksum, size,
MIME/signature, authenticated download, and any drawing viewer route pass.
**Data integrity:** do not upload unrelated bytes under the missing key or
silently repoint immutable drawing history.

## Extraction Worker Failure

**Symptoms:** pending jobs age, cron exits nonzero, or all jobs report a safe
database/storage processing failure. **Likely causes:** missing shared
configuration, database or provider outage, parser dependency failure, or
insufficient scheduler runtime. **Immediate action:** preserve jobs and inspect
safe category logs plus cron environment parity. **Recovery:** correct the
dependency/configuration and run one bounded job, then resume the recurring
command. **Verification:** claimed/completed counts advance, extraction status
changes, and search returns the expected synthetic term. **Data integrity:**
do not mark jobs complete or edit page text manually.

## Stuck Extraction Lease

**Symptoms:** a job remains `processing` beyond `lease_expires_at` and no
processor owns its token. **Likely causes:** terminated process, scheduler
timeout, host restart, or an undersized lease relative to batch runtime.
**Immediate action:** confirm no original command is still running; do not
clear the token while it may still finalize. **Recovery:** after expiry, run a
bounded processor so normal lease recovery issues a new token. **Verification:**
only the current token finalizes, attempt count is bounded, and the extraction
is terminal or retryable. **Data integrity:** stale workers must remain unable
to replace page rows.

## Repeated Extraction Failure

**Symptoms:** retry backoff repeats or a job reaches max attempts with a safe
failure code. **Likely causes:** corrupt/encrypted input, persistent storage
failure, parser resource limit, or unsupported content. **Immediate action:**
stop automatic retry loops and classify the safe failure code without logging
content. **Recovery:** fix infrastructure or replace the source through a
normal product workflow; use explicit reprocess only after the cause changes.
**Verification:** one controlled retry reaches the factual terminal state and
does not create duplicate active jobs. **Data integrity:** keep the prior
searchable extraction until a same-checksum replacement completes.

## Parser Crash

**Symptoms:** the finite command exits unexpectedly, a lease expires, or the
parser returns `parser_error`. **Likely causes:** malformed PDF, native library
failure, memory pressure, or limits exceeded before cooperative timeout.
**Immediate action:** isolate the synthetic/reported file identity without
copying content to logs; preserve the object and job. **Recovery:** reproduce
in an isolated bounded environment, patch/upgrade only through a reviewed
release, and let lease recovery retry if appropriate. **Verification:** corrupt
input fails safely, healthy input still completes, and no temporary files or
page images remain. **Data integrity:** never persist partial replacement page
rows as a completed extraction.

## Search Index Drift

**Symptoms:** extraction is searchable but known text returns no result,
vectors are null, or Alembic reports schema drift. **Likely causes:** failed
vector population, manual database changes, interrupted migration, or an
extractor upgrade without deliberate reprocessing. **Immediate action:**
compare extraction checksum to Document checksum and inspect vector/index
counts without printing text. **Recovery:** apply the current migration, use
controlled reprocess for affected Documents, and `REINDEX` only under normal
PostgreSQL maintenance procedures. **Verification:** GIN index exists, vectors
are populated, `EXPLAIN` can use it on representative data, and project/deleted
filters remain correct. **Data integrity:** do not bulk overwrite normalized
text or bypass checksum guards.

## OCR Unavailable

**Symptoms:** raster/image-only content reports `unavailable` with an OCR
warning and is absent from content results. **Likely causes:** expected release
configuration: `DOCUMENT_OCR_ENABLED=false` and provider `disabled`.
**Immediate action:** explain the factual limitation; do not relabel the file
as searchable or install an undeclared system binary on a production host.
**Recovery:** none in M16; metadata search and direct viewing/download remain
available. **Verification:** native-text PDFs still extract and the UI labels
OCR-unavailable states honestly. **Data integrity:** no empty/fabricated OCR
page rows are persisted.

## Migration Failure

**Symptoms:** deploy halts at Alembic, current differs from head, or constraint
creation fails. **Likely causes:** database availability, inconsistent prior
schema, concurrent releases, or unexpected historical data. **Immediate
action:** stop the new API release and concurrent migrations; preserve a
backup and capture migration ID/error without secrets. **Recovery:** restore
database health, resolve the exact data/schema conflict, and rerun the linear
chain; prefer application rollback over an untested production downgrade.
**Verification:** one head, current `e4b7c2d9f651`, Alembic check clean, API
health, and representative document/search queries pass. **Data integrity:**
never edit an already-shipped migration or drop factual drawing/relationship
history to force an upgrade.

## PDF Viewer Worker Failure

**Symptoms:** metadata loads but page render reports worker/PDF failure.
**Likely causes:** stale cached chunk, blocked same-origin worker, corrupt or
encrypted PDF, CSP/proxy mismatch, or browser incompatibility. **Immediate
action:** retain metadata and authenticated download; inspect safe browser
console/network categories without exposing Blob URLs or tokens. **Recovery:**
deploy matching app/worker assets, clear the affected deployment cache, or use
download for unsupported source PDFs. **Verification:** one-page and multipage
synthetic PDFs render, the worker is same-origin, navigation/search work, and
the single Blob is revoked on exit. **Data integrity:** viewer failure must not
change revision metadata or current/superseded lineage.

## Relationship Target Missing

**Symptoms:** a related record displays unavailable and has no navigation
action. **Likely causes:** target soft deletion/archive, retained historical
link, or exceptional out-of-band parent removal. **Immediate action:** retain
the relationship as factual context and inspect the target through its domain
lifecycle. **Recovery:** restore availability only through that domain's
supported workflow, or remove the relationship explicitly if it is no longer
useful. **Verification:** labels remain directional, unavailable targets leak
no fields, and new links to unavailable records are rejected. **Data
integrity:** never hard-delete a target merely to clean the generic graph.

## Permanent Purge Preparation

**Symptoms:** retention policy requires irreversible deletion, which M16 does
not implement. **Likely causes:** legal/contract policy or storage lifecycle
planning. **Immediate action:** do not use ad hoc SQL or bucket deletion.
Inventory Document lineage, drawing revisions/issues, relationships,
attachments, extraction rows/jobs, and soft-deletion state. **Recovery:** not
applicable; design and review a future purge transaction plus object cleanup
workflow. **Verification:** a dry-run inventory accounts for every reference
and backup/hold requirement. **Data integrity:** drawing history and legal
holds take precedence over storage reclamation.

## Future Soft-Delete Restore

**Symptoms:** an operator is asked to restore a soft-deleted Document, but no
restore API/UI exists. **Likely causes:** accidental user deletion or a future
retention request. **Immediate action:** preserve metadata and the retained
private object; do not toggle fields manually in production. **Recovery:** wait
for a reviewed restore capability that revalidates object existence,
checksum, folder/project ownership, current-version rules, drawing conflicts,
and extraction state. **Verification:** future restore tests must cover all of
those invariants plus authorization and auditability. **Data integrity:** an
object retained by policy is not proof that restoring it is currently safe.

## Incident Closeout

Record environment, release commit, UTC interval, safe route/command,
aggregate affected counts, recovery action, and verification evidence. Remove
temporary databases, profiles, PDFs, page images, text dumps, logs, and test
objects. Confirm no secrets or document content entered tickets, chat, logs,
or source control.
