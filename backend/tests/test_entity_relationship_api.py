from datetime import datetime, timezone
import unittest

from sqlalchemy import event

from app.models.change_order import ChangeOrder
from app.models.daily_log import DailyLog
from app.models.document import Document
from app.models.drawing import (
    DrawingIssue,
    DrawingRevision,
    DrawingSet,
    DrawingSheet,
)
from app.models.entity_relationship import EntityRelationship
from app.models.punch_item import PunchItem
from app.models.rfi import RFI
from app.models.submittal import Submittal
from app.models.user import User
from tests.test_api import ApiTestCase


class EntityRelationshipApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.owner_headers = self.register_and_login("owner@example.com")
        self.intruder_headers = self.register_and_login(
            "intruder@example.com"
        )
        self.project_id = self.create_project(self.owner_headers, "Owned")
        self.second_project_id = self.create_project(
            self.owner_headers,
            "Second",
        )
        self.foreign_project_id = self.create_project(
            self.intruder_headers,
            "Private",
        )

        with self.TestingSession() as db:
            self.owner_id = (
                db.query(User)
                .filter(User.email == "owner@example.com")
                .one()
                .id
            )
            intruder_id = (
                db.query(User)
                .filter(User.email == "intruder@example.com")
                .one()
                .id
            )
            self.entities = self._create_entities(
                db,
                self.project_id,
                self.owner_id,
                "owned",
            )
            self.second_entities = self._create_entities(
                db,
                self.second_project_id,
                self.owner_id,
                "second",
            )
            self.foreign_entities = self._create_entities(
                db,
                self.foreign_project_id,
                intruder_id,
                "foreign",
            )
            db.commit()

    @staticmethod
    def _document(project_id, user_id, key, name):
        return Document(
            project_id=project_id,
            original_filename=f"{name}.pdf",
            display_name=name,
            extension=".pdf",
            mime_type="application/pdf",
            size_bytes=24,
            checksum_sha256=(key * 64)[:64],
            storage_provider="memory",
            storage_key=f"relationships/{key}.pdf",
            uploaded_by=user_id,
            document_type="General",
            status="Active",
        )

    def _create_entities(self, db, project_id, user_id, suffix):
        document = self._document(
            project_id,
            user_id,
            f"{suffix}-document",
            f"Coordination {suffix}",
        )
        revision_document = self._document(
            project_id,
            user_id,
            f"{suffix}-revision",
            f"A-101 {suffix}",
        )
        drawing_set = DrawingSet(
            project_id=project_id,
            name=f"IFC {suffix}",
            description="Issued construction set",
            status="active",
            issue_date="2026-08-01",
            created_by=user_id,
        )
        db.add_all([document, revision_document, drawing_set])
        db.flush()

        sheet = DrawingSheet(
            project_id=project_id,
            drawing_set_id=drawing_set.id,
            sheet_number=f"A-{project_id}01",
            normalized_sheet_number=f"A-{project_id}01",
            title=f"Floor Plan {suffix}",
            discipline="A",
            sort_key=f"A-{project_id}01",
            status="active",
            created_by=user_id,
        )
        db.add(sheet)
        db.flush()
        revision = DrawingRevision(
            project_id=project_id,
            drawing_sheet_id=sheet.id,
            document_id=revision_document.id,
            revision_code="1",
            normalized_revision_code="1",
            revision_date="2026-08-01",
            description="Coordination revision",
            sequence_number=1,
            is_current=True,
            uploaded_by=user_id,
        )
        issue = DrawingIssue(
            project_id=project_id,
            drawing_set_id=drawing_set.id,
            name=f"Permit issue {suffix}",
            issue_number=f"ISS-{project_id}",
            issue_date="2026-08-01",
            purpose="permit",
            status="draft",
            created_by=user_id,
        )
        rfi = RFI(
            project_id=project_id,
            number=f"RFI-{project_id:03d}",
            subject=f"Shelf lighting {suffix}",
            question="Please clarify the detail.",
            submitted_date="2026-08-01",
            status="Open",
        )
        submittal = Submittal(
            project_id=project_id,
            number=f"SUB-{project_id:03d}",
            specification_section="26 50 00",
            title=f"Lighting package {suffix}",
            status="Submitted",
        )
        punch_item = PunchItem(
            project_id=project_id,
            number=f"PUNCH-{project_id:03d}",
            location="Level 1",
            description=f"Repair lighting {suffix}",
            priority="High",
            status="Open",
        )
        change_order = ChangeOrder(
            project_id=project_id,
            date="2026-08-01",
            co_number=f"CO-{project_id:03d}",
            title=f"Lighting revision {suffix}",
            status="Pending",
        )
        daily_log = DailyLog(
            project_id=project_id,
            date="2026-08-01",
            company=f"Builder {suffix}",
            manpower=5,
            work_performed="Lighting coordination",
        )
        db.add_all(
            [
                revision,
                issue,
                rfi,
                submittal,
                punch_item,
                change_order,
                daily_log,
            ]
        )
        db.flush()
        sheet.current_revision_id = revision.id
        return {
            "document": document.id,
            "drawing_set": drawing_set.id,
            "drawing_sheet": sheet.id,
            "drawing_revision": revision.id,
            "drawing_issue": issue.id,
            "rfi": rfi.id,
            "submittal": submittal.id,
            "punch_item": punch_item.id,
            "change_order": change_order.id,
            "daily_log": daily_log.id,
        }

    def create_relationship(self, payload, *, headers=None, project_id=None):
        return self.client.post(
            f"/projects/{project_id or self.project_id}/relationships",
            json=payload,
            headers=headers or self.owner_headers,
        )

    def list_relationships(self, entity_type, entity_id, **params):
        return self.client.get(
            f"/projects/{self.project_id}/relationships",
            params={
                "entity_type": entity_type,
                "entity_id": entity_id,
                **params,
            },
            headers=self.owner_headers,
        )

    def test_routes_require_authentication_and_owned_project(self):
        payload = {
            "source_type": "rfi",
            "source_id": self.entities["rfi"],
            "target_type": "drawing_revision",
            "target_id": self.entities["drawing_revision"],
            "relationship_type": "references",
        }
        unauthenticated = (
            self.client.get(
                f"/projects/{self.project_id}/relationships",
                params={"entity_type": "rfi", "entity_id": 1},
            ),
            self.client.post(
                f"/projects/{self.project_id}/relationships",
                json=payload,
            ),
            self.client.get(
                f"/projects/{self.project_id}/relationship-candidates",
                params={"entity_type": "rfi"},
            ),
            self.client.delete(
                f"/projects/{self.project_id}/relationships/1"
            ),
        )
        self.assertTrue(
            all(response.status_code == 401 for response in unauthenticated)
        )

        for method, path, kwargs in (
            (
                "get",
                f"/projects/{self.project_id}/relationships",
                {"params": {"entity_type": "rfi", "entity_id": 1}},
            ),
            (
                "post",
                f"/projects/{self.project_id}/relationships",
                {"json": payload},
            ),
            (
                "get",
                f"/projects/{self.project_id}/relationship-candidates",
                {"params": {"entity_type": "rfi"}},
            ),
            (
                "delete",
                f"/projects/{self.project_id}/relationships/1",
                {},
            ),
        ):
            response = getattr(self.client, method)(
                path,
                headers=self.intruder_headers,
                **kwargs,
            )
            self.assertEqual(response.status_code, 403)

    def test_directional_create_and_perspective_listing(self):
        payload = {
            "source_type": "rfi",
            "source_id": self.entities["rfi"],
            "target_type": "drawing_revision",
            "target_id": self.entities["drawing_revision"],
            "relationship_type": "references",
        }
        created = self.create_relationship(payload)
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertEqual(body["direction"], "outgoing")
        self.assertEqual(body["relationship_label"], "References")
        self.assertEqual(body["related"]["type"], "drawing_revision")
        self.assertEqual(body["related"]["identifier"], "A-101 - Rev 1")
        self.assertEqual(body["related"]["route"]["page"], "drawingViewer")
        self.assertNotIn("storage_key", str(body))

        outgoing = self.list_relationships("rfi", self.entities["rfi"])
        self.assertEqual(outgoing.status_code, 200)
        self.assertEqual(outgoing.headers["cache-control"], "no-store")
        self.assertEqual(outgoing.json()["pagination"]["total"], 1)
        self.assertEqual(
            outgoing.json()["relationships"][0]["direction"],
            "outgoing",
        )

        incoming = self.list_relationships(
            "drawing_revision",
            self.entities["drawing_revision"],
        )
        item = incoming.json()["relationships"][0]
        self.assertEqual(item["direction"], "incoming")
        self.assertEqual(item["relationship_label"], "Referenced by")
        self.assertEqual(item["related"]["type"], "rfi")

    def test_symmetric_relationship_is_canonical_and_rejects_reverse_duplicate(self):
        forward = {
            "source_type": "rfi",
            "source_id": self.entities["rfi"],
            "target_type": "document",
            "target_id": self.entities["document"],
            "relationship_type": "associated_with",
        }
        created = self.create_relationship(forward)
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertEqual(body["direction"], "symmetric")
        self.assertEqual(body["relationship_label"], "Associated with")
        self.assertEqual(body["source"]["type"], "document")
        self.assertEqual(body["target"]["type"], "rfi")

        reverse = {
            **forward,
            "source_type": "document",
            "source_id": self.entities["document"],
            "target_type": "rfi",
            "target_id": self.entities["rfi"],
        }
        self.assertEqual(self.create_relationship(reverse).status_code, 409)
        self.assertEqual(self.create_relationship(forward).status_code, 409)
        with self.TestingSession() as db:
            self.assertEqual(db.query(EntityRelationship).count(), 1)

    def test_validation_rejects_invalid_combinations_self_and_mass_assignment(self):
        base = {
            "source_type": "rfi",
            "source_id": self.entities["rfi"],
            "target_type": "drawing_revision",
            "target_id": self.entities["drawing_revision"],
            "relationship_type": "references",
        }
        invalid_requests = (
            {**base, "relationship_type": "owns"},
            {**base, "target_type": "daily_log"},
            {
                **base,
                "target_type": "rfi",
                "target_id": self.entities["rfi"],
            },
            {**base, "source_id": 0},
            {**base, "project_id": self.project_id},
            {**base, "created_by": self.owner_id},
            {**base, "direction": "outgoing"},
            {**base, "metadata": {}},
        )
        for payload in invalid_requests:
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.create_relationship(payload).status_code,
                    422,
                )
        with self.TestingSession() as db:
            self.assertEqual(db.query(EntityRelationship).count(), 0)

    def test_source_target_and_project_mismatch_are_not_enumerable(self):
        for entity_type, foreign_id in self.foreign_entities.items():
            counterpart_type = "rfi" if entity_type == "document" else "document"
            counterpart_id = self.entities[counterpart_type]
            source_payload = {
                "source_type": entity_type,
                "source_id": foreign_id,
                "target_type": counterpart_type,
                "target_id": counterpart_id,
                "relationship_type": "associated_with",
            }
            target_payload = {
                "source_type": counterpart_type,
                "source_id": counterpart_id,
                "target_type": entity_type,
                "target_id": foreign_id,
                "relationship_type": "associated_with",
            }
            with self.subTest(entity_type=entity_type, side="source"):
                self.assertEqual(
                    self.create_relationship(source_payload).status_code,
                    404,
                )
            with self.subTest(entity_type=entity_type, side="target"):
                self.assertEqual(
                    self.create_relationship(target_payload).status_code,
                    404,
                )
            hidden = self.list_relationships(entity_type, foreign_id)
            self.assertEqual(hidden.status_code, 404)

        mismatch = {
            "source_type": "rfi",
            "source_id": self.entities["rfi"],
            "target_type": "drawing_revision",
            "target_id": self.second_entities["drawing_revision"],
            "relationship_type": "references",
        }
        self.assertEqual(self.create_relationship(mismatch).status_code, 404)

    def test_filters_pagination_and_stable_ordering(self):
        payloads = (
            {
                "source_type": "rfi",
                "source_id": self.entities["rfi"],
                "target_type": "drawing_sheet",
                "target_id": self.entities["drawing_sheet"],
                "relationship_type": "references",
            },
            {
                "source_type": "submittal",
                "source_id": self.entities["submittal"],
                "target_type": "rfi",
                "target_id": self.entities["rfi"],
                "relationship_type": "responds_to",
            },
            {
                "source_type": "rfi",
                "source_id": self.entities["rfi"],
                "target_type": "document",
                "target_id": self.entities["document"],
                "relationship_type": "associated_with",
            },
        )
        ids = [self.create_relationship(payload).json()["id"] for payload in payloads]

        first = self.list_relationships(
            "rfi",
            self.entities["rfi"],
            limit=2,
            offset=0,
        ).json()
        self.assertEqual(first["pagination"]["total"], 3)
        self.assertTrue(first["pagination"]["has_more"])
        self.assertEqual(
            [item["id"] for item in first["relationships"]],
            list(reversed(ids[-2:])),
        )
        second = self.list_relationships(
            "rfi",
            self.entities["rfi"],
            limit=2,
            offset=2,
        ).json()
        self.assertFalse(second["pagination"]["has_more"])
        self.assertEqual(len(second["relationships"]), 1)

        incoming = self.list_relationships(
            "rfi",
            self.entities["rfi"],
            direction="incoming",
        ).json()["relationships"]
        self.assertEqual([item["relationship_type"] for item in incoming], ["responds_to"])
        filtered = self.list_relationships(
            "rfi",
            self.entities["rfi"],
            relationship_type="references",
            related_type="drawing_sheet",
        ).json()["relationships"]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["related"]["type"], "drawing_sheet")

    def test_candidates_cover_all_types_and_never_leak_foreign_records(self):
        search_by_type = {
            "document": "Coordination owned",
            "drawing_set": "IFC owned",
            "drawing_sheet": f"A-{self.project_id}01",
            "drawing_revision": "Coordination revision",
            "drawing_issue": "Permit issue owned",
            "rfi": "Shelf lighting owned",
            "submittal": "Lighting package owned",
            "punch_item": "Repair lighting owned",
            "change_order": "Lighting revision owned",
            "daily_log": "Builder owned",
        }
        for entity_type, search in search_by_type.items():
            with self.subTest(entity_type=entity_type):
                response = self.client.get(
                    f"/projects/{self.project_id}/relationship-candidates",
                    params={
                        "entity_type": entity_type,
                        "search": search,
                        "limit": 20,
                    },
                    headers=self.owner_headers,
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["cache-control"], "no-store")
                candidates = response.json()["candidates"]
                self.assertEqual(len(candidates), 1)
                self.assertEqual(candidates[0]["id"], self.entities[entity_type])
                self.assertNotIn("storage_key", str(candidates))
                self.assertNotIn(str(self.foreign_entities[entity_type]), str(candidates))

        bounded = self.client.get(
            f"/projects/{self.project_id}/relationship-candidates",
            params={"entity_type": "document", "limit": 1},
            headers=self.owner_headers,
        ).json()
        self.assertEqual(len(bounded["candidates"]), 1)
        self.assertTrue(bounded["has_more"])
        excluded = self.client.get(
            f"/projects/{self.project_id}/relationship-candidates",
            params={
                "entity_type": "rfi",
                "exclude_type": "rfi",
                "exclude_id": self.entities["rfi"],
            },
            headers=self.owner_headers,
        ).json()
        self.assertEqual(excluded["candidates"], [])
        incomplete = self.client.get(
            f"/projects/{self.project_id}/relationship-candidates",
            params={"entity_type": "rfi", "exclude_type": "rfi"},
            headers=self.owner_headers,
        )
        self.assertEqual(incomplete.status_code, 422)

    def test_archived_deleted_superseded_and_missing_entities_are_safe(self):
        links = (
            {
                "source_type": "rfi",
                "source_id": self.entities["rfi"],
                "target_type": "drawing_sheet",
                "target_id": self.entities["drawing_sheet"],
                "relationship_type": "references",
            },
            {
                "source_type": "rfi",
                "source_id": self.entities["rfi"],
                "target_type": "document",
                "target_id": self.entities["document"],
                "relationship_type": "associated_with",
            },
            {
                "source_type": "punch_item",
                "source_id": self.entities["punch_item"],
                "target_type": "drawing_revision",
                "target_id": self.entities["drawing_revision"],
                "relationship_type": "located_on",
            },
            {
                "source_type": "document",
                "source_id": self.entities["document"],
                "target_type": "submittal",
                "target_id": self.entities["submittal"],
                "relationship_type": "supports",
            },
        )
        for payload in links:
            self.assertEqual(self.create_relationship(payload).status_code, 201)

        with self.TestingSession() as db:
            revision = db.get(
                DrawingRevision,
                self.entities["drawing_revision"],
            )
            revision.is_current = False
            db.commit()

        candidates = self.client.get(
            f"/projects/{self.project_id}/relationship-candidates",
            params={
                "entity_type": "drawing_revision",
                "search": "Revision",
            },
            headers=self.owner_headers,
        ).json()["candidates"]
        self.assertEqual(candidates[0]["status"], "Superseded")

        with self.TestingSession() as db:
            sheet = db.get(DrawingSheet, self.entities["drawing_sheet"])
            sheet.status = "archived"
            sheet.deleted_at = datetime.now(timezone.utc)
            document = db.get(Document, self.entities["document"])
            document.status = "Deleted"
            document.deleted_at = datetime.now(timezone.utc)
            submittal = db.get(Submittal, self.entities["submittal"])
            db.delete(submittal)
            db.commit()

        rfi_links = self.list_relationships("rfi", self.entities["rfi"]).json()[
            "relationships"
        ]
        by_type = {item["related"]["type"]: item["related"] for item in rfi_links}
        self.assertEqual(by_type["drawing_sheet"]["status"], "Archived")
        self.assertTrue(by_type["drawing_sheet"]["available"])
        self.assertFalse(by_type["document"]["available"])
        self.assertEqual(by_type["document"]["status"], "Deleted")

        missing = self.list_relationships(
            "document",
            self.entities["document"],
        ).json()["relationships"]
        submittal = next(item for item in missing if item["related"]["type"] == "submittal")
        self.assertEqual(submittal["related"]["identifier"], "Related record unavailable")
        self.assertFalse(submittal["related"]["available"])

        archived_create = self.create_relationship(
            {
                "source_type": "change_order",
                "source_id": self.entities["change_order"],
                "target_type": "drawing_sheet",
                "target_id": self.entities["drawing_sheet"],
                "relationship_type": "impacts",
            }
        )
        self.assertEqual(archived_create.status_code, 409)
        deleted_target = self.create_relationship(
            {
                "source_type": "rfi",
                "source_id": self.entities["rfi"],
                "target_type": "document",
                "target_id": self.entities["document"],
                "relationship_type": "associated_with",
            }
        )
        self.assertEqual(deleted_target.status_code, 409)

    def test_delete_is_soft_repeated_is_404_and_target_is_unchanged(self):
        payload = {
            "source_type": "rfi",
            "source_id": self.entities["rfi"],
            "target_type": "drawing_revision",
            "target_id": self.entities["drawing_revision"],
            "relationship_type": "references",
        }
        relationship_id = self.create_relationship(payload).json()["id"]
        deleted = self.client.delete(
            f"/projects/{self.project_id}/relationships/{relationship_id}",
            headers=self.owner_headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json(), {"message": "Relationship deleted"})
        self.assertEqual(
            self.list_relationships("rfi", self.entities["rfi"]).json()[
                "pagination"
            ]["total"],
            0,
        )
        repeated = self.client.delete(
            f"/projects/{self.project_id}/relationships/{relationship_id}",
            headers=self.owner_headers,
        )
        self.assertEqual(repeated.status_code, 404)
        foreign = self.client.delete(
            f"/projects/{self.foreign_project_id}/relationships/{relationship_id}",
            headers=self.intruder_headers,
        )
        self.assertEqual(foreign.status_code, 404)
        with self.TestingSession() as db:
            relationship = db.get(EntityRelationship, relationship_id)
            self.assertIsNotNone(relationship.deleted_at)
            self.assertIsNotNone(
                db.get(DrawingRevision, self.entities["drawing_revision"])
            )

        recreated = self.create_relationship(payload)
        self.assertEqual(recreated.status_code, 201)
        self.assertNotEqual(recreated.json()["id"], relationship_id)

    def test_mixed_listing_uses_batched_resolver_queries(self):
        payloads = (
            ("drawing_sheet", "references"),
            ("drawing_revision", "references"),
            ("document", "associated_with"),
            ("change_order", "impacts"),
        )
        for target_type, relationship_type in payloads:
            self.create_relationship(
                {
                    "source_type": "rfi",
                    "source_id": self.entities["rfi"],
                    "target_type": target_type,
                    "target_id": self.entities[target_type],
                    "relationship_type": relationship_type,
                }
            )

        statements = []

        def track_query(_connection, _cursor, statement, *_args):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", track_query)
        try:
            response = self.list_relationships("rfi", self.entities["rfi"])
        finally:
            event.remove(self.engine, "before_cursor_execute", track_query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["relationships"]), 4)
        self.assertLessEqual(len(statements), 11)


if __name__ == "__main__":
    unittest.main()
