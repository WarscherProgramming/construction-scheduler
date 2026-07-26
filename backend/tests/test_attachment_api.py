from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers

from app.api.dependencies import (
    get_attachment_config,
    get_attachment_storage,
    get_db,
)
from app.core.config import (
    DEFAULT_ATTACHMENT_MIME_TYPES,
    AttachmentConfig,
)
from app.db.database import Base
from app.main import app
from app.models.attachment import Attachment
from app.models.change_order import ChangeOrder
from app.models.daily_log import DailyLog
from app.models.project import Project
from app.models.punch_item import PunchItem
from app.models.rfi import RFI
from app.models.submittal import Submittal
from app.models.user import User
from app.services.attachment import (
    create_attachment,
    delete_attachments_for_parent,
    list_attachment_records,
    sanitize_attachment_filename,
)
from app.storage.attachment import (
    AttachmentStorageError,
    MemoryAttachmentStorage,
)


PDF_CONTENT = b"%PDF-1.7\nattachment test\n%%EOF"
PNG_CONTENT = b"\x89PNG\r\n\x1a\n" + b"image-data"
TEXT_CONTENT = b"FieldFlow attachment text"
OLE_CONTENT = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"office-data"
ZIP_CONTENT = b"PK\x03\x04" + b"office-archive"


class TrackingMemoryStorage(MemoryAttachmentStorage):
    def __init__(self):
        super().__init__()
        self.put_calls = 0
        self.open_calls = 0
        self.delete_calls = 0
        self.fail_put = False
        self.fail_open = False
        self.fail_delete = False

    def put_stream(self, storage_key, chunks):
        self.put_calls += 1
        if self.fail_put:
            raise AttachmentStorageError("provider unavailable")
        return super().put_stream(storage_key, chunks)

    def open_stream(self, storage_key, chunk_size):
        self.open_calls += 1
        if self.fail_open:
            raise AttachmentStorageError("provider unavailable")
        return super().open_stream(storage_key, chunk_size)

    def delete(self, storage_key):
        self.delete_calls += 1
        if self.fail_delete:
            raise AttachmentStorageError("provider unavailable")
        return super().delete(storage_key)


class BoundedReadBytesIO(BytesIO):
    def read(self, size=-1):
        if size is None or size < 0:
            raise AssertionError("Attachment reads must always be bounded")
        return super().read(size)


class AttachmentApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.TestingSession = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
        )

        def override_get_db():
            db = self.TestingSession()
            try:
                yield db
            finally:
                db.close()

        self.storage = TrackingMemoryStorage()
        self.config = AttachmentConfig(
            storage_provider="memory",
            local_storage_root=Path("unused"),
            max_upload_size=26_214_400,
            upload_chunk_size=8,
            permitted_mime_types=DEFAULT_ATTACHMENT_MIME_TYPES,
        )

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_attachment_storage] = (
            lambda: self.storage
        )
        app.dependency_overrides[get_attachment_config] = (
            lambda: self.config
        )
        self.client = TestClient(app)

        self.owner_headers = self.register_and_login("owner@example.com")
        self.intruder_headers = self.register_and_login(
            "intruder@example.com"
        )
        self.project_id = self.create_project(
            self.owner_headers,
            "Riverside",
        )
        self.other_project_id = self.create_project(
            self.owner_headers,
            "North Ridge",
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
            self.parents = self.create_parent_records(db, self.project_id)
            self.other_parents = self.create_parent_records(
                db,
                self.other_project_id,
                suffix="2",
            )
            db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def register_and_login(self, email):
        self.client.post(
            "/auth/register",
            json={"email": email, "password": "Secret123!"},
        )
        response = self.client.post(
            "/auth/login",
            data={"username": email, "password": "Secret123!"},
        )
        return {
            "Authorization": (
                f"Bearer {response.json()['access_token']}"
            )
        }

    def create_project(self, headers, name):
        response = self.client.post(
            "/projects",
            json={"name": name},
            headers=headers,
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def create_parent_records(self, db, project_id, suffix="1"):
        records = {
            "daily_log": DailyLog(
                project_id=project_id,
                date="2026-07-26",
                company="Builder",
                manpower=4,
            ),
            "rfi": RFI(
                project_id=project_id,
                number=f"RFI-00{suffix}",
                subject="Field condition",
                question="Please clarify.",
                submitted_date="2026-07-26",
                status="Open",
            ),
            "submittal": Submittal(
                project_id=project_id,
                number=f"SUB-00{suffix}",
                specification_section="03 30 00",
                title="Concrete mix",
                status="Draft",
            ),
            "punch_item": PunchItem(
                project_id=project_id,
                number=f"PUNCH-00{suffix}",
                location="Level 1",
                description="Repair finish",
                priority="Medium",
                status="Open",
            ),
            "change_order": ChangeOrder(
                project_id=project_id,
                date="2026-07-26",
                co_number=f"CO-00{suffix}",
                status="Draft",
                description="Field revision",
            ),
        }
        db.add_all(records.values())
        db.flush()
        return {
            parent_type: record.id
            for parent_type, record in records.items()
        }

    def set_max_upload_size(self, size):
        self.config = AttachmentConfig(
            storage_provider="memory",
            local_storage_root=Path("unused"),
            max_upload_size=size,
            upload_chunk_size=4,
            permitted_mime_types=DEFAULT_ATTACHMENT_MIME_TYPES,
        )

    def upload(
        self,
        *,
        parent_type="project",
        parent_id=None,
        filename="plans.pdf",
        content=PDF_CONTENT,
        mime_type="application/pdf",
        headers=None,
        project_id=None,
    ):
        route_project_id = project_id or self.project_id
        return self.client.post(
            f"/projects/{route_project_id}/attachments",
            data={
                "parent_type": parent_type,
                "parent_id": (
                    route_project_id
                    if parent_id is None
                    else parent_id
                ),
            },
            files={"file": (filename, content, mime_type)},
            headers=headers or self.owner_headers,
        )

    def stored_attachment(self, attachment_id):
        with self.TestingSession() as db:
            return db.get(Attachment, attachment_id)

    def test_attachment_routes_require_authentication(self):
        created = self.upload()
        attachment_id = created.json()["id"]

        requests = [
            self.client.get(
                f"/projects/{self.project_id}/attachments",
                params={
                    "parent_type": "project",
                    "parent_id": self.project_id,
                },
            ),
            self.client.post(
                f"/projects/{self.project_id}/attachments",
                data={
                    "parent_type": "project",
                    "parent_id": self.project_id,
                },
                files={
                    "file": (
                        "plans.pdf",
                        PDF_CONTENT,
                        "application/pdf",
                    )
                },
            ),
            self.client.get(
                f"/projects/{self.project_id}/attachments/"
                f"{attachment_id}/download"
            ),
            self.client.delete(
                f"/projects/{self.project_id}/attachments/{attachment_id}"
            ),
        ]

        self.assertTrue(
            all(response.status_code == 401 for response in requests)
        )

    def test_project_ownership_and_project_scoping_are_enforced(self):
        created = self.upload()
        attachment_id = created.json()["id"]

        unowned = self.client.get(
            f"/projects/{self.project_id}/attachments",
            params={
                "parent_type": "project",
                "parent_id": self.project_id,
            },
            headers=self.intruder_headers,
        )
        missing_in_other_owned_project = self.client.get(
            f"/projects/{self.other_project_id}/attachments/"
            f"{attachment_id}/download",
            headers=self.owner_headers,
        )
        cross_project_delete = self.client.delete(
            f"/projects/{self.other_project_id}/attachments/{attachment_id}",
            headers=self.owner_headers,
        )

        self.assertEqual(unowned.status_code, 403)
        self.assertEqual(missing_in_other_owned_project.status_code, 404)
        self.assertEqual(cross_project_delete.status_code, 404)

    def test_parent_resolver_supports_every_allowed_type(self):
        parent_ids = {
            "project": self.project_id,
            **self.parents,
        }

        for parent_type, parent_id in parent_ids.items():
            with self.subTest(parent_type=parent_type):
                response = self.client.get(
                    f"/projects/{self.project_id}/attachments",
                    params={
                        "parent_type": parent_type.upper(),
                        "parent_id": parent_id,
                    },
                    headers=self.owner_headers,
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"attachments": []})

    def test_parent_resolver_rejects_invalid_and_cross_project_parents(self):
        unknown = self.client.get(
            f"/projects/{self.project_id}/attachments",
            params={"parent_type": "task", "parent_id": 1},
            headers=self.owner_headers,
        )
        missing = self.client.get(
            f"/projects/{self.project_id}/attachments",
            params={"parent_type": "rfi", "parent_id": 9999},
            headers=self.owner_headers,
        )
        wrong_project = self.client.get(
            f"/projects/{self.project_id}/attachments",
            params={
                "parent_type": "rfi",
                "parent_id": self.other_parents["rfi"],
            },
            headers=self.owner_headers,
        )
        project_mismatch = self.client.get(
            f"/projects/{self.project_id}/attachments",
            params={
                "parent_type": "project",
                "parent_id": self.other_project_id,
            },
            headers=self.owner_headers,
        )
        malformed = self.client.get(
            f"/projects/{self.project_id}/attachments",
            params={"parent_type": "project"},
            headers=self.owner_headers,
        )

        self.assertEqual(unknown.status_code, 422)
        self.assertIn("parent_type must be one of", unknown.json()["detail"])
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(wrong_project.status_code, 404)
        self.assertEqual(project_mismatch.status_code, 404)
        self.assertEqual(malformed.status_code, 422)

    def test_upload_persists_safe_metadata_and_streamed_hash(self):
        response = self.upload(
            parent_type=" RFI ",
            parent_id=self.parents["rfi"],
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["project_id"], self.project_id)
        self.assertEqual(body["parent_type"], "rfi")
        self.assertEqual(body["parent_id"], self.parents["rfi"])
        self.assertEqual(body["uploaded_by"], self.owner_id)
        self.assertEqual(body["size_bytes"], len(PDF_CONTENT))
        self.assertEqual(body["sha256"], sha256(PDF_CONTENT).hexdigest())
        self.assertNotIn("storage_key", body)
        self.assertNotIn("storage_provider", body)

        attachment = self.stored_attachment(body["id"])
        self.assertRegex(attachment.storage_key, r"^[0-9a-f]{32}$")
        self.assertNotIn("plans", attachment.storage_key)
        self.assertEqual(
            self.storage.objects[attachment.storage_key],
            PDF_CONTENT,
        )

    def test_upload_accepts_supported_image_text_and_office_containers(self):
        cases = [
            ("photo.png", PNG_CONTENT, "image/png"),
            ("report.txt", TEXT_CONTENT, "text/plain"),
            ("data.csv", b"name,value\nA,1\n", "text/csv"),
            ("memo.doc", OLE_CONTENT, "application/msword"),
            (
                "sheet.xls",
                OLE_CONTENT,
                "application/vnd.ms-excel",
            ),
            (
                "memo.docx",
                ZIP_CONTENT,
                (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            ),
            (
                "sheet.xlsx",
                ZIP_CONTENT,
                (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
            ),
        ]

        for filename, content, mime_type in cases:
            with self.subTest(filename=filename):
                response = self.upload(
                    filename=filename,
                    content=content,
                    mime_type=mime_type,
                )
                self.assertEqual(response.status_code, 201)
                self.assertEqual(
                    response.json()["original_filename"],
                    filename,
                )

    def test_duplicate_display_filenames_are_allowed(self):
        first = self.upload()
        second = self.upload()

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(
            first.json()["original_filename"],
            second.json()["original_filename"],
        )

    def test_filename_sanitization_handles_traversal_and_controls(self):
        self.assertEqual(
            sanitize_attachment_filename("../../plans.pdf"),
            "plans.pdf",
        )
        self.assertEqual(
            sanitize_attachment_filename(
                r"C:\fakepath\  field" + "\x00\t" + " plan.PDF"
            ),
            "field plan.pdf",
        )
        self.assertEqual(
            sanitize_attachment_filename(
                f"{'a' * 300}.pdf"
            ),
            f"{'a' * 251}.pdf",
        )

        with self.assertRaises(HTTPException) as context:
            sanitize_attachment_filename("..")
        self.assertEqual(context.exception.status_code, 422)

    def test_upload_rejects_unsupported_or_mismatched_files(self):
        cases = [
            ("page.html", b"<html></html>", "text/html"),
            ("image.svg", b"<svg></svg>", "image/svg+xml"),
            ("run.exe", b"MZ", "application/octet-stream"),
            ("plans.pdf", PDF_CONTENT, "image/png"),
            ("plans.png", PDF_CONTENT, "image/png"),
            ("plans.pdf", b"not a pdf", "application/pdf"),
            ("data.csv", b"\x00binary", "text/csv"),
        ]

        for filename, content, mime_type in cases:
            with self.subTest(filename=filename, mime_type=mime_type):
                response = self.upload(
                    filename=filename,
                    content=content,
                    mime_type=mime_type,
                )
                self.assertEqual(response.status_code, 415)

    def test_upload_rejects_blank_filename_and_zero_bytes(self):
        blank = self.upload(filename="..")
        empty = self.upload(content=b"")

        self.assertEqual(blank.status_code, 422)
        self.assertEqual(empty.status_code, 422)
        self.assertEqual(self.storage.objects, {})

    def test_upload_size_boundary_is_inclusive_and_cleans_partial_data(self):
        exact = b"%PDF-" + b"a" * 11
        self.set_max_upload_size(len(exact))
        accepted = self.upload(content=exact)
        rejected = self.upload(content=exact + b"b")

        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(rejected.status_code, 413)
        self.assertEqual(len(self.storage.objects), 1)

    def test_oversized_content_length_is_rejected_before_storage(self):
        huge_length = (
            self.config.max_upload_size + 1_048_576 + 1
        )
        response = self.upload(
            headers={
                **self.owner_headers,
                "Content-Length": str(huge_length),
            }
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.storage.put_calls, 0)

    def test_streamed_limit_failure_leaves_no_partial_object(self):
        self.set_max_upload_size(8)
        with self.TestingSession() as db:
            upload = UploadFile(
                BytesIO(PDF_CONTENT),
                size=None,
                filename="plans.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            )
            with self.assertRaises(HTTPException) as context:
                create_attachment(
                    db,
                    self.storage,
                    self.config,
                    project_id=self.project_id,
                    parent_type="project",
                    parent_id=self.project_id,
                    upload=upload,
                    uploaded_by=self.owner_id,
                    content_length=None,
                )

        self.assertEqual(context.exception.status_code, 413)
        self.assertEqual(self.storage.objects, {})

    def test_upload_service_never_uses_an_unbounded_file_read(self):
        with self.TestingSession() as db:
            upload = UploadFile(
                BoundedReadBytesIO(PDF_CONTENT),
                size=None,
                filename="plans.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            )
            attachment = create_attachment(
                db,
                self.storage,
                self.config,
                project_id=self.project_id,
                parent_type="project",
                parent_id=self.project_id,
                upload=upload,
                uploaded_by=self.owner_id,
                content_length=None,
            )

        self.assertEqual(attachment.size_bytes, len(PDF_CONTENT))
        self.assertEqual(attachment.sha256, sha256(PDF_CONTENT).hexdigest())

    def test_storage_upload_failure_returns_503(self):
        self.storage.fail_put = True
        response = self.upload()

        self.assertEqual(response.status_code, 503)
        with self.TestingSession() as db:
            self.assertEqual(db.query(Attachment).count(), 0)

    def test_database_failure_after_storage_triggers_cleanup(self):
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
                    create_attachment(
                        db,
                        self.storage,
                        self.config,
                        project_id=self.project_id,
                        parent_type="project",
                        parent_id=self.project_id,
                        upload=upload,
                        uploaded_by=self.owner_id,
                        content_length=None,
                    )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(self.storage.objects, {})
        self.assertEqual(self.storage.delete_calls, 1)

    def test_listing_is_parent_scoped_ordered_and_metadata_only(self):
        first = self.upload(filename="first.pdf")
        second = self.upload(filename="second.pdf")
        self.upload(
            parent_type="rfi",
            parent_id=self.parents["rfi"],
            filename="other.pdf",
        )
        other_project = self.upload(
            project_id=self.other_project_id,
            filename="other-project.pdf",
        )
        open_calls_before = self.storage.open_calls

        response = self.client.get(
            f"/projects/{self.project_id}/attachments",
            params={
                "parent_type": "project",
                "parent_id": self.project_id,
            },
            headers=self.owner_headers,
        )

        self.assertEqual(response.status_code, 200)
        attachments = response.json()["attachments"]
        self.assertEqual(
            [item["id"] for item in attachments],
            [first.json()["id"], second.json()["id"]],
        )
        self.assertTrue(
            all("storage_key" not in item for item in attachments)
        )
        self.assertEqual(self.storage.open_calls, open_calls_before)

        empty = self.client.get(
            f"/projects/{self.other_project_id}/attachments",
            params={
                "parent_type": "project",
                "parent_id": self.other_project_id,
            },
            headers=self.owner_headers,
        )
        self.assertEqual(
            [item["id"] for item in empty.json()["attachments"]],
            [other_project.json()["id"]],
        )

    def test_download_streams_content_and_sets_security_headers(self):
        created = self.upload(filename="résumé plans.pdf")
        response = self.client.get(
            f"/projects/{self.project_id}/attachments/"
            f"{created.json()['id']}/download",
            headers=self.owner_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, PDF_CONTENT)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(
            response.headers["content-length"],
            str(len(PDF_CONTENT)),
        )
        self.assertEqual(
            response.headers["x-content-type-options"],
            "nosniff",
        )
        self.assertEqual(
            response.headers["content-security-policy"],
            "sandbox",
        )
        self.assertTrue(
            response.headers["content-disposition"].startswith("inline;")
        )
        self.assertIn("filename*=UTF-8''", response.headers["content-disposition"])

    def test_download_uses_attachment_disposition_for_text_and_office(self):
        image_attachment = self.upload(
            filename="photo.png",
            content=PNG_CONTENT,
            mime_type="image/png",
        )
        text_attachment = self.upload(
            filename="report.txt",
            content=TEXT_CONTENT,
            mime_type="text/plain",
        )
        office_attachment = self.upload(
            filename="memo.doc",
            content=OLE_CONTENT,
            mime_type="application/msword",
        )

        image_response = self.client.get(
            f"/projects/{self.project_id}/attachments/"
            f"{image_attachment.json()['id']}/download",
            headers=self.owner_headers,
        )
        self.assertTrue(
            image_response.headers["content-disposition"].startswith(
                "inline;"
            )
        )

        for attachment_id in (
            text_attachment.json()["id"],
            office_attachment.json()["id"],
        ):
            with self.subTest(attachment_id=attachment_id):
                response = self.client.get(
                    f"/projects/{self.project_id}/attachments/"
                    f"{attachment_id}/download",
                    headers=self.owner_headers,
                )
                self.assertTrue(
                    response.headers["content-disposition"].startswith(
                        "attachment;"
                    )
                )

    def test_download_handles_missing_metadata_object_and_outage(self):
        missing = self.client.get(
            f"/projects/{self.project_id}/attachments/9999/download",
            headers=self.owner_headers,
        )
        created = self.upload()
        attachment = self.stored_attachment(created.json()["id"])
        self.storage.delete(attachment.storage_key)

        missing_object = self.client.get(
            f"/projects/{self.project_id}/attachments/"
            f"{attachment.id}/download",
            headers=self.owner_headers,
        )
        self.storage.fail_open = True
        outage = self.client.get(
            f"/projects/{self.project_id}/attachments/"
            f"{attachment.id}/download",
            headers=self.owner_headers,
        )

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing_object.status_code, 503)
        self.assertEqual(outage.status_code, 503)
        self.assertNotIn(
            attachment.storage_key,
            missing_object.json()["detail"],
        )

    def test_delete_removes_storage_and_metadata(self):
        created = self.upload()
        attachment = self.stored_attachment(created.json()["id"])

        response = self.client.delete(
            f"/projects/{self.project_id}/attachments/{attachment.id}",
            headers=self.owner_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Attachment deleted"})
        self.assertFalse(self.storage.exists(attachment.storage_key))
        self.assertIsNone(self.stored_attachment(attachment.id))

        missing = self.client.delete(
            f"/projects/{self.project_id}/attachments/{attachment.id}",
            headers=self.owner_headers,
        )
        self.assertEqual(missing.status_code, 404)

    def test_delete_is_idempotent_for_missing_object(self):
        created = self.upload()
        attachment = self.stored_attachment(created.json()["id"])
        self.storage.delete(attachment.storage_key)

        response = self.client.delete(
            f"/projects/{self.project_id}/attachments/{attachment.id}",
            headers=self.owner_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.stored_attachment(attachment.id))

    def test_delete_outage_preserves_metadata(self):
        created = self.upload()
        attachment_id = created.json()["id"]
        self.storage.fail_delete = True

        response = self.client.delete(
            f"/projects/{self.project_id}/attachments/{attachment_id}",
            headers=self.owner_headers,
        )

        self.assertEqual(response.status_code, 503)
        self.assertIsNotNone(self.stored_attachment(attachment_id))

    def test_parent_cleanup_helper_lists_and_removes_attachments(self):
        first = self.upload()
        second = self.upload()

        with self.TestingSession() as db:
            listed = list_attachment_records(
                db,
                self.project_id,
                "project",
                self.project_id,
            )
            self.assertEqual(
                [item.id for item in listed],
                [first.json()["id"], second.json()["id"]],
            )
            removed = delete_attachments_for_parent(
                db,
                self.storage,
                self.project_id,
                "project",
                self.project_id,
            )

        self.assertEqual(removed, 2)
        self.assertEqual(self.storage.objects, {})
        with self.TestingSession() as db:
            self.assertEqual(db.query(Attachment).count(), 0)

    def test_parent_cleanup_storage_failure_preserves_metadata(self):
        created = self.upload()
        self.storage.fail_delete = True

        with self.TestingSession() as db:
            with self.assertRaises(HTTPException) as context:
                delete_attachments_for_parent(
                    db,
                    self.storage,
                    self.project_id,
                    "project",
                    self.project_id,
                )

        self.assertEqual(context.exception.status_code, 503)
        self.assertIsNotNone(
            self.stored_attachment(created.json()["id"])
        )


if __name__ == "__main__":
    unittest.main()
