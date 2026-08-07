# AI Preconstruction Follow-Up Actions

## Purpose

M18.5 closes the loop on an accepted M18.4 finding. A reviewer who accepts
*"Requirement X may not be covered by Subcontract Y"* can now record that they
decided to act, keep the evidence trail, and point at the record that answers
it — without retyping anything and without losing the connection.

It creates **no** RFI, Change Order, Submittal, Task, relationship, procurement
record, cost estimate, or notification. It approves nothing. It calls no AI
provider and adds no analysis type.

The authoritative flow is:

```text
accepted advisory Finding (M18.4)
  -> human raises a FindingFollowUp (status = planned) + deterministic draft
  -> human creates the record in that record's OWN existing workflow
  -> human links it back (status = linked)
  -> human closes it (completed | cancelled)
```

## Terminology

A **follow-up** is an *intent plus a link*. It is not a task, an assignment, an
approval, an obligation, or a second review decision. Accepting the finding was
the decision; the follow-up records only what a person chose to do next.

## What M18.5 deliberately is not

- **Not a workflow engine.** No assignees, due dates, reminders, escalation,
  priorities, or per-trade status.
- **Not a second review system.** The finding's append-only
  `PreconstructionFindingReview` history remains the sole authority on whether
  a finding is valid. A follow-up carries a lifecycle, never a judgement, and
  has no decision or reason-code vocabulary of its own.
- **Not a second creation path.** Preconstruction never writes to `rfis`,
  `change_orders`, `submittals`, or `entity_relationships`. Each record type
  keeps exactly one creation workflow: its own.
- **Not automatic.** Every transition is an explicit human action. There is no
  bulk raise, no "apply all", and no confidence or severity threshold that
  raises work on its own.

## Why preconstruction does not create the record

Calling the RFI service from the follow-up service would have been more
convenient and was rejected. It would introduce a second RFI-creation path,
invert the dependency direction — nothing currently depends on preconstruction,
and preconstruction depends only on documents and drawings — and make an
advisory subsystem a writer to authoritative workflow tables. Keeping creation
where it already lives is what makes *"no automatic RFI creation"* literally
true rather than argued.

## Eligibility

A follow-up may be raised only from a finding whose current status is
**`accepted`**.

`intentional_exclusion` is refused on purpose: that status is the recorded
human decision *not* to act, so raising work from it would contradict a
judgement a person already made. `proposed`, `needs_review`, `rejected`, and
`superseded` are refused as unreviewed or settled-against. Archived comparison
plans and archived review sets are read-only.

## Action types

Six controlled actions are defined in
`backend/app/preconstruction/follow_up.py`. Three carry a linkable record type;
three are tracked to completion with a closing note.

| Action | Links to |
|---|---|
| `rfi` | `rfi` |
| `change_order` | `change_order` |
| `submittal` | `submittal` |
| `procurement_action` | — |
| `subcontract_clarification` | — |
| `internal_follow_up` | — |

Linkable target types are validated at import against `ENTITY_TYPES` from the
existing relationship rules, so there is no second registry of what a follow-up
may reference.

## Lifecycle

```text
planned ──> linked ──> completed
   │           │
   └──────────┴──> cancelled
```

`completed` and `cancelled` are terminal and are never reopened. Cancelling
always requires a note, because it discards planned work. A link is written
once: a linked follow-up cannot be relinked or repointed.

## The pinned acceptance

Every follow-up stores `finding_review_id` — the exact acceptance review that
authorized it. This is the M18.4 `assertion_review_id` pattern applied one
level up, and it is what makes *"the finding was accepted when this work was
raised"* provable after a reviewer later reverses the decision.

If a finding moves back to `needs_review`, existing follow-ups are **never
deleted, rewritten, or reinterpreted**. The response derives a
`finding_no_longer_accepted` flag from the finding's current status, the UI
surfaces it, and new follow-ups are refused. The stored row is untouched —
the same principle as *"a review change produces a new manifest instead of
rewriting history."*

## Deterministic drafts

The draft is assembled server-side from stored finding data only: finding
title, type label, severity label, comparison type label, the linked
requirement and coverage assertion subjects, and evidence citations by
reference (source display name, page, segment). Same finding in, same draft
out.

Evidence is **cited, never copied**: the draft references page and segment
identity and does not duplicate excerpt text into a second store.

The draft is a starting point. The human edits it in the dialog and again in
the workflow form before anything is sent. It is plain text with no Markdown,
no HTML, and no links, and it is bounded by configuration.

When a finding came from provider validation, its summary may appear in the
draft. That text is treated exactly like an evidence excerpt: sanitized,
length-bounded, and rendered inertly.

## Controlled language

A draft heads toward a contractual document, so the vocabulary stays
descriptive. Templates say *potential*, *please confirm*, and *for review*.
Import-time validation rejects the module if breach, liability, entitlement,
damages, negligence, default, termination, or warranty-claim vocabulary appears
in any action value, label, description, guidance, status, template, or the
advisory notice. Tests assert the same over generated drafts.

Every generated draft ends with the advisory notice stating that the finding is
advisory, that a reviewer accepted it for follow-up, and that the wording must
be confirmed before sending.

## API

```text
GET  /findings/{finding_id}/follow-ups      list + available actions + drafts
POST /findings/{finding_id}/follow-ups      raise one planned follow-up
GET  /comparison-plans/{id}/follow-ups      bounded, filtered plan roll-up
PUT  /follow-ups/{id}                       edit the draft while planned
POST /follow-ups/{id}/link                  attach an existing owned record
POST /follow-ups/{id}/close                 completed | cancelled + note
```

Every route resolves ownership through `get_owned_project` before any nested
identifier, in the established order: finding → plan → review set. Filters
(`action_type`, `follow_up_status`, `target_type`, `finding_id`) are
allowlisted; an unknown value returns 422 rather than being ignored.

Ordering is status priority (planned, linked, completed, cancelled), then
action type, then id.

## Target resolution

A link is resolved through the existing
`resolve_relationship_entity(..., require_selectable=True)`, the same code that
guards the relationship graph. Ownership, existence, and selectability are
enforced there, so a foreign, missing, or unavailable record can never be
linked. A record in another project returns 404 rather than leaking its
existence.

`target_type` must match the action's declared type: an RFI follow-up cannot be
pointed at a Change Order. Actions with no record type refuse linking outright.

The reference is intentionally untyped — no foreign key — so a follow-up never
restricts or cascades into an authoritative workflow table. Deleting the linked
RFI leaves the follow-up history intact.

## Query budget

One follow-up page costs a fixed number of queries regardless of page size: the
listing, a count, one batched finding query, one grouped target resolution, and
the summary aggregate. There is no per-row query.

## Frontend

The existing lazy `#/projects/{id}/preconstruction` route gains a follow-up
panel inside the finding detail disclosure it already had. There is no new
route, no new navigation entry, and no separate "actions" page.

Raising, linking, and closing each use their own dialog alongside the three
M18.4 dialogs. Status, action type, and target are always rendered as text;
colour is never the only signal. Draft text renders with preserved wrapping and
no Markdown or HTML interpretation.

The dialog offers a plain navigation button to the record's own workflow page.
It carries **no draft text in the route**: the hash router serializes
identifiers only, and draft wording does not belong in a URL. The human saves
the draft, opens the workflow, and copies the wording in.

## Security

- Ownership is enforced before any follow-up, finding, plan, or review-set
  identifier is resolved; a two-user matrix covers all six routes.
- Mutation schemas forbid unknown fields and reject client-supplied project
  identity, finding identity, lifecycle status, the pinned acceptance review,
  target identity at creation, draft template version, actor identity, and all
  lifecycle timestamps. The server computes every one of them.
- A partial unique index on `(finding_id, action_type)` where status is
  `planned` or `linked` means a double submission can never produce two RFIs
  for the same finding.
- Per-finding and per-plan limits bound volume.
- Logs may carry follow-up, finding, plan, and target identifiers, action type,
  status, and counts. They must never carry draft titles or bodies, closure
  notes, evidence excerpts, assertion text, or reviewer notes.

## Migration

Alembic revision `e2b8d4f7c103` follows `d5a3f9c14e28`. It creates one table
with its constraints and indexes. It performs **no backfill**, alters **no
existing table**, and widens **no existing allowlist** — M18.5 adds no analysis
type, so unlike M18.3 and M18.4 it needs no CHECK widening anywhere.

No existing accepted finding gains a follow-up automatically. Project deletion
cascades follow-ups with the rest of the advisory graph; the M18.3 and M18.4
`RESTRICT` protections on cited assertions and evidence are unchanged.

## Verification

Automated release evidence is 522 backend tests with 723 separately reported
backend subtests, and 646 frontend tests across 93 files: 1,168 primary tests.
Follow-up-specific coverage is 25 backend tests plus 122 subtests across
`test_preconstruction_follow_up.py` and `test_finding_follow_up_migration.py`,
and 14 frontend tests in `FollowUpWorkflow.test.jsx` plus extended API-client
and hook coverage. ESLint and the production build pass. No dependency or
lockfile change is part of M18.5.

A snapshot test captures 18 authoritative tables — including
`entity_relationships`, `rfis`, `change_orders`, `submittals`, `tasks`, and the
whole M18.2–M18.4 immutable chain — before and after a complete follow-up
lifecycle and asserts byte-equality. A route-inventory test asserts there are
exactly six follow-up routes, all project-scoped, and that no promote,
auto-create, or bulk endpoint exists.

## Deferred

Automatic RFI, Change Order, procurement, relationship, or notification
creation; contract or purchase-order approval; autonomous acceptance; assignees
and due dates; subcontractor notification; external portals; cross-project
follow-ups; and live provider adapters are all out of scope for M18.5 and
require later separately reviewed milestones.
