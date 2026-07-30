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


if __name__ == "__main__":
    unittest.main()
