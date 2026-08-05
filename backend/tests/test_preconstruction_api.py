from app.api.dependencies import get_preconstruction_config
from app.api.routes_preconstruction import get_preconstruction_provider
from app.core.config import PreconstructionAIConfig
from app.main import app
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.drawing import DrawingRevision, DrawingSet, DrawingSheet
from app.models.user import User
from app.preconstruction.provider import (
    DeterministicFakePreconstructionAIProvider,
    DisabledPreconstructionAIProvider,
)
from tests.test_api import ApiTestCase


def ai_config(*, enabled=True, max_sources=250, max_attempts=3):
    return PreconstructionAIConfig(
        enabled=enabled,
        provider="fake_test" if enabled else "disabled",
        model="fieldflow-fake-v1" if enabled else "disabled",
        max_attempts=max_attempts,
        lease_seconds=60,
        batch_size=5,
        max_sources_per_review=max_sources,
        max_manifest_bytes=262_144,
        max_result_bytes=32_768,
        retry_base_seconds=1,
        retry_max_seconds=8,
        fake_provider_allowed=enabled,
        template_version="preconstruction-foundation-1",
        schema_version="preconstruction-foundation-1",
    )


class PreconstructionTestBase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.config = ai_config()
        self.provider = DeterministicFakePreconstructionAIProvider()
        app.dependency_overrides[get_preconstruction_config] = lambda: self.config
        app.dependency_overrides[get_preconstruction_provider] = lambda: self.provider
        self.owner_headers = self.register_and_login("precon-owner@example.com")
        self.other_headers = self.register_and_login("precon-other@example.com")
        self.project_id = self.create_project(self.owner_headers, "Preconstruction")
        self.foreign_project_id = self.create_project(self.other_headers, "Foreign")
        with self.TestingSession() as db:
            self.owner_id = db.query(User).filter(User.email == "precon-owner@example.com").one().id
            self.other_id = db.query(User).filter(User.email == "precon-other@example.com").one().id

    def create_document(self, *, project_id=None, owner_id=None, name="Plans.pdf", ready=True):
        project_id = project_id or self.project_id
        owner_id = owner_id or self.owner_id
        with self.TestingSession() as db:
            document = Document(
                project_id=project_id,
                original_filename=name,
                display_name=name,
                extension="pdf",
                mime_type="application/pdf",
                size_bytes=100,
                checksum_sha256=(f"{project_id}-{name}".encode().hex() + "0" * 64)[:64],
                storage_provider="memory",
                storage_key=f"projects/{project_id}/{name}",
                uploaded_by=owner_id,
                document_type="Drawing" if "Plan" in name else "General",
                status="Active",
            )
            db.add(document)
            db.flush()
            if ready:
                db.add(DocumentExtraction(
                    project_id=project_id,
                    document_id=document.id,
                    status="completed",
                    extraction_method="embedded_text",
                    page_count=1,
                    pages_processed=1,
                    text_character_count=40,
                    searchable=True,
                    language="eng",
                    extractor_version="test-v1",
                    source_checksum=document.checksum_sha256,
                ))
            db.commit()
            return document.id

    def create_drawing_revision(self):
        document_id = self.create_document(name="Plan A101.pdf")
        with self.TestingSession() as db:
            drawing_set = DrawingSet(
                project_id=self.project_id,
                name="Architectural",
                status="active",
                created_by=self.owner_id,
            )
            db.add(drawing_set)
            db.flush()
            sheet = DrawingSheet(
                project_id=self.project_id,
                drawing_set_id=drawing_set.id,
                sheet_number="A1.01",
                normalized_sheet_number="a1.01",
                title="Floor Plan",
                discipline="A",
                sort_key="a-001",
                status="active",
                created_by=self.owner_id,
            )
            db.add(sheet)
            db.flush()
            revision = DrawingRevision(
                project_id=self.project_id,
                drawing_sheet_id=sheet.id,
                document_id=document_id,
                revision_code="0",
                normalized_revision_code="0",
                revision_date="2026-08-05",
                sequence_number=1,
                is_current=True,
                uploaded_by=self.owner_id,
            )
            db.add(revision)
            db.flush()
            sheet.current_revision_id = revision.id
            db.commit()
            return document_id, revision.id

    def create_review_set(self, name="Bid Review", purpose="bid_scope_review"):
        response = self.client.post(
            f"/projects/{self.project_id}/preconstruction/review-sets",
            json={"name": name, "description": "Controlled review", "purpose": purpose},
            headers=self.owner_headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def add_source(self, review_id, document_id, role, **extra):
        payload = {
            "source_type": "document",
            "document_id": document_id,
            "document_role": role,
            **extra,
        }
        return self.client.post(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review_id}/sources",
            json=payload,
            headers=self.owner_headers,
        )

    def ready_review(self):
        review = self.create_review_set()
        self.add_source(review["id"], self.create_document(name="Requirement.pdf"), "specification")
        self.add_source(review["id"], self.create_document(name="Proposal.pdf"), "proposal")
        return review


class PreconstructionApiTests(PreconstructionTestBase):

    def test_authentication_and_project_ownership_are_enforced(self):
        self.assertEqual(
            self.client.get(f"/projects/{self.project_id}/preconstruction/review-sets").status_code,
            401,
        )
        self.assertEqual(
            self.client.get(
                f"/projects/{self.project_id}/preconstruction/review-sets",
                headers=self.other_headers,
            ).status_code,
            403,
        )

    def test_review_set_crud_archive_duplicate_and_mass_assignment(self):
        review = self.create_review_set(name="  Bid Review  ")
        listing = self.client.get(
            f"/projects/{self.project_id}/preconstruction/review-sets?state=active",
            headers=self.owner_headers,
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["items"][0]["purpose_label"], "Bid Scope Review")
        duplicate = self.client.post(
            f"/projects/{self.project_id}/preconstruction/review-sets",
            json={"name": "bid review", "purpose": "bid_scope_review"},
            headers=self.owner_headers,
        )
        self.assertEqual(duplicate.status_code, 409)
        mass_assignment = self.client.put(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}",
            json={"status": "ready"},
            headers=self.owner_headers,
        )
        self.assertEqual(mass_assignment.status_code, 422)
        updated = self.client.put(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}",
            json={"description": "Updated"},
            headers=self.owner_headers,
        )
        self.assertEqual(updated.status_code, 200)
        archived = self.client.post(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/archive",
            headers=self.owner_headers,
        )
        self.assertEqual(archived.status_code, 200)
        self.assertEqual(archived.json()["status"], "archived")
        self.assertEqual(
            self.client.put(
                f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}",
                json={"description": "No"},
                headers=self.owner_headers,
            ).status_code,
            409,
        )

    def test_document_source_lifecycle_snapshots_and_safe_response(self):
        review = self.create_review_set()
        document_id = self.create_document(name="Specifications.pdf")
        created = self.add_source(
            review["id"], document_id, "specification", discipline="Architectural", trade="General"
        )
        self.assertEqual(created.status_code, 201, created.text)
        source = created.json()
        self.assertEqual(source["role_category"], "requirement")
        self.assertEqual(source["extraction_status"], "completed")
        self.assertEqual(len(source["source_checksum"]), 64)
        self.assertNotIn("storage_key", source)
        duplicate = self.add_source(review["id"], document_id, "drawing")
        self.assertEqual(duplicate.status_code, 409)
        updated = self.client.put(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/sources/{source['id']}",
            json={"document_role": "drawing", "trade": "Electrical"},
            headers=self.owner_headers,
        )
        self.assertEqual(updated.status_code, 200)
        removed = self.client.delete(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/sources/{source['id']}",
            headers=self.owner_headers,
        )
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(
            self.client.get(
                f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/sources",
                headers=self.owner_headers,
            ).json()["items"],
            [],
        )

    def test_drawing_revision_source_requires_matching_backing_document(self):
        review = self.create_review_set(purpose="revision_impact_review")
        document_id, revision_id = self.create_drawing_revision()
        wrong_document = self.create_document(name="Wrong.pdf")
        path = f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/sources"
        mismatch = self.client.post(
            path,
            json={
                "source_type": "drawing_revision",
                "document_id": wrong_document,
                "drawing_revision_id": revision_id,
                "document_role": "drawing",
            },
            headers=self.owner_headers,
        )
        self.assertEqual(mismatch.status_code, 404)
        created = self.client.post(
            path,
            json={
                "source_type": "drawing_revision",
                "document_id": document_id,
                "drawing_revision_id": revision_id,
                "document_role": "drawing",
            },
            headers=self.owner_headers,
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["sheet_number"], "A1.01")

    def test_foreign_deleted_and_missing_sources_are_hidden(self):
        review = self.create_review_set()
        foreign_document = self.create_document(
            project_id=self.foreign_project_id, owner_id=self.other_id, name="Foreign.pdf"
        )
        self.assertEqual(self.add_source(review["id"], foreign_document, "drawing").status_code, 404)
        document_id = self.create_document(name="Deleted.pdf")
        with self.TestingSession() as db:
            document = db.get(Document, document_id)
            from datetime import datetime, timezone
            document.deleted_at = datetime.now(timezone.utc)
            db.commit()
        self.assertEqual(self.add_source(review["id"], document_id, "drawing").status_code, 404)
        self.assertEqual(self.add_source(review["id"], 999999, "drawing").status_code, 404)

    def test_readiness_is_deterministic_and_reports_provider_and_extraction(self):
        review = self.create_review_set()
        pending_id = self.create_document(name="Pending.pdf", ready=False)
        self.add_source(review["id"], pending_id, "specification")
        self.add_source(review["id"], self.create_document(name="Proposal.pdf"), "proposal")
        path = f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/readiness"
        first = self.client.get(path, headers=self.owner_headers).json()
        second = self.client.get(path, headers=self.owner_headers).json()
        self.assertFalse(first["ready"])
        self.assertEqual(first, second)
        self.assertIn("Pending.pdf is not searchable yet.", first["blockers"])
        self.assertEqual(first["requirement_source_count"], 1)
        self.assertEqual(first["coverage_source_count"], 1)
        self.assertTrue(first["provider"]["available"])

    def test_disabled_provider_is_a_factual_readiness_blocker(self):
        app.dependency_overrides[get_preconstruction_config] = lambda: ai_config(enabled=False)
        app.dependency_overrides[get_preconstruction_provider] = DisabledPreconstructionAIProvider
        review = self.ready_review()
        response = self.client.get(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/readiness",
            headers=self.owner_headers,
        )
        self.assertIn("AI provider is disabled.", response.json()["blockers"])
        self.assertFalse(response.json()["provider"]["available"])

    def test_ready_run_pins_manifest_locks_sources_and_is_idempotent(self):
        review = self.ready_review()
        path = f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/runs"
        first = self.client.post(
            path,
            json={"analysis_type": "provider_contract_validation"},
            headers=self.owner_headers,
        )
        self.assertEqual(first.status_code, 201, first.text)
        duplicate = self.client.post(
            path,
            json={"analysis_type": "provider_contract_validation"},
            headers=self.owner_headers,
        )
        self.assertEqual(duplicate.status_code, 201)
        self.assertEqual(first.json()["id"], duplicate.json()["id"])
        sources = self.client.get(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/sources",
            headers=self.owner_headers,
        ).json()["items"]
        self.assertTrue(all(source["locked"] for source in sources))
        self.assertEqual(
            self.client.put(
                f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/sources/{sources[0]['id']}",
                json={"document_role": "drawing"},
                headers=self.owner_headers,
            ).status_code,
            409,
        )
        run = first.json()
        self.assertEqual(len(run["manifest_hash"]), 64)
        self.assertNotIn("manifest_json", run)
        self.assertNotIn("provider_response", run)

    def test_not_ready_run_rejected_and_run_ownership_is_safe(self):
        review = self.create_review_set()
        response = self.client.post(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/runs",
            json={"analysis_type": "provider_contract_validation"},
            headers=self.owner_headers,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            self.client.get(
                f"/projects/{self.project_id}/preconstruction/runs/99999",
                headers=self.owner_headers,
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                f"/projects/{self.project_id}/preconstruction/runs/1",
                headers=self.other_headers,
            ).status_code,
            403,
        )

    def test_cancel_and_retry_rules_are_explicit(self):
        review = self.ready_review()
        run = self.client.post(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/runs",
            json={"analysis_type": "provider_contract_validation"},
            headers=self.owner_headers,
        ).json()
        cancelled = self.client.post(
            f"/projects/{self.project_id}/preconstruction/runs/{run['id']}/cancel",
            headers=self.owner_headers,
        )
        self.assertEqual(cancelled.json()["status"], "cancelled")
        self.assertFalse(cancelled.json()["can_retry"])
        self.assertEqual(
            self.client.post(
                f"/projects/{self.project_id}/preconstruction/runs/{run['id']}/cancel",
                headers=self.owner_headers,
            ).status_code,
            409,
        )

    def test_source_candidates_are_bounded_searchable_and_safe(self):
        self.create_document(name="Electrical Proposal.pdf")
        response = self.client.get(
            f"/projects/{self.project_id}/preconstruction/source-candidates",
            params={"source_type": "document", "search": "Electrical", "limit": 20},
            headers=self.owner_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["items"]), 1)
        self.assertNotIn("storage_key", response.text)
        self.assertNotIn("page_text", response.text)

    def test_source_limit_and_invalid_role_are_rejected(self):
        app.dependency_overrides[get_preconstruction_config] = lambda: ai_config(max_sources=1)
        review = self.create_review_set()
        self.assertEqual(
            self.add_source(review["id"], self.create_document(name="One.pdf"), "drawing").status_code,
            201,
        )
        self.assertEqual(
            self.add_source(review["id"], self.create_document(name="Two.pdf"), "proposal").status_code,
            422,
        )
        invalid = self.client.post(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/sources",
            json={"source_type": "document", "document_id": 1, "document_role": "custom"},
            headers=self.owner_headers,
        )
        self.assertEqual(invalid.status_code, 422)
