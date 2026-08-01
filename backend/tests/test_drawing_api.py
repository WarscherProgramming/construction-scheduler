from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.datastructures import Headers

from app.api.dependencies import (
    get_storage_config,
    get_storage_provider,
    get_storage_provider_resolver,
)
from app.core.config import (
    DEFAULT_ATTACHMENT_MIME_TYPES,
    AttachmentConfig,
)
from app.main import app
from app.models.document import Document
from app.models.drawing import (
    DrawingIssue,
    DrawingIssueRevision,
    DrawingRevision,
    DrawingSheet,
)
from app.models.user import User
from app.schemas.drawing import DrawingRevisionCreateMetadata
from app.services.drawing import create_drawing_revision
from app.storage.provider import MemoryStorageProvider
from tests.test_api import ApiTestCase


PDF_CONTENT = b"%PDF-1.7\ndrawing revision\n%%EOF"


class DrawingApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.storage = MemoryStorageProvider()
        self.config = AttachmentConfig(
            storage_provider="memory",
            local_storage_root=Path("unused"),
            max_upload_size=1024 * 1024,
            upload_chunk_size=16,
            permitted_mime_types=DEFAULT_ATTACHMENT_MIME_TYPES,
        )
        app.dependency_overrides[get_storage_provider] = (
            lambda: self.storage
        )
        app.dependency_overrides[get_storage_provider_resolver] = (
            lambda: lambda provider: self.storage
        )
        app.dependency_overrides[get_storage_config] = lambda: self.config
        self.owner = self.register_and_login("drawing-owner@example.com")
        self.intruder = self.register_and_login(
            "drawing-intruder@example.com"
        )
        self.project_id = self.create_project(self.owner, "Terminal")
        self.foreign_project_id = self.create_project(
            self.intruder, "Private"
        )

    def create_set(self, name="Issued for Construction", **overrides):
        payload = {
            "name": name,
            "description": "Construction issue set",
            "status": "active",
            "issue_date": "2026-07-30",
            **overrides,
        }
        return self.client.post(
            f"/projects/{self.project_id}/drawing-sets",
            json=payload,
            headers=self.owner,
        )

    def create_sheet(
        self,
        drawing_set_id,
        *,
        sheet_number="A-101",
        title="Floor Plan",
        discipline="A",
        revision_code="0",
        revision_date="2026-07-30",
        filename="A-101.pdf",
        content=PDF_CONTENT,
        headers=None,
    ):
        metadata = {
            "sheet_number": sheet_number,
            "title": title,
            "discipline": discipline,
            "description": "Level one plan",
            "revision_code": revision_code,
            "revision_date": revision_date,
            "revision_description": "Initial issue",
        }
        return self.client.post(
            f"/drawing-sets/{drawing_set_id}/sheets",
            data={"metadata": json.dumps(metadata)},
            files={"file": (filename, content, "application/pdf")},
            headers=headers or self.owner,
        )

    def upload_revision(
        self,
        sheet_id,
        code="1",
        *,
        date="2026-08-01",
        filename="A-101-r1.pdf",
        content=PDF_CONTENT,
        headers=None,
    ):
        return self.client.post(
            f"/drawing-sheets/{sheet_id}/revisions",
            data={
                "metadata": json.dumps(
                    {
                        "revision_code": code,
                        "revision_date": date,
                        "description": f"Revision {code}",
                    }
                )
            },
            files={"file": (filename, content, "application/pdf")},
            headers=headers or self.owner,
        )

    def test_drawing_routes_require_authentication(self):
        requests = (
            self.client.get("/projects/1/drawing-sets"),
            self.client.post(
                "/projects/1/drawing-sets", json={"name": "Permit"}
            ),
            self.client.get("/projects/1/drawings"),
            self.client.get("/drawing-sets/1"),
            self.client.get("/drawing-sheets/1"),
            self.client.get("/drawing-issues/1"),
            self.client.get("/drawing-revisions/1/download"),
        )
        self.assertTrue(all(response.status_code == 401 for response in requests))

    def test_drawing_set_create_list_update_archive_and_duplicate(self):
        created = self.create_set()
        self.assertEqual(created.status_code, 201)
        drawing_set = created.json()
        self.assertEqual(drawing_set["sheet_count"], 0)

        duplicate = self.create_set()
        self.assertEqual(duplicate.status_code, 409)

        listing = self.client.get(
            f"/projects/{self.project_id}/drawing-sets",
            headers=self.owner,
        )
        self.assertEqual(len(listing.json()["drawing_sets"]), 1)

        updated = self.client.patch(
            f"/drawing-sets/{drawing_set['id']}",
            json={"name": "IFC Set"},
            headers=self.owner,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "IFC Set")

        archived = self.client.delete(
            f"/drawing-sets/{drawing_set['id']}",
            headers=self.owner,
        )
        self.assertEqual(archived.json()["status"], "archived")
        hidden = self.client.get(
            f"/projects/{self.project_id}/drawing-sets",
            headers=self.owner,
        )
        self.assertEqual(hidden.json()["drawing_sets"], [])
        retained = self.client.get(
            f"/drawing-sets/{drawing_set['id']}", headers=self.owner
        )
        self.assertEqual(retained.status_code, 200)

    def test_sheet_first_revision_is_atomic_safe_and_explorer_visible(self):
        drawing_set = self.create_set().json()
        response = self.create_sheet(drawing_set["id"])
        self.assertEqual(response.status_code, 201)
        sheet = response.json()
        current = sheet["current_revision"]
        self.assertEqual(sheet["revision_count"], 1)
        self.assertTrue(current["is_current"])
        self.assertEqual(current["sequence_number"], 1)
        self.assertNotIn("storage_key", str(response.json()))
        self.assertNotIn("checksum", str(response.json()))

        explorer = self.client.get(
            f"/projects/{self.project_id}/documents/explorer",
            headers=self.owner,
        ).json()
        self.assertEqual(len(explorer["documents"]), 1)
        self.assertEqual(explorer["documents"][0]["document_type"], "Drawing")

        download = self.client.get(
            f"/drawing-revisions/{current['id']}/download",
            headers=self.owner,
        )
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, PDF_CONTENT)
        self.assertEqual(download.headers["content-type"], "application/pdf")
        self.assertEqual(download.headers["content-length"], str(len(PDF_CONTENT)))
        self.assertNotIn("accept-ranges", download.headers)
        self.assertEqual(download.headers["cache-control"], "private, no-store")
        self.assertEqual(download.headers["x-content-type-options"], "nosniff")
        self.assertEqual(download.headers["content-security-policy"], "sandbox")

    def test_sheet_number_normalization_discipline_and_mass_assignment(self):
        drawing_set = self.create_set().json()
        first = self.create_sheet(drawing_set["id"], sheet_number="A-101")
        self.assertEqual(first.status_code, 201)
        duplicate = self.create_sheet(
            drawing_set["id"],
            sheet_number="a 101",
            title="Duplicate",
        )
        self.assertEqual(duplicate.status_code, 409)

        invalid = self.create_sheet(
            drawing_set["id"],
            sheet_number="M-101",
            discipline="Unrestricted",
        )
        self.assertEqual(invalid.status_code, 422)

        metadata = {
            "sheet_number": "E-101",
            "title": "Power Plan",
            "discipline": "E",
            "revision_code": "0",
            "revision_date": "2026-07-30",
            "project_id": self.foreign_project_id,
            "current_revision_id": 999,
        }
        mass_assignment = self.client.post(
            f"/drawing-sets/{drawing_set['id']}/sheets",
            data={"metadata": json.dumps(metadata)},
            files={"file": ("E-101.pdf", PDF_CONTENT, "application/pdf")},
            headers=self.owner,
        )
        self.assertEqual(mass_assignment.status_code, 422)

    def test_new_revision_supersedes_once_and_preserves_old_download(self):
        drawing_set = self.create_set().json()
        sheet = self.create_sheet(drawing_set["id"]).json()
        first = sheet["current_revision"]
        second_response = self.upload_revision(sheet["id"], "1")
        self.assertEqual(second_response.status_code, 201)
        second = second_response.json()
        self.assertTrue(second["is_current"])
        self.assertEqual(second["sequence_number"], 2)

        history = self.client.get(
            f"/drawing-sheets/{sheet['id']}/revisions",
            headers=self.owner,
        ).json()["revisions"]
        self.assertEqual([item["sequence_number"] for item in history], [2, 1])
        old = history[1]
        self.assertFalse(old["is_current"])
        self.assertEqual(old["superseded_by_revision_id"], second["id"])
        self.assertIsNotNone(old["superseded_at"])

        current = self.client.get(
            f"/drawing-sheets/{sheet['id']}/current-revision",
            headers=self.owner,
        ).json()
        self.assertEqual(current["id"], second["id"])
        old_download = self.client.get(
            f"/drawing-revisions/{first['id']}/download",
            headers=self.owner,
        )
        self.assertEqual(old_download.content, PDF_CONTENT)

        with self.TestingSession() as db:
            self.assertEqual(
                db.query(DrawingRevision)
                .filter(
                    DrawingRevision.drawing_sheet_id == sheet["id"],
                    DrawingRevision.is_current.is_(True),
                )
                .count(),
                1,
            )
            persisted = db.get(DrawingSheet, sheet["id"])
            self.assertEqual(persisted.current_revision_id, second["id"])

    def test_duplicate_revision_invalid_pdf_and_storage_cleanup(self):
        drawing_set = self.create_set().json()
        sheet = self.create_sheet(drawing_set["id"]).json()
        object_count = len(self.storage.objects)

        duplicate = self.upload_revision(sheet["id"], "0")
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(len(self.storage.objects), object_count)

        invalid_extension = self.upload_revision(
            sheet["id"], "2", filename="A-101.svg"
        )
        self.assertEqual(invalid_extension.status_code, 415)
        self.assertEqual(len(self.storage.objects), object_count)

        invalid_signature = self.upload_revision(
            sheet["id"], "2", content=b"not a pdf"
        )
        self.assertEqual(invalid_signature.status_code, 415)
        self.assertEqual(len(self.storage.objects), object_count)

    def test_revision_rollback_cleans_storage_and_current_constraint_holds(self):
        drawing_set = self.create_set().json()
        sheet_payload = self.create_sheet(drawing_set["id"]).json()
        first_revision_id = sheet_payload["current_revision"]["id"]
        object_count = len(self.storage.objects)

        with self.TestingSession() as db:
            sheet = db.get(DrawingSheet, sheet_payload["id"])
            user_id = (
                db.query(User.id)
                .filter(User.email == "drawing-owner@example.com")
                .scalar()
            )
            upload = UploadFile(
                BytesIO(PDF_CONTENT),
                size=len(PDF_CONTENT),
                filename="A-101-r1.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            )
            with patch.object(
                db,
                "commit",
                side_effect=SQLAlchemyError("database unavailable"),
            ):
                with self.assertRaises(HTTPException) as context:
                    create_drawing_revision(
                        db,
                        self.storage,
                        self.config,
                        sheet,
                        user_id,
                        DrawingRevisionCreateMetadata(
                            revision_code="1",
                            revision_date="2026-08-01",
                        ),
                        upload,
                        None,
                    )
        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(len(self.storage.objects), object_count)

        with self.TestingSession() as db:
            persisted_sheet = db.get(DrawingSheet, sheet_payload["id"])
            first_revision = db.get(DrawingRevision, first_revision_id)
            self.assertEqual(
                persisted_sheet.current_revision_id, first_revision_id
            )
            self.assertTrue(first_revision.is_current)
            constraint_document = Document(
                project_id=self.project_id,
                folder_id=None,
                original_filename="constraint.pdf",
                display_name="Constraint probe",
                extension=".pdf",
                mime_type="application/pdf",
                size_bytes=len(PDF_CONTENT),
                checksum_sha256="0" * 64,
                storage_provider="memory",
                storage_key="drawing-constraint-probe",
                uploaded_by=user_id,
                document_type="Drawing",
                status="Active",
            )
            db.add(constraint_document)
            db.flush()
            duplicate_current = DrawingRevision(
                project_id=self.project_id,
                drawing_sheet_id=sheet_payload["id"],
                document_id=constraint_document.id,
                revision_code="2",
                normalized_revision_code="2",
                revision_date="2026-08-02",
                sequence_number=2,
                is_current=True,
                uploaded_by=user_id,
            )
            db.add(duplicate_current)
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_issue_draft_membership_freezes_then_voids(self):
        drawing_set = self.create_set().json()
        sheet = self.create_sheet(drawing_set["id"]).json()
        revision_id = sheet["current_revision"]["id"]
        created = self.client.post(
            f"/drawing-sets/{drawing_set['id']}/issues",
            json={
                "name": "Permit Submission",
                "issue_number": "ISS-001",
                "issue_date": "2026-07-30",
                "purpose": "permit",
                "notes": "Authority review",
            },
            headers=self.owner,
        )
        self.assertEqual(created.status_code, 201)
        issue = created.json()
        self.assertEqual(issue["status"], "draft")

        added = self.client.post(
            f"/drawing-issues/{issue['id']}/revisions",
            json={"revision_id": revision_id},
            headers=self.owner,
        )
        self.assertEqual(len(added.json()["revisions"]), 1)
        issued = self.client.post(
            f"/drawing-issues/{issue['id']}/issue",
            headers=self.owner,
        )
        self.assertEqual(issued.json()["status"], "issued")

        frozen = self.client.delete(
            f"/drawing-issues/{issue['id']}/revisions/{revision_id}",
            headers=self.owner,
        )
        self.assertEqual(frozen.status_code, 409)
        edit_frozen = self.client.patch(
            f"/drawing-issues/{issue['id']}",
            json={"name": "Changed"},
            headers=self.owner,
        )
        self.assertEqual(edit_frozen.status_code, 409)

        voided = self.client.post(
            f"/drawing-issues/{issue['id']}/void",
            headers=self.owner,
        )
        self.assertEqual(voided.json()["status"], "void")
        repeated = self.client.post(
            f"/drawing-issues/{issue['id']}/void",
            headers=self.owner,
        )
        self.assertEqual(repeated.json()["status"], "void")

    def test_issue_rejects_cross_set_and_duplicate_sheet_membership(self):
        first_set = self.create_set("Set One").json()
        second_set = self.create_set("Set Two").json()
        first_sheet = self.create_sheet(first_set["id"]).json()
        second_sheet = self.create_sheet(
            second_set["id"], sheet_number="E-101", discipline="E"
        ).json()
        issue = self.client.post(
            f"/drawing-sets/{first_set['id']}/issues",
            json={
                "name": "IFC",
                "issue_number": "1",
                "issue_date": "2026-07-30",
                "purpose": "construction",
            },
            headers=self.owner,
        ).json()

        cross_set = self.client.post(
            f"/drawing-issues/{issue['id']}/revisions",
            json={"revision_id": second_sheet["current_revision"]["id"]},
            headers=self.owner,
        )
        self.assertEqual(cross_set.status_code, 404)
        self.client.post(
            f"/drawing-issues/{issue['id']}/revisions",
            json={"revision_id": first_sheet["current_revision"]["id"]},
            headers=self.owner,
        )
        second_revision = self.upload_revision(first_sheet["id"], "1").json()
        duplicate_sheet = self.client.post(
            f"/drawing-issues/{issue['id']}/revisions",
            json={"revision_id": second_revision["id"]},
            headers=self.owner,
        )
        self.assertEqual(duplicate_sheet.status_code, 409)

    def test_register_search_filter_sort_pagination_and_safe_fields(self):
        drawing_set = self.create_set("Permit Set").json()
        self.create_sheet(
            drawing_set["id"],
            sheet_number="A-2",
            title="Second Floor",
        )
        self.create_sheet(
            drawing_set["id"],
            sheet_number="A-10",
            title="Tenth Floor",
        )
        self.create_sheet(
            drawing_set["id"],
            sheet_number="E-1",
            title="Lighting %_ Plan",
            discipline="E",
        )
        register = self.client.get(
            f"/projects/{self.project_id}/drawings",
            params={"limit": 2, "sort": "sheet_number"},
            headers=self.owner,
        ).json()
        self.assertEqual(register["pagination"]["total"], 3)
        self.assertTrue(register["pagination"]["has_more"])
        self.assertEqual(
            [sheet["sheet_number"] for sheet in register["sheets"]],
            ["A-2", "A-10"],
        )

        filtered = self.client.get(
            f"/projects/{self.project_id}/drawings",
            params={"discipline": "E", "search": "%_"},
            headers=self.owner,
        ).json()
        self.assertEqual(
            [sheet["sheet_number"] for sheet in filtered["sheets"]],
            ["E-1"],
        )
        self.assertNotIn("storage_key", str(filtered))
        self.assertEqual(
            self.client.get(
                f"/projects/{self.project_id}/drawings",
                params={"sort": "raw_database_column"},
                headers=self.owner,
            ).status_code,
            422,
        )

    def test_archival_and_referenced_document_deletion_preserve_history(self):
        drawing_set = self.create_set().json()
        sheet = self.create_sheet(drawing_set["id"]).json()
        document_id = sheet["current_revision"]["document_id"]
        blocked = self.client.delete(
            f"/documents/{document_id}", headers=self.owner
        )
        self.assertEqual(blocked.status_code, 409)

        archived = self.client.delete(
            f"/drawing-sheets/{sheet['id']}", headers=self.owner
        )
        self.assertEqual(archived.json()["status"], "archived")
        history = self.client.get(
            f"/drawing-sheets/{sheet['id']}/revisions",
            headers=self.owner,
        )
        self.assertEqual(history.status_code, 200)
        with self.TestingSession() as db:
            self.assertIsNone(db.get(Document, document_id).deleted_at)

    def test_ownership_and_guessed_ids_are_safe(self):
        drawing_set = self.create_set().json()
        sheet = self.create_sheet(drawing_set["id"]).json()
        issue = self.client.post(
            f"/drawing-sets/{drawing_set['id']}/issues",
            json={
                "name": "Draft",
                "issue_number": "D1",
                "issue_date": "2026-07-30",
                "purpose": "other",
            },
            headers=self.owner,
        ).json()
        paths = (
            f"/drawing-sets/{drawing_set['id']}",
            f"/drawing-sheets/{sheet['id']}",
            f"/drawing-sheets/{sheet['id']}/revisions",
            f"/drawing-issues/{issue['id']}",
            (
                "/drawing-revisions/"
                f"{sheet['current_revision']['id']}/download"
            ),
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(
                    self.client.get(path, headers=self.intruder).status_code,
                    404,
                )
        self.assertEqual(
            self.client.get(
                f"/projects/{self.project_id}/drawings",
                headers=self.intruder,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.create_sheet(
                drawing_set["id"], headers=self.intruder
            ).status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
