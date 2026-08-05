from datetime import datetime, timedelta, timezone
import json
from time import perf_counter
from unittest.mock import patch

from sqlalchemy import event

from app.core.config import PreconstructionAIConfig
from app.models.preconstruction import (
    PreconstructionAnalysisAttempt,
    PreconstructionAnalysisRun,
    PreconstructionReviewSource,
)
from app.preconstruction.factory import build_preconstruction_provider
from app.preconstruction.provider import (
    DeterministicFakePreconstructionAIProvider,
    DisabledPreconstructionAIProvider,
    ProviderError,
    ProviderRequest,
    ProviderResult,
)
from app.services.preconstruction import (
    canonical_manifest,
    claim_analysis_attempt,
    create_analysis_run,
    process_analysis_attempts,
    recover_expired_attempts,
    review_readiness,
)
from app.schemas.preconstruction import AnalysisRunCreate
from tests.test_preconstruction_api import PreconstructionTestBase, ai_config


class PreconstructionProviderTests(PreconstructionTestBase):
    def make_run(self, *, name="Worker Review"):
        review = self.create_review_set(name=name)
        self.add_source(review["id"], self.create_document(name=f"{name} Requirements.pdf"), "specification")
        self.add_source(review["id"], self.create_document(name=f"{name} Proposal.pdf"), "proposal")
        response = self.client.post(
            f"/projects/{self.project_id}/preconstruction/review-sets/{review['id']}/runs",
            json={"analysis_type": "provider_contract_validation"},
            headers=self.owner_headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def process_run(self, run, provider, config=None):
        with self.TestingSession() as db:
            return process_analysis_attempts(
                db,
                provider,
                config or self.config,
                max_jobs=1,
                run_id=run["id"],
            )

    def stored_run(self, run_id):
        with self.TestingSession() as db:
            return db.get(PreconstructionAnalysisRun, run_id)

    def test_disabled_and_fake_provider_contracts(self):
        request = ProviderRequest(
            manifest_hash="a" * 64,
            analysis_type="provider_contract_validation",
            provider_profile="fake_test",
            template_version="v1",
            schema_version="v1",
            sources=(),
        )
        disabled = DisabledPreconstructionAIProvider()
        self.assertFalse(disabled.available)
        with self.assertRaises(ProviderError) as context:
            disabled.execute(request)
        self.assertEqual(context.exception.code, "provider_disabled")
        result = DeterministicFakePreconstructionAIProvider().execute(request)
        self.assertIsInstance(result, ProviderResult)
        self.assertEqual(result.payload["manifest_hash"], "a" * 64)

    def test_provider_factory_is_allowlisted_and_rejects_fake_in_production(self):
        self.assertIsInstance(
            build_preconstruction_provider(ai_config(enabled=False)),
            DisabledPreconstructionAIProvider,
        )
        with patch("app.preconstruction.factory.APP_ENV", "production"):
            with self.assertRaises(RuntimeError):
                build_preconstruction_provider(ai_config())
        unknown = PreconstructionAIConfig(
            **{**ai_config().__dict__, "provider": "unknown"}
        )
        with self.assertRaises(RuntimeError):
            build_preconstruction_provider(unknown)

    def test_worker_success_and_warning_complete_safe_summaries(self):
        for mode, expected in (("success", "completed"), ("warning", "completed_with_warnings")):
            with self.subTest(mode=mode):
                run = self.make_run(name=f"Worker {mode}")
                result = self.process_run(run, DeterministicFakePreconstructionAIProvider(mode))
                self.assertEqual(result.claimed, 1)
                stored = self.stored_run(run["id"])
                self.assertEqual(stored.status, expected)
                summary = json.loads(stored.result_summary_json)
                self.assertEqual(summary["payload"]["manifest_hash"], stored.manifest_hash)
                self.assertNotIn("reasoning", summary)
                self.assertNotIn("prompt", summary)

    def test_retryable_failure_schedules_bounded_retry(self):
        run = self.make_run(name="Retryable")
        result = self.process_run(
            run, DeterministicFakePreconstructionAIProvider("retryable_failure")
        )
        self.assertEqual(result.retryable, 1)
        with self.TestingSession() as db:
            stored = db.get(PreconstructionAnalysisRun, run["id"])
            attempts = db.query(PreconstructionAnalysisAttempt).filter_by(run_id=run["id"]).all()
            self.assertEqual(stored.status, "pending")
            self.assertEqual(stored.current_attempt_count, 2)
            self.assertEqual([attempt.status for attempt in attempts], ["failed", "pending"])

    def test_permanent_malformed_and_timeout_failures_are_classified(self):
        cases = (
            ("permanent_failure", "failed", "provider_rejected_request"),
            ("malformed", "failed", "invalid_provider_result"),
            ("timeout", "pending", None),
        )
        for mode, expected_status, expected_code in cases:
            with self.subTest(mode=mode):
                run = self.make_run(name=f"Failure {mode}")
                self.process_run(run, DeterministicFakePreconstructionAIProvider(mode))
                stored = self.stored_run(run["id"])
                self.assertEqual(stored.status, expected_status)
                self.assertEqual(stored.failure_code, expected_code)

    def test_max_attempts_stops_retryable_failure(self):
        limited = ai_config(max_attempts=1)
        self.config = limited
        from app.api.dependencies import get_preconstruction_config
        from app.main import app
        app.dependency_overrides[get_preconstruction_config] = lambda: limited
        run = self.make_run(name="Maximum")
        result = self.process_run(
            run,
            DeterministicFakePreconstructionAIProvider("retryable_failure"),
            limited,
        )
        self.assertEqual(result.failed, 1)
        self.assertEqual(self.stored_run(run["id"]).status, "failed")

    def test_claim_is_atomic_and_cancelled_work_is_not_executed(self):
        run = self.make_run(name="Claim")
        with self.TestingSession() as first_db:
            first = claim_analysis_attempt(first_db, run_id=run["id"], lease_seconds=60)
            self.assertIsNotNone(first)
        with self.TestingSession() as second_db:
            second = claim_analysis_attempt(second_db, run_id=run["id"], lease_seconds=60)
            self.assertIsNone(second)

        cancelled = self.client.post(
            f"/projects/{self.project_id}/preconstruction/runs/{run['id']}/cancel",
            headers=self.owner_headers,
        )
        self.assertEqual(cancelled.status_code, 200)
        result = self.process_run(run, DeterministicFakePreconstructionAIProvider())
        self.assertEqual(result.claimed, 0)

    def test_expired_lease_is_recovered_with_append_only_attempt(self):
        run = self.make_run(name="Expired Lease")
        with self.TestingSession() as db:
            attempt = db.query(PreconstructionAnalysisAttempt).filter_by(run_id=run["id"]).one()
            attempt.status = "processing"
            attempt.lease_token = "expired-token"
            attempt.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            stored = db.get(PreconstructionAnalysisRun, run["id"])
            stored.status = "processing"
            db.commit()
        with self.TestingSession() as db:
            self.assertEqual(recover_expired_attempts(db, self.config), 1)
            attempts = db.query(PreconstructionAnalysisAttempt).filter_by(run_id=run["id"]).order_by(PreconstructionAnalysisAttempt.attempt_number).all()
            self.assertEqual([attempt.status for attempt in attempts], ["failed", "pending"])
            self.assertEqual(attempts[0].failure_code, "lease_expired")

    def test_manifest_serialization_is_stable_and_bounded(self):
        first_payload = {"sources": [{"id": 2}, {"id": 1}], "review_set_id": 4}
        second_payload = {"review_set_id": 4, "sources": [{"id": 2}, {"id": 1}]}
        first_json, first_hash = canonical_manifest(first_payload, 1000)
        second_json, second_hash = canonical_manifest(second_payload, 1000)
        self.assertEqual(first_json, second_json)
        self.assertEqual(first_hash, second_hash)
        self.assertNotIn("page_text", first_json)
        with self.assertRaises(Exception):
            canonical_manifest({"large": "x" * 100}, 20)

    def test_readiness_and_manifest_scale_to_configured_source_limit(self):
        from app.models.document import Document
        from app.models.document_extraction import DocumentExtraction
        from app.models.preconstruction import PreconstructionReviewSet

        for count in (10, 100, 250):
            with self.subTest(source_count=count):
                review = self.create_review_set(
                    name=f"Scale {count}", purpose="general_scope_review"
                )
                with self.TestingSession() as db:
                    review_row = db.get(PreconstructionReviewSet, review["id"])
                    for index in range(count):
                        checksum = f"{index:064x}"
                        document = Document(
                            project_id=self.project_id,
                            original_filename=f"scale-{count}-{index}.pdf",
                            display_name=f"Scale {count} {index}",
                            extension="pdf",
                            mime_type="application/pdf",
                            size_bytes=1,
                            checksum_sha256=checksum,
                            storage_provider="memory",
                            storage_key=f"scale/{count}/{index}",
                            uploaded_by=self.owner_id,
                            document_type="General",
                            status="Active",
                        )
                        db.add(document)
                        db.flush()
                        extraction = DocumentExtraction(
                            project_id=self.project_id,
                            document_id=document.id,
                            status="completed",
                            extraction_method="embedded_text",
                            page_count=1,
                            pages_processed=1,
                            text_character_count=1,
                            searchable=True,
                            language="eng",
                            extractor_version="test-v1",
                            source_checksum=checksum,
                        )
                        db.add(extraction)
                        db.flush()
                        db.add(PreconstructionReviewSource(
                            project_id=self.project_id,
                            review_set_id=review_row.id,
                            source_type="document",
                            document_id=document.id,
                            document_role="specification" if index == 0 else "proposal",
                            source_checksum=checksum,
                            extraction_id=extraction.id,
                            extraction_version="test-v1",
                            extraction_status="completed",
                            display_name_snapshot=document.display_name,
                            added_by=self.owner_id,
                        ))
                    db.commit()
                    # Resolve expired ORM attributes before query counting.
                    review_row.id
                    review_row.project_id
                    review_row.purpose
                    review_row.status
                    query_count = 0

                    def count_query(*args):
                        nonlocal query_count
                        query_count += 1

                    event.listen(self.engine, "before_cursor_execute", count_query)
                    readiness_started = perf_counter()
                    readiness = review_readiness(db, review_row, self.config, self.provider)
                    readiness_elapsed = perf_counter() - readiness_started
                    readiness_queries = query_count
                    self.assertTrue(readiness["ready"])
                    self.assertEqual(readiness["source_count"], count)
                    self.assertLessEqual(readiness_queries, 5)
                    self.assertLess(len(json.dumps(readiness).encode("utf-8")), 16_384)

                    query_count = 0
                    run_started = perf_counter()
                    run = create_analysis_run(
                        db,
                        review_row,
                        self.owner_id,
                        AnalysisRunCreate(
                            analysis_type="provider_contract_validation"
                        ),
                        self.config,
                        self.provider,
                    )
                    run_elapsed = perf_counter() - run_started
                    run_queries = query_count
                    event.remove(self.engine, "before_cursor_execute", count_query)
                    self.assertEqual(run.source_count, count)
                    self.assertLessEqual(run_queries, 15)
                    manifest_bytes = len(run.manifest_json.encode("utf-8"))
                    self.assertLessEqual(manifest_bytes, self.config.max_manifest_bytes)
                    print(
                        "preconstruction-scale "
                        f"sources={count} readiness_queries={readiness_queries} "
                        f"readiness_ms={readiness_elapsed * 1000:.2f} "
                        f"run_queries={run_queries} run_ms={run_elapsed * 1000:.2f} "
                        f"manifest_bytes={manifest_bytes}"
                    )
