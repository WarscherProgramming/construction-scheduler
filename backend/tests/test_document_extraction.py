from dataclasses import replace
from datetime import timedelta
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.api.dependencies import (
    get_document_extraction_config,
    get_storage_config,
    get_storage_provider,
    get_storage_provider_resolver,
)
from app.api.routes_document_search import reprocess_rate_limiter
from app.core.config import (
    DEFAULT_ATTACHMENT_MIME_TYPES,
    DOCUMENT_EXTRACTION_CONFIG,
    AttachmentConfig,
)
from app.commands.process_document_extractions import main as extraction_main
from app.extraction.ocr import (
    OCRProvider,
    OCRResult,
    OCRTimeoutError,
)
from app.extraction.pdf import ExtractionError, extract_document_content
from app.main import app
from app.models.document import Document
from app.models.document_extraction import (
    DocumentExtraction,
    DocumentExtractionJob,
    DocumentPageText,
)
from app.services.document_extraction import (
    EXTRACTOR_VERSION,
    claim_extraction_jobs,
    enqueue_document_extraction,
    process_extraction_jobs,
    utc_now,
)
from app.storage.provider import MemoryStorageProvider, StorageProviderError
from tests.test_api import ApiTestCase


class DeterministicOCRProvider(OCRProvider):
    provider_name = "test"

    def __init__(self, text="OCR model AX-410", confidence=87.5):
        self.text = text
        self.confidence = confidence
        self.calls = 0

    @property
    def available(self):
        return True

    def extract_text(self, image, *, language, timeout_seconds):
        self.calls += 1
        return OCRResult(self.text, self.confidence)


class TimeoutOCRProvider(DeterministicOCRProvider):
    def extract_text(self, image, *, language, timeout_seconds):
        raise OCRTimeoutError("timed out")


class FailingMemoryStorage(MemoryStorageProvider):
    def __init__(self):
        super().__init__()
        self.fail_open = False

    def open_stream(self, storage_key, chunk_size):
        if self.fail_open:
            raise StorageProviderError("storage unavailable")
        return super().open_stream(storage_key, chunk_size)


def pdf_bytes(*pages, encrypted=False):
    output = BytesIO()
    encrypt = StandardEncryption("secret") if encrypted else None
    pdf = canvas.Canvas(output, encrypt=encrypt)
    for page in pages or ("",):
        if page == "image":
            image = Image.new("RGB", (300, 120), "white")
            for x in range(40, 260):
                image.putpixel((x, 60), (0, 0, 0))
            source = BytesIO()
            image.save(source, "PNG")
            image.close()
            pdf.drawImage(ImageReader(source), 72, 600, 300, 120)
        elif page:
            pdf.drawString(72, 720, page)
        pdf.showPage()
    pdf.save()
    return output.getvalue()


def raster_bytes(size=(300, 120), image_format="PNG"):
    image = Image.new("RGB", size, "white")
    image.putpixel((10, 10), (0, 0, 0))
    output = BytesIO()
    image.save(output, image_format)
    image.close()
    return output.getvalue()


class ExtractionPipelineTests(ApiTestCase):
    def test_embedded_mixed_blank_and_encrypted_pdfs(self):
        config = replace(
            DOCUMENT_EXTRACTION_CONFIG,
            ocr_enabled=True,
            embedded_text_threshold=10,
        )
        provider = DeterministicOCRProvider()

        embedded = extract_document_content(
            pdf_bytes("Fire-rated assembly RFI-017"),
            "application/pdf",
            provider,
            config,
        )
        mixed = extract_document_content(
            pdf_bytes("Embedded cover text", "image"),
            "application/pdf",
            provider,
            config,
        )
        blank = extract_document_content(
            pdf_bytes(""),
            "application/pdf",
            provider,
            config,
        )

        self.assertEqual(embedded.extraction_method, "embedded_text")
        self.assertEqual(mixed.extraction_method, "mixed")
        self.assertEqual(mixed.pages[1].confidence, 87.5)
        self.assertEqual(blank.status, "completed")
        self.assertEqual(blank.extraction_method, "metadata_only")
        self.assertEqual(provider.calls, 1)
        with self.assertRaises(ExtractionError) as encrypted:
            extract_document_content(
                pdf_bytes("Protected", encrypted=True),
                "application/pdf",
                provider,
                config,
            )
        self.assertEqual(encrypted.exception.code, "encrypted_pdf")

    def test_disabled_ocr_and_ocr_failure_are_factual(self):
        disabled = replace(
            DOCUMENT_EXTRACTION_CONFIG,
            ocr_enabled=False,
        )
        unavailable = extract_document_content(
            pdf_bytes("image"),
            "application/pdf",
            DeterministicOCRProvider(),
            disabled,
        )
        self.assertEqual(unavailable.status, "unavailable")
        self.assertEqual(unavailable.warning_codes, ("ocr_unavailable",))

        enabled = replace(disabled, ocr_enabled=True)
        with self.assertRaises(ExtractionError) as timeout:
            extract_document_content(
                raster_bytes(),
                "image/png",
                TimeoutOCRProvider(),
                enabled,
            )
        self.assertEqual(timeout.exception.code, "ocr_timeout")
        self.assertTrue(timeout.exception.retryable)

    def test_page_pixel_and_character_limits_are_bounded(self):
        provider = DeterministicOCRProvider(text="X" * 500)
        config = replace(
            DOCUMENT_EXTRACTION_CONFIG,
            ocr_enabled=True,
            max_pages=1,
            max_chars_per_page=30,
            max_chars_per_document=20,
        )
        with self.assertRaises(ExtractionError) as pages:
            extract_document_content(
                pdf_bytes("First", "Second"),
                "application/pdf",
                provider,
                config,
            )
        self.assertEqual(pages.exception.code, "page_limit_exceeded")

        bounded = extract_document_content(
            raster_bytes(),
            "image/png",
            provider,
            config,
        )
        self.assertEqual(len(bounded.pages[0].text), 20)
        self.assertEqual(bounded.status, "completed_with_warnings")

        page_bounded = extract_document_content(
            raster_bytes(),
            "image/png",
            provider,
            replace(config, max_chars_per_document=1_000),
        )
        self.assertEqual(len(page_bounded.pages[0].text), 30)
        self.assertEqual(
            page_bounded.warning_codes,
            ("text_limit_exceeded",),
        )

        with self.assertRaises(ExtractionError) as pixels:
            extract_document_content(
                raster_bytes((120, 120)),
                "image/png",
                provider,
                replace(config, ocr_max_dimension=100),
            )
        self.assertEqual(pixels.exception.code, "image_limit_exceeded")

    def test_corrupt_and_unsupported_content_fail_safely(self):
        provider = DeterministicOCRProvider()
        with self.assertRaises(ExtractionError) as corrupt:
            extract_document_content(
                b"not a pdf",
                "application/pdf",
                provider,
                DOCUMENT_EXTRACTION_CONFIG,
            )
        self.assertEqual(corrupt.exception.code, "corrupt_file")
        with self.assertRaises(ExtractionError) as unsupported:
            extract_document_content(
                b"plain",
                "text/plain",
                provider,
                DOCUMENT_EXTRACTION_CONFIG,
            )
        self.assertEqual(unsupported.exception.code, "unsupported_type")


class DocumentExtractionApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.storage = FailingMemoryStorage()
        self.storage_config = AttachmentConfig(
            storage_provider="memory",
            local_storage_root=Path("unused"),
            max_upload_size=2 * 1024 * 1024,
            upload_chunk_size=1024,
            permitted_mime_types=DEFAULT_ATTACHMENT_MIME_TYPES,
        )
        self.extraction_config = replace(
            DOCUMENT_EXTRACTION_CONFIG,
            ocr_enabled=False,
            retry_base_seconds=1,
            retry_max_seconds=2,
            max_attempts=2,
        )
        app.dependency_overrides[get_storage_provider] = lambda: self.storage
        app.dependency_overrides[get_storage_provider_resolver] = (
            lambda: lambda provider: self.storage
        )
        app.dependency_overrides[get_storage_config] = (
            lambda: self.storage_config
        )
        app.dependency_overrides[get_document_extraction_config] = (
            lambda: self.extraction_config
        )
        self.owner = self.register_and_login("extract-owner@example.com")
        self.intruder = self.register_and_login("extract-other@example.com")
        self.project_id = self.create_project(self.owner, "Searchable")
        self.foreign_project_id = self.create_project(
            self.intruder,
            "Private",
        )

    def upload_pdf(self, text="Embedded sprinkler specification"):
        return self.client.post(
            "/documents/upload",
            data={"project_id": str(self.project_id)},
            files={
                "file": (
                    "specification.pdf",
                    pdf_bytes(text),
                    "application/pdf",
                )
            },
            headers=self.owner,
        )

    def process(self, provider=None, max_jobs=10):
        with self.TestingSession() as db:
            return process_extraction_jobs(
                db,
                lambda name: self.storage,
                self.storage_config,
                self.extraction_config,
                ocr_provider=provider or DeterministicOCRProvider(),
                max_jobs=max_jobs,
            )

    def test_upload_queues_once_and_processing_persists_page_text(self):
        document = self.upload_pdf().json()
        with self.TestingSession() as db:
            extraction = db.query(DocumentExtraction).one()
            self.assertEqual(extraction.status, "pending")
            self.assertEqual(extraction.source_checksum, document["checksum_sha256"])
            self.assertEqual(extraction.extractor_version, EXTRACTOR_VERSION)
            stored_document = db.get(Document, document["id"])
            _, duplicate = enqueue_document_extraction(
                db,
                stored_document,
                stored_document.uploaded_by,
                self.extraction_config,
            )
            self.assertEqual(duplicate.id, db.query(DocumentExtractionJob).one().id)
            self.assertEqual(db.query(DocumentExtractionJob).count(), 1)

        with self.TestingSession() as db:
            disabled = process_extraction_jobs(
                db,
                lambda name: self.storage,
                self.storage_config,
                replace(self.extraction_config, enabled=False),
                max_jobs=1,
            )
        self.assertEqual(disabled.claimed, 0)

        result = self.process()
        self.assertEqual(result.completed, 1)
        with self.TestingSession() as db:
            extraction = db.query(DocumentExtraction).one()
            page = db.query(DocumentPageText).one()
            self.assertEqual(extraction.status, "completed")
            self.assertTrue(extraction.searchable)
            self.assertEqual(page.page_number, 1)
            self.assertIn("sprinkler", page.text)
            self.assertNotIn("specification.pdf", page.text)
            stored_document = db.get(Document, document["id"])
            stored_document.checksum_sha256 = "f" * 64
            pending, replacement_job = enqueue_document_extraction(
                db,
                stored_document,
                stored_document.uploaded_by,
                self.extraction_config,
                force=True,
            )
            self.assertIsNotNone(replacement_job)
            self.assertEqual(
                pending.source_checksum,
                document["checksum_sha256"],
            )

    def test_status_reprocess_auth_ownership_and_mass_assignment(self):
        document_id = self.upload_pdf().json()["id"]
        path = (
            f"/projects/{self.project_id}/documents/{document_id}/extraction"
        )
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(
            self.client.get(path, headers=self.intruder).status_code,
            403,
        )
        status_response = self.client.get(path, headers=self.owner)
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["extraction"]["status"], "pending")
        self.assertEqual(status_response.headers["cache-control"], "no-store")

        reprocess = self.client.post(
            f"{path}/reprocess",
            json={},
            headers=self.owner,
        )
        duplicate = self.client.post(
            f"{path}/reprocess",
            json={},
            headers=self.owner,
        )
        mass_assignment = self.client.post(
            f"{path}/reprocess",
            json={"status": "completed"},
            headers=self.owner,
        )
        self.assertEqual(reprocess.status_code, 202)
        self.assertEqual(duplicate.status_code, 202)
        self.assertEqual(mass_assignment.status_code, 422)
        with self.TestingSession() as db:
            self.assertEqual(db.query(DocumentExtractionJob).count(), 1)

        wrong_project = self.client.get(
            f"/projects/{self.project_id + 100}/documents/{document_id}/extraction",
            headers=self.owner,
        )
        self.assertEqual(wrong_project.status_code, 403)
        missing = self.client.get(
            f"/projects/{self.project_id}/documents/999999/extraction",
            headers=self.owner,
        )
        self.assertEqual(missing.status_code, 404)

    def test_reprocess_is_rate_limited_and_unsupported_types_are_factual(self):
        document_id = self.upload_pdf().json()["id"]
        endpoint = (
            f"/projects/{self.project_id}/documents/{document_id}/"
            "extraction/reprocess"
        )
        responses = [
            self.client.post(endpoint, json={}, headers=self.owner)
            for _ in range(self.extraction_config.reprocess_rate_limit + 1)
        ]
        self.assertTrue(all(response.status_code == 202 for response in responses[:-1]))
        self.assertEqual(responses[-1].status_code, 429)
        self.assertIn("retry-after", responses[-1].headers)
        reprocess_rate_limiter.clear()

        unsupported = self.client.post(
            "/documents/upload",
            data={"project_id": str(self.project_id)},
            files={"file": ("notes.txt", b"plain notes", "text/plain")},
            headers=self.owner,
        )
        self.assertEqual(unsupported.status_code, 201)
        unsupported_id = unsupported.json()["id"]
        status_response = self.client.get(
            f"/projects/{self.project_id}/documents/{unsupported_id}/extraction",
            headers=self.owner,
        ).json()["extraction"]
        self.assertEqual(status_response["extraction_method"], "metadata_only")
        self.assertEqual(status_response["failure_code"], "unsupported_type")
        self.assertEqual(
            self.client.post(
                f"/projects/{self.project_id}/documents/{unsupported_id}/"
                "extraction/reprocess",
                json={},
                headers=self.owner,
            ).status_code,
            409,
        )

    def test_storage_failure_retries_then_fails_safely(self):
        document_id = self.upload_pdf().json()["id"]
        self.storage.fail_open = True
        first = self.process(max_jobs=1)
        self.assertEqual(first.retryable, 1)
        with self.TestingSession() as db:
            job = db.query(DocumentExtractionJob).one()
            job.available_at = utc_now() - timedelta(seconds=1)
            db.commit()
        second = self.process(max_jobs=1)
        self.assertEqual(second.failed, 1)
        response = self.client.get(
            f"/projects/{self.project_id}/documents/{document_id}/extraction",
            headers=self.owner,
        ).json()["extraction"]
        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["failure_code"], "storage_unavailable")
        self.assertNotIn("storage_key", json.dumps(response))

        exit_code = extraction_main(
            [
                "--retry-failed",
                "--document-id",
                str(document_id),
                "--max-jobs",
                "1",
            ],
            session_factory=self.TestingSession,
            storage_config=self.storage_config,
            extraction_config=self.extraction_config,
            storage_resolver=lambda provider: self.storage,
            ocr_provider=DeterministicOCRProvider(),
        )
        self.assertEqual(exit_code, 0)
        with self.TestingSession() as db:
            retried_job = db.query(DocumentExtractionJob).one()
            self.assertEqual(retried_job.status, "pending")
            self.assertEqual(retried_job.attempt_count, 1)

    def test_expired_lease_recovery_rejects_stale_claim(self):
        self.upload_pdf()
        with self.TestingSession() as db:
            first = claim_extraction_jobs(
                db,
                batch_size=1,
                lease_seconds=1,
                max_attempts=self.extraction_config.max_attempts,
            )[0]
            job = db.get(DocumentExtractionJob, first.job_id)
            job.lease_expires_at = utc_now() - timedelta(seconds=1)
            db.commit()
            second = claim_extraction_jobs(
                db,
                batch_size=1,
                lease_seconds=30,
                max_attempts=self.extraction_config.max_attempts,
            )[0]
            job = db.get(DocumentExtractionJob, second.job_id)
            job.lease_expires_at = utc_now() - timedelta(seconds=1)
            db.commit()
            exhausted = claim_extraction_jobs(
                db,
                batch_size=1,
                lease_seconds=30,
                max_attempts=self.extraction_config.max_attempts,
            )
            job = db.get(DocumentExtractionJob, second.job_id)
        self.assertEqual(first.job_id, second.job_id)
        self.assertNotEqual(first.lease_token, second.lease_token)
        self.assertEqual(exhausted, ())
        self.assertEqual(job.status, "failed")

    def test_soft_delete_cancels_pending_extraction(self):
        document_id = self.upload_pdf().json()["id"]
        deleted = self.client.delete(
            f"/documents/{document_id}",
            headers=self.owner,
        )
        self.assertEqual(deleted.status_code, 200)
        with self.TestingSession() as db:
            self.assertEqual(db.query(DocumentExtraction).one().status, "cancelled")
            self.assertEqual(db.query(DocumentExtractionJob).one().status, "cancelled")

    def test_drawing_upload_queues_in_the_same_transaction(self):
        drawing_set = self.client.post(
            f"/projects/{self.project_id}/drawing-sets",
            json={"name": "IFC", "status": "active"},
            headers=self.owner,
        ).json()
        metadata = {
            "sheet_number": "A-101",
            "title": "Floor Plan",
            "discipline": "A",
            "revision_code": "0",
            "revision_date": "2026-08-01",
        }
        created = self.client.post(
            f"/drawing-sets/{drawing_set['id']}/sheets",
            data={"metadata": json.dumps(metadata)},
            files={
                "file": (
                    "A-101.pdf",
                    pdf_bytes("Drawing floor plan"),
                    "application/pdf",
                )
            },
            headers=self.owner,
        )
        self.assertEqual(created.status_code, 201)
        with self.TestingSession() as db:
            self.assertEqual(db.query(DocumentExtractionJob).count(), 1)
            job = db.query(DocumentExtractionJob).one()
            self.assertEqual(job.document_id, created.json()["current_revision"]["document_id"])

    def test_finite_worker_command_processes_a_bounded_batch(self):
        self.upload_pdf("Command smoke test text")
        exit_code = extraction_main(
            ["--batch-size", "1", "--max-jobs", "1"],
            session_factory=self.TestingSession,
            storage_config=self.storage_config,
            extraction_config=self.extraction_config,
            storage_resolver=lambda provider: self.storage,
            ocr_provider=DeterministicOCRProvider(),
        )
        self.assertEqual(exit_code, 0)
        with self.TestingSession() as db:
            self.assertEqual(db.query(DocumentExtractionJob).one().status, "completed")
