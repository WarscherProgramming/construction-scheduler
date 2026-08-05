# Schedule Operations

This runbook covers M17 scheduling recovery. Preserve the canonical Task graph
and project ownership boundary; do not repair derived dates directly in SQL.

## Standard Response

For every incident: capture project ID, Data Date, baseline ID, endpoint,
status code, and correlation-safe logs; confirm the project owner; retry once
after the cause is understood; verify tasks, settings, and selected baseline;
then rerun the relevant read endpoint. Never log tokens, secrets, or report
contents.

## Recalculation Failure

- **Symptoms:** task mutation fails and dates do not change.
- **Likely cause:** invalid graph, constraint, or database transaction failure.
- **Action/recovery:** keep the failed transaction rolled back; correct the
  input through the API and retry. Do not patch derived dates.
- **Verify/integrity:** reload tasks and confirm all inputs and prior dates are
  intact, then check summary/leaf rollups.

## Dependency Cycle

- **Symptoms:** 422 response naming a cycle or self/cross-project dependency.
- **Likely cause:** the proposed normalized edge makes the graph invalid.
- **Action/recovery:** remove or correct that edge; retain existing edges.
- **Verify/integrity:** reload tasks and planning dialog; ensure no partial
  dependency write occurred.

## Baseline Capture or Variance Failure

- **Symptoms:** capture fails, variance is missing, or counts appear mismatched.
- **Likely cause:** invalid current schedule, duplicate name, missing/archived
  comparison, or stale selected baseline.
- **Action/recovery:** validate/recalculate current tasks, choose an active
  baseline, and retry. Never edit immutable snapshots.
- **Verify/integrity:** compare header task count with paginated detail and
  confirm the selected baseline ID and current Data Date.

## Data Date Correction

- **Symptoms:** incomplete work forecasts from the wrong reporting date.
- **Likely cause:** project Data Date was entered incorrectly.
- **Action/recovery:** update Data Date through Schedule settings; accept the
  recalculation confirmation and review affected progress.
- **Verify/integrity:** reload tasks, variance, look-ahead, resource loading,
  health, and reports. Actual dates and baseline snapshots must not change.

## Out-of-Sequence or Negative Float

- **Symptoms:** textual warning, negative float, or critical health category.
- **Likely cause:** actual progress precedes logic completion, mandatory dates,
  or forecast pressure.
- **Action/recovery:** review actual dates, remaining duration, dependency type
  and lag, and mandatory constraints. Escalate negative float to the project
  scheduler; do not clear it by editing derived fields.
- **Verify/integrity:** recalculate through a valid mutation and confirm the
  warning/reason remains factual or clears for an explainable input change.

## Mandatory Constraint Conflict

- **Symptoms:** critical health reason or task constraint violation.
- **Likely cause:** the network cannot satisfy a mandatory start/finish date.
- **Action/recovery:** verify the contract date, then correct logic/duration or
  formally revise the constraint through the task planning workflow.
- **Verify/integrity:** review forecast, float, baseline variance, and report.

## Look-Ahead Failure or Missing Task

- **Symptoms:** plan/detail retry state or “task no longer available.”
- **Likely cause:** request failure, archived plan, stale response, or a deleted
  live task with retained sparse metadata.
- **Action/recovery:** retry the selected plan; switch to an active plan for
  edits. Retained missing-task metadata is expected and must not be relinked.
- **Verify/integrity:** summary totals equal grouped items without duplicates;
  schedule dates remain live and unchanged by look-ahead edits.

## Resource Loading, Over-Allocation, or Unavailability

- **Symptoms:** retry state, over-allocation, unavailable conflict, or an
  unassigned task.
- **Likely cause:** invalid date/filter, assignment demand above capacity,
  capacity override, archived resource, or missing assignment.
- **Action/recovery:** narrow the bounded date/resource filters; review task
  dates, allocations, and availability. Reassign or change capacity only from
  verified operational information. No automatic leveling occurs.
- **Verify/integrity:** exact summary counts remain stable; truncated responses
  state the total and cap; task dates do not move.

## Executive Report Failure

- **Symptoms:** authenticated download fails or no PDF opens.
- **Likely cause:** session expiry, missing baseline request, ReportLab/temp
  directory failure, or browser popup policy.
- **Action/recovery:** reauthenticate if required, retry without an invalid
  baseline, verify writable temporary storage, and allow the user-initiated
  download. Do not expose a local path.
- **Verify/integrity:** filename is ASCII-safe, content is escaped/bounded, and
  no temporary PDF remains after success or failure.

## Migration Failure

- **Symptoms:** Alembic current differs from the single head or startup fails.
- **Likely cause:** interrupted deployment, wrong database URL, or schema drift.
- **Action/recovery:** stop writes, back up production, inspect current/heads,
  and run the documented upgrade in migration order. Do not edit old revisions.
- **Verify/integrity:** current equals `f7c5d0b3e826`, one head exists, Alembic
  check is clean, and scheduling smoke tests pass.

## Oversized Response or Browser Print Failure

- **Symptoms:** proxy timeout, slow transfer, browser memory pressure, clipped
  print, or more conflicts than serialized.
- **Likely cause:** broad date/resource range, 2,000-task look-ahead, unbounded
  browser DOM, or print settings.
- **Action/recovery:** narrow filters/range and use resource pagination; retain
  conflict truncation metadata. For print, use the dedicated mode, wait for
  load completion, and select landscape where needed.
- **Verify/integrity:** totals remain exact; no item is duplicated; print hides
  controls and does not alter server state.
