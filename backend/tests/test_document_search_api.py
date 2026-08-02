from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path

from reportlab.pdfgen import canvas

from app.api.dependencies import (
    get_storage_config,
    get_storage_provider,
    get_storage_provider_resolver,
)
from app.core.config import (
    DEFAULT_ATTACHMENT_MIME_TYPES,
    DOCUMENT_EXTRACTION_CONFIG,
    AttachmentConfig,
)
from app.main import app
from app.models.document import Document
from app.models.document_extraction import DocumentPageText
from app.services.document_extraction import process_extraction_jobs
from app.storage.provider import MemoryStorageProvider
from tests.test_api import ApiTestCase


def searchable_pdf(text):
    output = BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()
    return output.getvalue()


class DocumentSearchApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.storage = MemoryStorageProvider()
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
        )
        app.dependency_overrides[get_storage_provider] = lambda: self.storage
        app.dependency_overrides[get_storage_provider_resolver] = (
            lambda: lambda provider: self.storage
        )
        app.dependency_overrides[get_storage_config] = (
            lambda: self.storage_config
        )
        self.owner = self.register_and_login("search-owner@example.com")
        self.intruder = self.register_and_login("search-other@example.com")
        self.project_id = self.create_project(self.owner, "Terminal Expansion")
        self.private_project_id = self.create_project(
            self.intruder,
            "Private Search",
        )

    def upload(
        self,
        display_name,
        text,
        *,
        project_id=None,
        headers=None,
        document_type="Specification",
    ):
        return self.client.post(
            "/documents/upload",
            data={
                "project_id": str(project_id or self.project_id),
                "display_name": display_name,
                "document_type": document_type,
            },
            files={
                "file": (
                    f"{display_name}.pdf",
                    searchable_pdf(text),
                    "application/pdf",
                )
            },
            headers=headers or self.owner,
        )

    def process(self):
        with self.TestingSession() as db:
            return process_extraction_jobs(
                db,
                lambda provider: self.storage,
                self.storage_config,
                self.extraction_config,
                max_jobs=20,
            )

    def search(self, query, **params):
        return self.client.get(
            f"/projects/{self.project_id}/search",
            params={"q": query, **params},
            headers=self.owner,
        )

    def test_search_requires_authentication_ownership_and_valid_query(self):
        self.assertEqual(
            self.client.get(
                f"/projects/{self.project_id}/search",
                params={"q": "sprinkler"},
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.get(
                f"/projects/{self.project_id}/search",
                params={"q": "sprinkler"},
                headers=self.intruder,
            ).status_code,
            403,
        )
        self.assertEqual(self.search("   ").status_code, 422)
        self.assertEqual(self.search("x" * 201).status_code, 422)
        self.assertEqual(self.search("term", scope="records").status_code, 422)

    def test_content_metadata_snippet_ranking_and_safe_fields(self):
        first = self.upload(
            "Fire Protection Specification",
            "Install sprinkler model AX-410 with seismic bracing",
        ).json()
        self.upload(
            "General Notes",
            "Coordinate fire protection sleeves before concrete placement",
        )
        self.process()

        content = self.search("AX-410")
        metadata = self.search("Fire Protection Specification")
        self.assertEqual(content.status_code, 200)
        self.assertEqual(content.headers["cache-control"], "no-store")
        result = content.json()["results"][0]
        self.assertEqual(result["document_id"], first["id"])
        self.assertEqual(result["page_number"], 1)
        self.assertIn("AX-410", result["snippet"])
        self.assertTrue(result["match_ranges"])
        self.assertEqual(result["extraction_method"], "embedded_text")
        self.assertEqual(result["route_target"]["type"], "document")
        metadata_result = metadata.json()["results"][0]
        self.assertGreater(metadata_result["rank"], 1)
        self.assertIsNone(metadata_result["page_number"])
        self.assertEqual(
            metadata_result["extraction_method"],
            "metadata_only",
        )
        self.assertIn(
            "Fire Protection Specification",
            metadata_result["snippet"],
        )
        serialized = json.dumps(result)
        for internal in (
            "storage_key",
            "storage_provider",
            "checksum",
            "search_vector",
            "normalized_text",
        ):
            self.assertNotIn(internal, serialized)

    def test_malicious_text_is_plain_bounded_and_never_full_page(self):
        payload = "<script>alert(1)</script> & formula =SUM(A1:A2) " + "scope " * 100
        self.upload("Unsafe Exhibit", payload)
        self.process()
        result = self.search("script").json()["results"][0]
        self.assertIn("<script>", result["snippet"])
        self.assertLessEqual(len(result["snippet"]), 326)
        self.assertNotIn("html", result)

    def test_pagination_filters_and_stable_empty_results(self):
        self.upload("Mechanical One", "pump schedule model P-100")
        self.upload("Mechanical Two", "pump schedule model P-100")
        self.process()

        first = self.search("P-100", limit=1, offset=0).json()
        second = self.search("P-100", limit=1, offset=1).json()
        self.assertEqual(first["pagination"]["total"], 2)
        self.assertTrue(first["pagination"]["has_more"])
        self.assertNotEqual(
            first["results"][0]["document_id"],
            second["results"][0]["document_id"],
        )
        self.assertEqual(
            self.search("P-100", document_type="Drawing").json()["results"],
            [],
        )
        self.assertEqual(
            self.search(
                "P-100",
                extraction_method="ocr",
            ).json()["results"],
            [],
        )
        self.assertEqual(self.search("no such content").json()["results"], [])

    def test_project_isolation_and_deleted_documents_are_excluded(self):
        owned = self.upload("Owned", "unique isolation phrase").json()
        self.upload(
            "Foreign",
            "unique isolation phrase",
            project_id=self.private_project_id,
            headers=self.intruder,
        )
        self.process()
        results = self.search("unique isolation phrase").json()["results"]
        self.assertEqual([item["document_id"] for item in results], [owned["id"]])
        self.client.delete(f"/documents/{owned['id']}", headers=self.owner)
        self.assertEqual(
            self.search("unique isolation phrase").json()["results"],
            [],
        )

    def test_drawing_results_enrich_and_filter_current_revisions(self):
        drawing_set = self.client.post(
            f"/projects/{self.project_id}/drawing-sets",
            json={"name": "IFC", "status": "active"},
            headers=self.owner,
        ).json()
        metadata = {
            "sheet_number": "M-201",
            "title": "Mechanical Plan",
            "discipline": "M",
            "revision_code": "0",
            "revision_date": "2026-08-01",
        }
        sheet = self.client.post(
            f"/drawing-sets/{drawing_set['id']}/sheets",
            data={"metadata": json.dumps(metadata)},
            files={
                "file": (
                    "M-201.pdf",
                    searchable_pdf("original air handler AHU-7"),
                    "application/pdf",
                )
            },
            headers=self.owner,
        ).json()
        revision = self.client.post(
            f"/drawing-sheets/{sheet['id']}/revisions",
            data={
                "metadata": json.dumps(
                    {
                        "revision_code": "1",
                        "revision_date": "2026-08-02",
                        "description": "Coordination update",
                    }
                )
            },
            files={
                "file": (
                    "M-201-r1.pdf",
                    searchable_pdf("revised air handler AHU-7"),
                    "application/pdf",
                )
            },
            headers=self.owner,
        ).json()
        self.process()

        current = self.search("AHU-7", scope="drawings").json()["results"]
        history = self.search(
            "AHU-7",
            scope="drawings",
            current_revisions_only="false",
            drawing_set_id=drawing_set["id"],
            discipline="M",
        ).json()["results"]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["drawing_revision_id"], revision["id"])
        self.assertEqual(current[0]["revision_status"], "current")
        self.assertEqual(current[0]["sheet_number"], "M-201")
        self.assertEqual(current[0]["route_target"]["type"], "drawing_revision")
        self.assertEqual(len(history), 2)
        self.assertEqual(
            {item["revision_status"] for item in history},
            {"current", "superseded"},
        )

    def test_search_does_not_return_partial_or_stale_page_rows(self):
        document = self.upload("Pending", "pending searchable phrase").json()
        with self.TestingSession() as db:
            stored = db.get(Document, document["id"])
            stored.checksum_sha256 = "0" * 64
            db.commit()
        self.process()
        self.assertEqual(
            self.search("pending searchable phrase").json()["results"],
            [],
        )
        with self.TestingSession() as db:
            self.assertEqual(db.query(DocumentPageText).count(), 0)
