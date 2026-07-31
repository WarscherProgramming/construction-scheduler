from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
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
from app.models.attachment_cleanup import AttachmentCleanupJob
from app.models.document import Document
from app.models.folder import Folder
from app.models.user import User
from app.services.document import (
    _validate_folder_ancestry,
    create_document,
    normalize_document_filename,
)
from app.storage.provider import MemoryStorageProvider, StorageProviderError
from tests.test_api import ApiTestCase


PDF_CONTENT = b"%PDF-1.7\ndocument foundation\n%%EOF"


class TrackingMemoryStorage(MemoryStorageProvider):
    def __init__(self):
        super().__init__()
        self.fail_delete = False

    def delete(self, storage_key):
        if self.fail_delete:
            raise StorageProviderError("provider unavailable")
        return super().delete(storage_key)


class DocumentApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.storage = TrackingMemoryStorage()
        self.config = AttachmentConfig(
            storage_provider="memory",
            local_storage_root=Path("unused"),
            max_upload_size=128,
            upload_chunk_size=8,
            permitted_mime_types=DEFAULT_ATTACHMENT_MIME_TYPES,
        )
        app.dependency_overrides[get_storage_provider] = (
            lambda: self.storage
        )
        app.dependency_overrides[get_storage_provider_resolver] = (
            lambda: lambda provider: self.storage
        )
        app.dependency_overrides[get_storage_config] = lambda: self.config

        self.owner_headers = self.register_and_login("owner@example.com")
        self.intruder_headers = self.register_and_login(
            "intruder@example.com"
        )
        self.project_id = self.create_project(self.owner_headers, "Owned")
        self.other_project_id = self.create_project(
            self.owner_headers,
            "Second",
        )
        self.unowned_project_id = self.create_project(
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

    def upload(
        self,
        *,
        project_id=None,
        headers=None,
        filename="plans.pdf",
        content=PDF_CONTENT,
        mime_type="application/pdf",
        folder_id=None,
        display_name=None,
    ):
        data = {"project_id": str(project_id or self.project_id)}
        if folder_id is not None:
            data["folder_id"] = str(folder_id)
        if display_name is not None:
            data["display_name"] = display_name
        return self.client.post(
            "/documents/upload",
            data=data,
            files={"file": (filename, content, mime_type)},
            headers=headers or self.owner_headers,
        )

    def create_folder(
        self,
        name,
        *,
        project_id=None,
        parent_folder_id=None,
        headers=None,
    ):
        return self.client.post(
            f"/projects/{project_id or self.project_id}/folders",
            json={
                "name": name,
                "parent_folder_id": parent_folder_id,
            },
            headers=headers or self.owner_headers,
        )

    def explore(self, *, project_id=None, headers=None, **params):
        return self.client.get(
            f"/projects/{project_id or self.project_id}/documents/explorer",
            params=params,
            headers=headers or self.owner_headers,
        )

    def test_document_routes_require_authentication(self):
        requests = (
            self.client.post(
                "/documents/upload",
                data={"project_id": "1"},
                files={
                    "file": (
                        "plans.pdf",
                        PDF_CONTENT,
                        "application/pdf",
                    )
                },
            ),
            self.client.get("/documents/1"),
            self.client.get("/documents/1/download"),
            self.client.delete("/documents/1"),
            self.client.get("/projects/1/documents"),
            self.client.get("/projects/1/folders"),
            self.client.post(
                "/projects/1/folders",
                json={"name": "Drawings"},
            ),
        )

        self.assertTrue(
            all(response.status_code == 401 for response in requests)
        )

    def test_upload_metadata_listing_and_download_are_safe(self):
        folder = self.create_folder("Drawings").json()
        response = self.upload(
            folder_id=folder["id"],
            filename="issued plans.pdf",
            display_name="Issued Plans",
        )

        self.assertEqual(response.status_code, 201)
        document = response.json()
        self.assertEqual(document["display_name"], "Issued Plans")
        self.assertEqual(document["folder_id"], folder["id"])
        self.assertEqual(document["size_bytes"], len(PDF_CONTENT))
        self.assertEqual(
            document["checksum_sha256"],
            sha256(PDF_CONTENT).hexdigest(),
        )
        self.assertEqual(document["version"], 1)
        self.assertTrue(document["is_current_version"])
        self.assertEqual(document["status"], "Active")
        for internal_name in (
            "storage_key",
            "storage_provider",
            "storage_bucket",
            "path",
            "url",
        ):
            self.assertNotIn(internal_name, document)

        metadata = self.client.get(
            f"/documents/{document['id']}",
            headers=self.owner_headers,
        )
        listing = self.client.get(
            f"/projects/{self.project_id}/documents",
            params={"folder_id": folder["id"]},
            headers=self.owner_headers,
        )
        download = self.client.get(
            f"/documents/{document['id']}/download",
            headers=self.owner_headers,
        )

        self.assertEqual(metadata.json(), document)
        self.assertEqual(listing.json()["documents"], [document])
        self.assertEqual(download.content, PDF_CONTENT)
        self.assertEqual(download.headers["content-length"], str(len(PDF_CONTENT)))
        self.assertEqual(download.headers["x-content-type-options"], "nosniff")
        self.assertEqual(download.headers["content-security-policy"], "sandbox")
        self.assertIn("issued%20plans.pdf", download.headers["content-disposition"])

        with self.TestingSession() as db:
            stored = db.query(Document).filter(Document.id == document["id"]).one()
            self.assertRegex(
                stored.storage_key,
                r"^documents/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{32}$",
            )
            self.assertNotIn("issued", stored.storage_key)

    def test_folders_are_hierarchical_and_unique_per_sibling(self):
        root = self.create_folder("Drawings")
        child = self.create_folder(
            "Issued",
            parent_folder_id=root.json()["id"],
        )
        same_name_elsewhere = self.create_folder(
            "Issued",
            project_id=self.other_project_id,
        )
        duplicate_root = self.create_folder("Drawings")
        duplicate_child = self.create_folder(
            "Issued",
            parent_folder_id=root.json()["id"],
        )

        self.assertEqual(root.status_code, 201)
        self.assertEqual(child.status_code, 201)
        self.assertEqual(same_name_elsewhere.status_code, 201)
        self.assertEqual(duplicate_root.status_code, 409)
        self.assertEqual(duplicate_child.status_code, 409)
        self.assertEqual(
            child.json()["path"],
            f"{root.json()['path']}/{child.json()['id']}",
        )

        listing = self.client.get(
            f"/projects/{self.project_id}/folders",
            headers=self.owner_headers,
        )
        self.assertEqual(
            [folder["name"] for folder in listing.json()["folders"]],
            ["Drawings", "Issued"],
        )

    def test_folder_integrity_rejects_invalid_foreign_and_cyclic_parents(self):
        invalid_names = (".", "..", "bad/name", "bad\\name", "trail.")
        for name in invalid_names:
            with self.subTest(name=name):
                self.assertEqual(self.create_folder(name).status_code, 422)

        foreign = self.create_folder(
            "Private Folder",
            project_id=self.unowned_project_id,
            headers=self.intruder_headers,
        )
        cross_project = self.create_folder(
            "Cross Project",
            parent_folder_id=foreign.json()["id"],
        )
        self.assertEqual(cross_project.status_code, 404)

        root = self.create_folder("Root").json()
        child = self.create_folder(
            "Child",
            parent_folder_id=root["id"],
        ).json()
        with self.TestingSession() as db:
            root_record = db.query(Folder).filter(Folder.id == root["id"]).one()
            root_record.parent_folder_id = child["id"]
            db.commit()
            child_record = db.query(Folder).filter(Folder.id == child["id"]).one()
            with self.assertRaises(HTTPException) as context:
                _validate_folder_ancestry(db, self.project_id, child_record)
        self.assertEqual(context.exception.status_code, 409)

    def test_project_and_document_ownership_is_enforced_without_leakage(self):
        document_id = self.upload().json()["id"]

        for method, path in (
            ("get", f"/documents/{document_id}"),
            ("get", f"/documents/{document_id}/download"),
            ("delete", f"/documents/{document_id}"),
        ):
            with self.subTest(path=path):
                response = getattr(self.client, method)(
                    path,
                    headers=self.intruder_headers,
                )
                self.assertEqual(response.status_code, 404)

        for path in (
            f"/projects/{self.project_id}/documents",
            f"/projects/{self.project_id}/folders",
        ):
            self.assertEqual(
                self.client.get(path, headers=self.intruder_headers).status_code,
                403,
            )
        self.assertEqual(
            self.create_folder(
                "No Access",
                headers=self.intruder_headers,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.upload(
                project_id=self.unowned_project_id,
                headers=self.owner_headers,
            ).status_code,
            403,
        )

    def test_upload_rejects_malformed_files_and_metadata(self):
        cases = (
            ("../plans.pdf", PDF_CONTENT, "application/pdf", 422),
            ("CON.pdf", PDF_CONTENT, "application/pdf", 422),
            ("plans.exe", b"MZpayload", "application/octet-stream", 415),
            ("plans.pdf", PDF_CONTENT, "image/png", 415),
            ("empty.pdf", b"", "application/pdf", 422),
            ("large.pdf", b"%PDF-" + b"x" * 200, "application/pdf", 413),
        )
        for filename, content, mime_type, expected in cases:
            with self.subTest(filename=filename):
                response = self.upload(
                    filename=filename,
                    content=content,
                    mime_type=mime_type,
                )
                self.assertEqual(response.status_code, expected)

        too_long_extension = f"plans.{('x' * 21)}"
        self.assertEqual(
            self.upload(
                filename=too_long_extension,
                content=b"content",
                mime_type="application/octet-stream",
            ).status_code,
            422,
        )
        for filename in ("bad\x00name.pdf", "bad\x1fname.pdf"):
            with self.subTest(filename=repr(filename)):
                with self.assertRaises(HTTPException) as context:
                    normalize_document_filename(filename)
                self.assertEqual(context.exception.status_code, 422)

    def test_soft_delete_is_idempotent_and_retains_object_for_restore(self):
        created = self.upload().json()
        with self.TestingSession() as db:
            storage_key = (
                db.query(Document)
                .filter(Document.id == created["id"])
                .one()
                .storage_key
            )

        first = self.client.delete(
            f"/documents/{created['id']}",
            headers=self.owner_headers,
        )
        second = self.client.delete(
            f"/documents/{created['id']}",
            headers=self.owner_headers,
        )
        missing = self.client.get(
            f"/documents/{created['id']}",
            headers=self.owner_headers,
        )
        listing = self.client.get(
            f"/projects/{self.project_id}/documents",
            headers=self.owner_headers,
        )

        self.assertEqual(first.json(), {"message": "Document deleted"})
        self.assertEqual(second.json(), {"message": "Document deleted"})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(listing.json(), {"documents": []})
        self.assertTrue(self.storage.exists(storage_key))
        with self.TestingSession() as db:
            deleted = db.query(Document).filter(Document.id == created["id"]).one()
            self.assertIsNotNone(deleted.deleted_at)
            self.assertFalse(deleted.is_current_version)
            self.assertEqual(deleted.status, "Deleted")

    def test_upload_database_failure_removes_object(self):
        with self.TestingSession() as db:
            upload = UploadFile(
                BytesIO(PDF_CONTENT),
                size=len(PDF_CONTENT),
                filename="plans.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            )
            with patch.object(
                db,
                "commit",
                side_effect=SQLAlchemyError("database unavailable"),
            ):
                with self.assertRaises(HTTPException) as context:
                    create_document(
                        db,
                        self.storage,
                        self.config,
                        project_id=self.project_id,
                        folder_id=None,
                        upload=upload,
                        uploaded_by=self.owner_id,
                        display_name=None,
                        document_type=None,
                        content_length=None,
                    )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(self.storage.objects, {})

    def test_upload_cleanup_failure_creates_durable_cleanup_job(self):
        with self.TestingSession() as db:
            upload = UploadFile(
                BytesIO(PDF_CONTENT),
                size=len(PDF_CONTENT),
                filename="plans.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            )
            original_commit = db.commit
            commit_calls = 0

            def fail_first_commit():
                nonlocal commit_calls
                commit_calls += 1
                if commit_calls == 1:
                    raise SQLAlchemyError("database unavailable")
                return original_commit()

            self.storage.fail_delete = True
            with patch.object(db, "commit", side_effect=fail_first_commit):
                with self.assertRaises(HTTPException):
                    create_document(
                        db,
                        self.storage,
                        self.config,
                        project_id=self.project_id,
                        folder_id=None,
                        upload=upload,
                        uploaded_by=self.owner_id,
                        display_name=None,
                        document_type=None,
                        content_length=None,
                    )

        with self.TestingSession() as db:
            self.assertEqual(db.query(Document).count(), 0)
            job = db.query(AttachmentCleanupJob).one()
            self.assertIsNone(job.attachment_id)
            self.assertEqual(job.project_id, self.project_id)
            self.assertEqual(job.storage_provider, "memory")
            self.assertEqual(job.status, "Pending")

    def test_explorer_root_and_nested_folder_response_with_counts(self):
        root = self.create_folder("Drawings").json()
        child = self.create_folder(
            "Issued",
            parent_folder_id=root["id"],
        ).json()
        empty = self.create_folder(
            "Empty",
            parent_folder_id=root["id"],
        ).json()
        root_document = self.upload(display_name="Root File").json()
        child_document = self.upload(
            folder_id=child["id"],
            display_name="Issued Plan",
        ).json()

        root_response = self.explore()
        nested_response = self.explore(folder_id=root["id"])
        empty_response = self.explore(folder_id=empty["id"])

        self.assertEqual(root_response.status_code, 200)
        self.assertEqual(root_response.headers["cache-control"], "no-store")
        root_body = root_response.json()
        self.assertIsNone(root_body["current_folder"])
        self.assertEqual(root_body["breadcrumbs"], [])
        self.assertEqual(
            [folder["name"] for folder in root_body["folders"]],
            ["Drawings"],
        )
        self.assertEqual(root_body["folders"][0]["child_folder_count"], 2)
        self.assertEqual(root_body["documents"][0]["id"], root_document["id"])

        nested_body = nested_response.json()
        self.assertEqual(nested_body["current_folder"]["id"], root["id"])
        self.assertEqual(
            nested_body["breadcrumbs"],
            [{"id": root["id"], "name": "Drawings"}],
        )
        self.assertEqual(
            [folder["name"] for folder in nested_body["folders"]],
            ["Empty", "Issued"],
        )
        issued = next(
            folder
            for folder in nested_body["folders"]
            if folder["id"] == child["id"]
        )
        self.assertEqual(issued["document_count"], 1)
        self.assertEqual(
            empty_response.json()["documents"],
            [],
        )
        self.assertEqual(
            empty_response.json()["pagination"]["total"],
            0,
        )
        self.assertEqual(child_document["folder_id"], child["id"])

    def test_explorer_nested_breadcrumbs_and_safe_fields(self):
        first = self.create_folder("Plans").json()
        second = self.create_folder(
            "Level 2",
            parent_folder_id=first["id"],
        ).json()
        third = self.create_folder(
            "Architectural",
            parent_folder_id=second["id"],
        ).json()
        document = self.upload(
            folder_id=third["id"],
            display_name="Floor Plan",
        ).json()

        response = self.explore(folder_id=third["id"])

        self.assertEqual(
            response.json()["breadcrumbs"],
            [
                {"id": first["id"], "name": "Plans"},
                {"id": second["id"], "name": "Level 2"},
                {"id": third["id"], "name": "Architectural"},
            ],
        )
        item = response.json()["documents"][0]
        self.assertEqual(item["id"], document["id"])
        self.assertEqual(
            set(item),
            {
                "id",
                "folder_id",
                "display_name",
                "original_filename",
                "extension",
                "mime_type",
                "size_bytes",
                "document_type",
                "status",
                "version",
                "created_at",
                "updated_at",
            },
        )
        for internal in (
            "storage_key",
            "storage_bucket",
            "storage_provider",
            "checksum_sha256",
            "uploaded_by",
        ):
            self.assertNotIn(internal, response.text)

    def test_explorer_search_escapes_wildcards_and_is_case_insensitive(self):
        self.upload(
            filename="percent.pdf",
            display_name="100%_Complete",
        )
        self.upload(
            filename="plans.pdf",
            display_name="Issued PLANS",
        )
        self.upload(
            filename="other.pdf",
            display_name="Specifications",
        )

        plans = self.explore(search="plans").json()["documents"]
        wildcard_literal = self.explore(search="%_").json()["documents"]

        self.assertEqual(
            [document["display_name"] for document in plans],
            ["Issued PLANS"],
        )
        self.assertEqual(
            [document["display_name"] for document in wildcard_literal],
            ["100%_Complete"],
        )
        self.assertEqual(self.explore(search=" ").status_code, 422)

    def test_explorer_sort_filter_pagination_and_stable_order(self):
        first = self.upload(
            filename="first.pdf",
            display_name="Same Name",
        ).json()
        second = self.upload(
            filename="second.pdf",
            display_name="Same Name",
        ).json()
        third = self.upload(
            filename="third.pdf",
            display_name="Different",
        ).json()
        with self.TestingSession() as db:
            db.query(Document).filter(
                Document.id.in_([first["id"], second["id"]])
            ).update(
                {Document.document_type: "Drawing"},
                synchronize_session=False,
            )
            db.query(Document).filter(Document.id == third["id"]).update(
                {Document.document_type: "Report"},
                synchronize_session=False,
            )
            db.commit()

        response = self.explore(
            document_type="drawing",
            mime_type="APPLICATION/PDF",
            extension="pdf",
            sort="name",
            order="asc",
            limit=1,
            offset=0,
        )
        second_page = self.explore(
            document_type="Drawing",
            sort="name",
            order="asc",
            limit=1,
            offset=1,
        )

        body = response.json()
        self.assertEqual(body["pagination"]["total"], 2)
        self.assertTrue(body["pagination"]["has_more"])
        self.assertEqual(body["documents"][0]["id"], first["id"])
        self.assertEqual(second_page.json()["documents"][0]["id"], second["id"])
        self.assertFalse(second_page.json()["pagination"]["has_more"])
        self.assertEqual(
            self.explore(sort="storage_key").status_code,
            422,
        )
        self.assertEqual(self.explore(limit=101).status_code, 422)
        self.assertEqual(self.explore(offset=-1).status_code, 422)

    def test_recent_documents_are_current_active_and_deterministic(self):
        folder = self.create_folder("Archive").json()
        oldest = self.upload(
            filename="oldest.pdf",
            display_name="Oldest",
        ).json()
        newest = self.upload(
            filename="newest.pdf",
            display_name="Newest",
        ).json()
        not_current = self.upload(
            filename="version.pdf",
            display_name="Old Version",
        ).json()
        deleted = self.upload(
            filename="deleted.pdf",
            display_name="Deleted",
        ).json()
        hidden_folder = self.upload(
            folder_id=folder["id"],
            filename="hidden.pdf",
            display_name="Hidden Folder",
        ).json()
        base = datetime(2026, 7, 30, tzinfo=timezone.utc)
        with self.TestingSession() as db:
            db.query(Document).filter(Document.id == oldest["id"]).update(
                {Document.created_at: base},
                synchronize_session=False,
            )
            db.query(Document).filter(Document.id == newest["id"]).update(
                {Document.created_at: base + timedelta(hours=1)},
                synchronize_session=False,
            )
            db.query(Document).filter(
                Document.id == not_current["id"]
            ).update(
                {Document.is_current_version: False},
                synchronize_session=False,
            )
            db.query(Document).filter(Document.id == deleted["id"]).update(
                {Document.deleted_at: base},
                synchronize_session=False,
            )
            db.query(Folder).filter(Folder.id == folder["id"]).update(
                {Folder.deleted_at: base},
                synchronize_session=False,
            )
            db.commit()

        response = self.client.get(
            f"/projects/{self.project_id}/documents/recent",
            params={"limit": 2},
            headers=self.owner_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(
            [document["id"] for document in response.json()["documents"]],
            [newest["id"], oldest["id"]],
        )
        excluded_ids = {
            not_current["id"],
            deleted["id"],
            hidden_folder["id"],
        }
        self.assertTrue(
            excluded_ids.isdisjoint(
                document["id"]
                for document in response.json()["documents"]
            )
        )
        self.assertEqual(
            self.client.get(
                f"/projects/{self.project_id}/documents/recent",
                params={"limit": 26},
                headers=self.owner_headers,
            ).status_code,
            422,
        )

    def test_folder_tree_is_flat_bounded_safe_and_excludes_deleted(self):
        root = self.create_folder("Root").json()
        child = self.create_folder(
            "Child",
            parent_folder_id=root["id"],
        ).json()
        deleted = self.create_folder("Deleted").json()
        self.upload(folder_id=child["id"])
        with self.TestingSession() as db:
            db.query(Folder).filter(Folder.id == deleted["id"]).update(
                {Folder.deleted_at: datetime.now(timezone.utc)},
                synchronize_session=False,
            )
            db.commit()

        response = self.client.get(
            f"/projects/{self.project_id}/folders/tree",
            headers=self.owner_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(
            {folder["id"] for folder in response.json()["folders"]},
            {root["id"], child["id"]},
        )
        child_response = next(
            folder
            for folder in response.json()["folders"]
            if folder["id"] == child["id"]
        )
        self.assertEqual(child_response["document_count"], 1)
        self.assertNotIn("path", response.text)

    def test_explorer_routes_enforce_project_ownership_and_guessed_ids(self):
        private_folder = self.create_folder(
            "Private",
            project_id=self.unowned_project_id,
            headers=self.intruder_headers,
        ).json()

        for path in (
            f"/projects/{self.unowned_project_id}/documents/explorer",
            f"/projects/{self.unowned_project_id}/documents/recent",
            f"/projects/{self.unowned_project_id}/folders/tree",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    self.client.get(
                        path,
                        headers=self.owner_headers,
                    ).status_code,
                    403,
                )
        self.assertEqual(
            self.explore(folder_id=private_folder["id"]).status_code,
            404,
        )
        self.assertEqual(self.explore(folder_id=2_147_483_648).status_code, 422)

    def test_upload_and_soft_delete_are_reflected_in_explorer(self):
        folder = self.create_folder("Field Reports").json()
        created = self.upload(
            folder_id=folder["id"],
            filename="report.pdf",
            display_name="Daily Report",
        ).json()
        before = self.explore(folder_id=folder["id"]).json()

        deleted = self.client.delete(
            f"/documents/{created['id']}",
            headers=self.owner_headers,
        )
        after = self.explore(folder_id=folder["id"]).json()

        self.assertEqual(before["pagination"]["total"], 1)
        self.assertEqual(before["documents"][0]["id"], created["id"])
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(after["documents"], [])
        self.assertEqual(after["pagination"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
