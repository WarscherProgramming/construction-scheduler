import json
from time import perf_counter

from sqlalchemy import event

from app.api.dependencies import get_preconstruction_follow_up_config
from app.core.config import PreconstructionFollowUpConfig
from app.main import app
from app.models.scope_follow_up import PreconstructionFindingFollowUp
from app.preconstruction import follow_up as F
from app.services.relationship_rules import ENTITY_TYPES
from tests.test_preconstruction_comparison import ComparisonTestBase


def follow_up_config(**overrides):
    values = {
        "max_follow_ups_per_finding": 6,
        "max_follow_ups_per_plan": 500,
        "max_draft_title_characters": 200,
        "max_draft_body_characters": 4_000,
        "max_closure_note_characters": 2_000,
        "follow_up_page_size": 25,
        "follow_up_max_page_size": 100,
        "schema_version": "scope-follow-up-1",
        "template_version": "scope-follow-up-draft-1",
    }
    values.update(overrides)
    return PreconstructionFollowUpConfig(**values)


class FollowUpTestBase(ComparisonTestBase):
    """Runs a real comparison, accepts a finding, then raises follow-ups."""

    def setUp(self):
        super().setUp()
        self.follow_up_config = follow_up_config()
        app.dependency_overrides[get_preconstruction_follow_up_config] = (
            lambda: self.follow_up_config
        )
        self._rfi_sequence = 0

    def accepted_finding(self):
        review, _specification, _proposal, _assertions = self.reviewed_review_set()
        plan = self.create_plan(review["id"])
        self.run_comparison(plan["id"])
        finding = self.first_finding(plan["id"])
        response = self.client.post(
            f"{self.base()}/findings/{finding['id']}/reviews",
            json={"decision": "accepted", "reason_code": "confirmed_gap"},
            headers=self.owner_headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return plan, response.json()["finding"]

    def create_rfi(self, headers=None, project_id=None):
        headers = headers or self.owner_headers
        project_id = project_id or self.project_id
        self._rfi_sequence += 1
        response = self.client.post(
            f"/projects/{project_id}/rfis",
            json={
                "subject": f"Lighting scope {self._rfi_sequence}",
                "question": "Please confirm the intended scope.",
                "submitted_date": "2026-08-06",
            },
            headers=headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def raise_follow_up(self, finding_id, action_type="rfi", **payload):
        body = {"action_type": action_type}
        body.update(payload)
        response = self.client.post(
            f"{self.base()}/findings/{finding_id}/follow-ups",
            json=body,
            headers=self.owner_headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["follow_up"]


class FollowUpVocabularyTests(FollowUpTestBase):
    def test_controlled_vocabulary_is_complete_and_validated(self):
        self.assertEqual(len(F.FOLLOW_UP_ACTIONS), 6)
        self.assertEqual(len(F.FOLLOW_UP_STATUSES), 4)
        self.assertEqual(F.FOLLOW_UP_ELIGIBLE_FINDING_STATUSES, ("accepted",))
        # Every linkable action points at a real relationship entity type, so
        # there is no second registry of what a follow-up may reference.
        for action in F.FOLLOW_UP_ACTIONS:
            with self.subTest(action=action.value):
                self.assertIn(action.value, F.DRAFT_OPENINGS)
                self.assertIn(action.value, F.DRAFT_CLOSINGS)
                if action.target_type is not None:
                    self.assertIn(action.target_type, ENTITY_TYPES)
        # Every status has a documented transition set and terminal states are
        # genuinely terminal.
        self.assertEqual(
            set(F.ALLOWED_FOLLOW_UP_TRANSITIONS), set(F.FOLLOW_UP_STATUSES)
        )
        self.assertEqual(F.ALLOWED_FOLLOW_UP_TRANSITIONS["completed"], ())
        self.assertEqual(F.ALLOWED_FOLLOW_UP_TRANSITIONS["cancelled"], ())

    def test_vocabulary_expresses_no_legal_conclusion(self):
        vocabulary = json.dumps(
            [
                list(F.FOLLOW_UP_ACTION_VALUES),
                [item.label for item in F.FOLLOW_UP_ACTIONS],
                [item.description for item in F.FOLLOW_UP_ACTIONS],
                [item.guidance for item in F.FOLLOW_UP_ACTIONS],
                list(F.FOLLOW_UP_STATUSES.values()),
                list(F.DRAFT_OPENINGS.values()),
                list(F.DRAFT_CLOSINGS.values()),
                F.ADVISORY_NOTICE,
            ]
        ).lower()
        for forbidden in F.FORBIDDEN_DRAFT_TERMS:
            with self.subTest(term=forbidden):
                self.assertNotIn(forbidden, vocabulary)

    def test_transition_and_note_rules(self):
        self.assertTrue(F.follow_up_transition_allowed("planned", "linked"))
        self.assertTrue(F.follow_up_transition_allowed("planned", "cancelled"))
        self.assertTrue(F.follow_up_transition_allowed("linked", "completed"))
        self.assertFalse(F.follow_up_transition_allowed("linked", "planned"))
        self.assertFalse(F.follow_up_transition_allowed("completed", "linked"))
        self.assertFalse(F.follow_up_transition_allowed("cancelled", "planned"))
        self.assertTrue(F.closure_note_required("cancelled"))
        self.assertFalse(F.closure_note_required("completed"))
        self.assertTrue(F.target_required("rfi"))
        self.assertFalse(F.target_required("internal_follow_up"))


class FollowUpDraftTests(FollowUpTestBase):
    def test_draft_is_deterministic_evidence_backed_and_advisory(self):
        plan, finding = self.accepted_finding()
        first = self.client.get(
            f"{self.base()}/findings/{finding['id']}/follow-ups",
            headers=self.owner_headers,
        )
        self.assertEqual(first.status_code, 200, first.text)
        payload = first.json()
        self.assertTrue(payload["eligible"])
        self.assertEqual(len(payload["actions"]), 6)
        self.assertEqual(len(payload["available_actions"]), 6)
        self.assertEqual(payload["items"], [])

        drafts = {item["action_type"]: item for item in payload["drafts"]}
        rfi_draft = drafts["rfi"]
        self.assertEqual(rfi_draft["target_type"], "rfi")
        self.assertEqual(
            rfi_draft["draft_template_version"], "scope-follow-up-draft-1"
        )
        self.assertIn(finding["title"], rfi_draft["draft_title"])
        body = rfi_draft["draft_body"]
        # Evidence citations are carried through by reference, never re-derived
        # into a second copy of the excerpt text.
        self.assertIn("Source references:", body)
        self.assertIn("page 1", body)
        self.assertIn(F.ADVISORY_NOTICE, body)
        for forbidden in F.FORBIDDEN_DRAFT_TERMS:
            with self.subTest(term=forbidden):
                self.assertNotIn(forbidden, body.lower())
        # No Markdown or HTML is ever generated.
        for markup in ("<", "**", "](", "```"):
            with self.subTest(markup=markup):
                self.assertNotIn(markup, body)

        # Same finding in, same draft out.
        second = self.client.get(
            f"{self.base()}/findings/{finding['id']}/follow-ups",
            headers=self.owner_headers,
        ).json()
        self.assertEqual(payload["drafts"], second["drafts"])

    def test_draft_offers_only_actions_that_are_not_already_open(self):
        plan, finding = self.accepted_finding()
        self.raise_follow_up(finding["id"], "rfi")
        listing = self.client.get(
            f"{self.base()}/findings/{finding['id']}/follow-ups",
            headers=self.owner_headers,
        ).json()
        offered = {item["value"] for item in listing["available_actions"]}
        self.assertNotIn("rfi", offered)
        self.assertIn("change_order", offered)
        self.assertEqual({item["action_type"] for item in listing["drafts"]}, offered)


class FollowUpEligibilityTests(FollowUpTestBase):
    def test_only_an_accepted_finding_can_raise_a_follow_up(self):
        review, _spec, _proposal, _assertions = self.reviewed_review_set()
        plan = self.create_plan(review["id"])
        self.run_comparison(plan["id"])
        finding = self.first_finding(plan["id"])

        # Proposed is refused.
        proposed = self.client.post(
            f"{self.base()}/findings/{finding['id']}/follow-ups",
            json={"action_type": "rfi"},
            headers=self.owner_headers,
        )
        self.assertEqual(proposed.status_code, 409, proposed.text)

        for decision, note in (
            ("needs_review", None),
            ("rejected", "Not a real gap"),
            ("intentional_exclusion", "Deliberately excluded"),
        ):
            with self.subTest(decision=decision):
                body = {"decision": decision}
                if note:
                    body["reviewer_note"] = note
                moved = self.client.post(
                    f"{self.base()}/findings/{finding['id']}/reviews",
                    json=body,
                    headers=self.owner_headers,
                )
                self.assertEqual(moved.status_code, 201, moved.text)
                refused = self.client.post(
                    f"{self.base()}/findings/{finding['id']}/follow-ups",
                    json={"action_type": "rfi"},
                    headers=self.owner_headers,
                )
                self.assertEqual(refused.status_code, 409, refused.text)
                listing = self.client.get(
                    f"{self.base()}/findings/{finding['id']}/follow-ups",
                    headers=self.owner_headers,
                ).json()
                self.assertFalse(listing["eligible"])
                self.assertEqual(listing["available_actions"], [])
                self.assertEqual(listing["drafts"], [])
                # Settled states must be reversed through review before the
                # next decision, exactly as M18.4 requires.
                self.client.post(
                    f"{self.base()}/findings/{finding['id']}/reviews",
                    json={
                        "decision": "needs_review",
                        "reviewer_note": "Reopening for the next case",
                    },
                    headers=self.owner_headers,
                )

        accepted = self.client.post(
            f"{self.base()}/findings/{finding['id']}/reviews",
            json={"decision": "accepted"},
            headers=self.owner_headers,
        )
        self.assertEqual(accepted.status_code, 201, accepted.text)
        self.raise_follow_up(finding["id"], "rfi")

    def test_review_reversal_preserves_history_and_blocks_new_work(self):
        plan, finding = self.accepted_finding()
        follow_up = self.raise_follow_up(finding["id"], "rfi")
        pinned_review_id = follow_up["finding_review_id"]
        self.assertIsNotNone(pinned_review_id)

        reversed_review = self.client.post(
            f"{self.base()}/findings/{finding['id']}/reviews",
            json={
                "decision": "needs_review",
                "reviewer_note": "Reopening after a site walk",
            },
            headers=self.owner_headers,
        )
        self.assertEqual(reversed_review.status_code, 201, reversed_review.text)

        listing = self.client.get(
            f"{self.base()}/findings/{finding['id']}/follow-ups",
            headers=self.owner_headers,
        ).json()
        self.assertFalse(listing["eligible"])
        self.assertEqual(len(listing["items"]), 1)
        preserved = listing["items"][0]
        # The follow-up itself is never rewritten; the reversal is surfaced.
        self.assertEqual(preserved["id"], follow_up["id"])
        self.assertEqual(preserved["status"], "planned")
        self.assertEqual(preserved["finding_review_id"], pinned_review_id)
        self.assertTrue(preserved["finding_no_longer_accepted"])
        self.assertEqual(preserved["finding_status"], "needs_review")

        blocked = self.client.post(
            f"{self.base()}/findings/{finding['id']}/follow-ups",
            json={"action_type": "change_order"},
            headers=self.owner_headers,
        )
        self.assertEqual(blocked.status_code, 409, blocked.text)

        # Existing work can still be closed out honestly.
        closed = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/close",
            json={"status": "cancelled", "closure_note": "Finding reopened"},
            headers=self.owner_headers,
        )
        self.assertEqual(closed.status_code, 201, closed.text)


class FollowUpLifecycleTests(FollowUpTestBase):
    def test_plan_link_and_complete_records_a_human_created_record(self):
        plan, finding = self.accepted_finding()
        follow_up = self.raise_follow_up(finding["id"], "rfi")
        self.assertEqual(follow_up["status"], "planned")
        self.assertIsNone(follow_up["target_type"])
        self.assertTrue(follow_up["can_edit_draft"])
        self.assertTrue(follow_up["can_link"])

        rfi = self.create_rfi()
        linked = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/link",
            json={"target_type": "rfi", "target_id": rfi["id"]},
            headers=self.owner_headers,
        )
        self.assertEqual(linked.status_code, 201, linked.text)
        body = linked.json()["follow_up"]
        self.assertEqual(body["status"], "linked")
        self.assertEqual(body["target_type"], "rfi")
        self.assertEqual(body["target_id"], rfi["id"])
        self.assertEqual(body["target"]["identifier"], rfi["number"])
        self.assertEqual(body["linked_by"], self.owner_id)
        self.assertFalse(body["can_edit_draft"])
        self.assertFalse(body["can_link"])

        completed = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/close",
            json={"status": "completed", "closure_note": "RFI answered"},
            headers=self.owner_headers,
        )
        self.assertEqual(completed.status_code, 201, completed.text)
        closed = completed.json()["follow_up"]
        self.assertEqual(closed["status"], "completed")
        self.assertEqual(closed["closed_by"], self.owner_id)
        self.assertFalse(closed["can_close"])

        # Terminal states are never reopened.
        reopened = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/close",
            json={"status": "cancelled", "closure_note": "Changed my mind"},
            headers=self.owner_headers,
        )
        self.assertEqual(reopened.status_code, 409, reopened.text)
        relinked = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/link",
            json={"target_type": "rfi", "target_id": rfi["id"]},
            headers=self.owner_headers,
        )
        self.assertEqual(relinked.status_code, 409, relinked.text)

    def test_cancelling_requires_a_note_and_frees_the_action(self):
        plan, finding = self.accepted_finding()
        follow_up = self.raise_follow_up(finding["id"], "rfi")

        missing_note = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/close",
            json={"status": "cancelled"},
            headers=self.owner_headers,
        )
        self.assertEqual(missing_note.status_code, 422, missing_note.text)

        duplicate = self.client.post(
            f"{self.base()}/findings/{finding['id']}/follow-ups",
            json={"action_type": "rfi"},
            headers=self.owner_headers,
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.text)

        cancelled = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/close",
            json={"status": "cancelled", "closure_note": "Handled verbally"},
            headers=self.owner_headers,
        )
        self.assertEqual(cancelled.status_code, 201, cancelled.text)
        # A cancelled round frees the action for genuinely new work.
        self.raise_follow_up(finding["id"], "rfi")

    def test_draft_editing_is_bounded_and_stops_once_linked(self):
        plan, finding = self.accepted_finding()
        follow_up = self.raise_follow_up(finding["id"], "rfi")

        edited = self.client.put(
            f"{self.base()}/follow-ups/{follow_up['id']}",
            json={
                "draft_title": "Lighting fixture coverage",
                "draft_body": "First line.\n\n\n\nSecond line.   \n",
            },
            headers=self.owner_headers,
        )
        self.assertEqual(edited.status_code, 200, edited.text)
        body = edited.json()["follow_up"]
        self.assertEqual(body["draft_title"], "Lighting fixture coverage")
        # Line structure survives; runaway blank lines and trailing spaces do not.
        self.assertEqual(body["draft_body"], "First line.\n\nSecond line.")

        blank = self.client.put(
            f"{self.base()}/follow-ups/{follow_up['id']}",
            json={"draft_body": "   \n   "},
            headers=self.owner_headers,
        )
        self.assertEqual(blank.status_code, 422, blank.text)

        rfi = self.create_rfi()
        self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/link",
            json={"target_type": "rfi", "target_id": rfi["id"]},
            headers=self.owner_headers,
        )
        frozen = self.client.put(
            f"{self.base()}/follow-ups/{follow_up['id']}",
            json={"draft_title": "Too late"},
            headers=self.owner_headers,
        )
        self.assertEqual(frozen.status_code, 409, frozen.text)

    def test_archived_plans_and_review_sets_are_read_only(self):
        plan, finding = self.accepted_finding()
        follow_up = self.raise_follow_up(finding["id"], "rfi")
        archived = self.client.post(
            f"{self.base()}/comparison-plans/{plan['id']}/archive",
            headers=self.owner_headers,
        )
        self.assertEqual(archived.status_code, 200, archived.text)

        for method, path, body in (
            ("post", f"/findings/{finding['id']}/follow-ups", {"action_type": "submittal"}),
            ("put", f"/follow-ups/{follow_up['id']}", {"draft_title": "Nope"}),
            (
                "post",
                f"/follow-ups/{follow_up['id']}/close",
                {"status": "completed"},
            ),
        ):
            with self.subTest(path=path):
                response = getattr(self.client, method)(
                    f"{self.base()}{path}", json=body, headers=self.owner_headers
                )
                self.assertEqual(response.status_code, 409, response.text)


class FollowUpTargetTests(FollowUpTestBase):
    def test_target_must_be_an_owned_record_of_the_declared_type(self):
        plan, finding = self.accepted_finding()
        follow_up = self.raise_follow_up(finding["id"], "rfi")
        foreign_rfi = self.create_rfi(
            headers=self.other_headers, project_id=self.foreign_project_id
        )

        # A record belonging to another project is not resolvable here.
        foreign = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/link",
            json={"target_type": "rfi", "target_id": foreign_rfi["id"]},
            headers=self.owner_headers,
        )
        self.assertEqual(foreign.status_code, 404, foreign.text)

        missing = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/link",
            json={"target_type": "rfi", "target_id": 999_999},
            headers=self.owner_headers,
        )
        self.assertEqual(missing.status_code, 404, missing.text)

        # An RFI follow-up cannot be pointed at a Change Order.
        rfi = self.create_rfi()
        wrong_type = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/link",
            json={"target_type": "change_order", "target_id": rfi["id"]},
            headers=self.owner_headers,
        )
        self.assertEqual(wrong_type.status_code, 422, wrong_type.text)

        # An unknown entity type never reaches the resolver.
        unknown = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/link",
            json={"target_type": "daily_log", "target_id": 1},
            headers=self.owner_headers,
        )
        self.assertEqual(unknown.status_code, 422, unknown.text)

    def test_actions_without_a_record_type_cannot_be_linked(self):
        plan, finding = self.accepted_finding()
        follow_up = self.raise_follow_up(finding["id"], "internal_follow_up")
        self.assertFalse(follow_up["can_link"])
        refused = self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/link",
            json={"target_type": "rfi", "target_id": 1},
            headers=self.owner_headers,
        )
        self.assertEqual(refused.status_code, 422, refused.text)


class FollowUpAuthorityTests(FollowUpTestBase):
    AUTHORITATIVE_TABLES = (
        "documents",
        "document_page_texts",
        "document_extractions",
        "drawing_revisions",
        "entity_relationships",
        "rfis",
        "change_orders",
        "submittals",
        "tasks",
        "preconstruction_content_snapshots",
        "preconstruction_content_segments",
        "preconstruction_scope_assertions",
        "preconstruction_assertion_evidence",
        "preconstruction_assertion_reviews",
        "preconstruction_finding_sets",
        "preconstruction_findings",
        "preconstruction_finding_assertions",
        "preconstruction_finding_evidence",
    )

    def snapshot(self):
        from sqlalchemy import text as sql_text

        with self.TestingSession() as db:
            return {
                table: db.execute(
                    sql_text(f"SELECT * FROM {table} ORDER BY id")
                ).fetchall()
                for table in self.AUTHORITATIVE_TABLES
            }

    def test_the_whole_follow_up_lifecycle_mutates_no_authoritative_system(self):
        plan, finding = self.accepted_finding()
        rfi = self.create_rfi()
        before = self.snapshot()

        follow_up = self.raise_follow_up(finding["id"], "rfi")
        self.client.put(
            f"{self.base()}/follow-ups/{follow_up['id']}",
            json={"draft_title": "Edited draft"},
            headers=self.owner_headers,
        )
        self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/link",
            json={"target_type": "rfi", "target_id": rfi["id"]},
            headers=self.owner_headers,
        )
        self.client.post(
            f"{self.base()}/follow-ups/{follow_up['id']}/close",
            json={"status": "completed", "closure_note": "Answered"},
            headers=self.owner_headers,
        )

        after = self.snapshot()
        for table in self.AUTHORITATIVE_TABLES:
            with self.subTest(table=table):
                self.assertEqual(before[table], after[table])

        # Specifically: linking creates no relationship row of its own.
        self.assertEqual(len(after["entity_relationships"]), 0)

    def test_no_route_creates_an_authoritative_record(self):
        follow_up_routes = [
            route
            for route in app.routes
            if "follow-up" in getattr(route, "path", "")
        ]
        self.assertEqual(len(follow_up_routes), 6)
        for route in follow_up_routes:
            with self.subTest(path=route.path):
                self.assertTrue(route.path.startswith("/projects/{project_id}/"))
        # There is no bulk, auto-create, or promote endpoint anywhere.
        paths = [getattr(route, "path", "") for route in app.routes]
        for forbidden in ("/promote", "/auto-create", "/follow-ups/bulk"):
            with self.subTest(path=forbidden):
                self.assertFalse(any(forbidden in path for path in paths))

    def test_server_controlled_fields_are_rejected(self):
        plan, finding = self.accepted_finding()
        for field, value in (
            ("status", "linked"),
            ("project_id", 999),
            ("finding_id", 999),
            ("finding_review_id", 1),
            ("target_type", "rfi"),
            ("target_id", 1),
            ("created_by", 999),
            ("draft_template_version", "forged"),
            ("closure_note", "forged"),
        ):
            with self.subTest(field=field):
                response = self.client.post(
                    f"{self.base()}/findings/{finding['id']}/follow-ups",
                    json={"action_type": "rfi", field: value},
                    headers=self.owner_headers,
                )
                self.assertEqual(response.status_code, 422, response.text)

    def test_two_user_matrix_denies_foreign_follow_up_records(self):
        plan, finding = self.accepted_finding()
        follow_up = self.raise_follow_up(finding["id"], "rfi")
        foreign_base = f"/projects/{self.foreign_project_id}/preconstruction"

        cases = (
            ("get", f"{self.base()}/findings/{finding['id']}/follow-ups", None, 403),
            (
                "post",
                f"{self.base()}/findings/{finding['id']}/follow-ups",
                {"action_type": "submittal"},
                403,
            ),
            (
                "get",
                f"{self.base()}/comparison-plans/{plan['id']}/follow-ups",
                None,
                403,
            ),
            ("put", f"{self.base()}/follow-ups/{follow_up['id']}", {"draft_title": "X"}, 403),
            (
                "post",
                f"{self.base()}/follow-ups/{follow_up['id']}/link",
                {"target_type": "rfi", "target_id": 1},
                403,
            ),
            (
                "post",
                f"{self.base()}/follow-ups/{follow_up['id']}/close",
                {"status": "completed"},
                403,
            ),
        )
        for method, path, body, expected in cases:
            with self.subTest(path=path):
                if body is None:
                    response = getattr(self.client, method)(
                        path, headers=self.other_headers
                    )
                else:
                    response = getattr(self.client, method)(
                        path, json=body, headers=self.other_headers
                    )
                self.assertEqual(response.status_code, expected, response.text)

        # Reaching the row through the other user's own project 404s instead of
        # leaking its existence.
        crossed = self.client.put(
            f"{foreign_base}/follow-ups/{follow_up['id']}",
            json={"draft_title": "X"},
            headers=self.other_headers,
        )
        self.assertEqual(crossed.status_code, 404, crossed.text)

        # Unauthenticated access is refused outright.
        anonymous = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/follow-ups"
        )
        self.assertEqual(anonymous.status_code, 401, anonymous.text)


class FollowUpListingTests(FollowUpTestBase):
    def test_filters_ordering_and_pagination_are_bounded(self):
        plan, finding = self.accepted_finding()
        rfi_follow_up = self.raise_follow_up(finding["id"], "rfi")
        self.raise_follow_up(finding["id"], "change_order")
        internal = self.raise_follow_up(finding["id"], "internal_follow_up")

        rfi = self.create_rfi()
        self.client.post(
            f"{self.base()}/follow-ups/{rfi_follow_up['id']}/link",
            json={"target_type": "rfi", "target_id": rfi["id"]},
            headers=self.owner_headers,
        )
        self.client.post(
            f"{self.base()}/follow-ups/{internal['id']}/close",
            json={"status": "completed", "closure_note": "Coordinated"},
            headers=self.owner_headers,
        )

        listing = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/follow-ups",
            headers=self.owner_headers,
        )
        self.assertEqual(listing.status_code, 200, listing.text)
        payload = listing.json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(payload["limit"], 25)
        self.assertEqual(payload["summary"]["planned"], 1)
        self.assertEqual(payload["summary"]["linked"], 1)
        self.assertEqual(payload["summary"]["completed"], 1)
        self.assertEqual(payload["summary"]["cancelled"], 0)
        self.assertEqual(payload["summary"]["total"], 3)
        # Deterministic priority: planned, then linked, then completed.
        self.assertEqual(
            [item["status"] for item in payload["items"]],
            ["planned", "linked", "completed"],
        )

        filtered = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/follow-ups"
            "?follow_up_status=linked",
            headers=self.owner_headers,
        ).json()
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(filtered["items"][0]["action_type"], "rfi")

        by_action = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/follow-ups"
            "?action_type=change_order",
            headers=self.owner_headers,
        ).json()
        self.assertEqual(by_action["total"], 1)

        by_target = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/follow-ups?target_type=rfi",
            headers=self.owner_headers,
        ).json()
        self.assertEqual(by_target["total"], 1)

        paged = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/follow-ups?limit=1&offset=1",
            headers=self.owner_headers,
        ).json()
        self.assertEqual(len(paged["items"]), 1)
        self.assertEqual(paged["total"], 3)

        for query in (
            "follow_up_status=invented",
            "action_type=invented",
            "target_type=daily_log",
            "limit=0",
            "limit=500",
        ):
            with self.subTest(query=query):
                rejected = self.client.get(
                    f"{self.base()}/comparison-plans/{plan['id']}/follow-ups?{query}",
                    headers=self.owner_headers,
                )
                self.assertEqual(rejected.status_code, 422, rejected.text)

    def test_listing_query_count_is_bounded(self):
        plan, finding = self.accepted_finding()
        for action in ("rfi", "change_order", "submittal", "internal_follow_up"):
            follow_up = self.raise_follow_up(finding["id"], action)
            if action in ("rfi", "change_order"):
                continue
            self.client.post(
                f"{self.base()}/follow-ups/{follow_up['id']}/close",
                json={"status": "completed", "closure_note": "Done"},
                headers=self.owner_headers,
            )
        rfi = self.create_rfi()
        first = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/follow-ups",
            headers=self.owner_headers,
        ).json()
        rfi_row = next(
            item for item in first["items"] if item["action_type"] == "rfi"
        )
        self.client.post(
            f"{self.base()}/follow-ups/{rfi_row['id']}/link",
            json={"target_type": "rfi", "target_id": rfi["id"]},
            headers=self.owner_headers,
        )

        statements = []

        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", record)
        try:
            response = self.client.get(
                f"{self.base()}/comparison-plans/{plan['id']}/follow-ups",
                headers=self.owner_headers,
            )
        finally:
            event.remove(self.engine, "before_cursor_execute", record)
        self.assertEqual(response.status_code, 200, response.text)
        selects = [item for item in statements if item.strip().upper().startswith("SELECT")]
        # Auth, project, plan, count, page, findings, one grouped target
        # resolution, and the summary. There is no per-row query.
        self.assertLessEqual(len(selects), 12, selects)


class FollowUpLimitTests(FollowUpTestBase):
    def test_per_finding_limit_is_enforced(self):
        self.follow_up_config = follow_up_config(max_follow_ups_per_finding=2)
        app.dependency_overrides[get_preconstruction_follow_up_config] = (
            lambda: self.follow_up_config
        )
        plan, finding = self.accepted_finding()
        self.raise_follow_up(finding["id"], "rfi")
        self.raise_follow_up(finding["id"], "change_order")
        refused = self.client.post(
            f"{self.base()}/findings/{finding['id']}/follow-ups",
            json={"action_type": "submittal"},
            headers=self.owner_headers,
        )
        self.assertEqual(refused.status_code, 409, refused.text)

    def test_oversized_draft_text_is_rejected(self):
        plan, finding = self.accepted_finding()
        for field, value in (
            ("draft_title", "T" * 201),
            ("draft_body", "B" * 4_001),
        ):
            with self.subTest(field=field):
                response = self.client.post(
                    f"{self.base()}/findings/{finding['id']}/follow-ups",
                    json={"action_type": "rfi", field: value},
                    headers=self.owner_headers,
                )
                self.assertEqual(response.status_code, 422, response.text)

    def test_performance_stays_bounded_across_many_follow_ups(self):
        plan, finding = self.accepted_finding()
        listing = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/findings?limit=100",
            headers=self.owner_headers,
        ).json()
        created = 0
        for item in listing["items"]:
            if item["status"] != "accepted":
                self.client.post(
                    f"{self.base()}/findings/{item['id']}/reviews",
                    json={"decision": "accepted"},
                    headers=self.owner_headers,
                )
            for action in ("rfi", "change_order", "submittal"):
                response = self.client.post(
                    f"{self.base()}/findings/{item['id']}/follow-ups",
                    json={"action_type": action},
                    headers=self.owner_headers,
                )
                if response.status_code == 201:
                    created += 1
        self.assertGreaterEqual(created, 3)

        started = perf_counter()
        response = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/follow-ups",
            headers=self.owner_headers,
        )
        elapsed = perf_counter() - started
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertLessEqual(len(payload["items"]), 25)
        self.assertEqual(payload["total"], created)
        self.assertLess(elapsed, 5.0)
        self.assertLess(len(response.content), 400_000)

    def test_stored_rows_carry_no_provider_or_review_vocabulary(self):
        plan, finding = self.accepted_finding()
        self.raise_follow_up(finding["id"], "rfi")
        with self.TestingSession() as db:
            row = db.query(PreconstructionFindingFollowUp).one()
            columns = {column.name for column in row.__table__.columns}
        # A follow-up carries no second review decision and no provider field.
        for absent in (
            "decision",
            "reason_code",
            "reviewer_note",
            "confidence",
            "provider_profile",
            "provider_disposition",
            "severity",
        ):
            with self.subTest(column=absent):
                self.assertNotIn(absent, columns)
