from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.commands.process_attachment_cleanup import main as cleanup_main
from app.core.config import (
    DEFAULT_ATTACHMENT_MIME_TYPES,
    AttachmentConfig,
)
from app.db.database import Base
from app.models.attachment import Attachment
from app.models.attachment_cleanup import AttachmentCleanupJob
from app.models.project import Project
from app.models.user import User
from app.services.attachment import delete_attachments_for_project
from app.services.attachment_cleanup import (
    claim_cleanup_jobs,
    enqueue_cleanup_job,
    process_cleanup_job_ids,
    process_cleanup_jobs,
    prune_completed_cleanup_jobs,
    queue_attachments_for_cleanup,
    reconcile_attachment_storage,
)
from app.storage.attachment import (
    AttachmentStorageConfigurationError,
    AttachmentStorageError,
    MemoryAttachmentStorage,
)


class ControlledStorage(MemoryAttachmentStorage):
    def __init__(self):
        super().__init__()
        self.delete_error = None
        self.delete_calls = []

    def delete(self, storage_key):
        self.delete_calls.append(storage_key)
        if self.delete_error:
            raise self.delete_error
        return super().delete(storage_key)


class AttachmentCleanupTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.config = AttachmentConfig(
            storage_provider="memory",
            local_storage_root=Path("unused"),
            max_upload_size=1024,
            upload_chunk_size=8,
            permitted_mime_types=DEFAULT_ATTACHMENT_MIME_TYPES,
            cleanup_batch_size=2,
            cleanup_max_attempts=3,
            cleanup_retry_base_seconds=10,
            cleanup_retry_max_seconds=60,
            cleanup_lease_seconds=30,
            cleanup_retention_days=30,
        )
        self.storage = ControlledStorage()

        with self.Session() as db:
            user = User(
                email="owner@example.com",
                hashed_password="hash",
            )
            db.add(user)
            db.flush()
            first = Project(name="First", user_id=user.id)
            second = Project(name="Second", user_id=user.id)
            db.add_all([first, second])
            db.commit()
            self.project_id = first.id
            self.other_project_id = second.id

    def tearDown(self):
        self.engine.dispose()

    def add_attachment(
        self,
        db,
        *,
        key,
        project_id=None,
        parent_type="project",
        parent_id=None,
    ):
        selected_project = project_id or self.project_id
        attachment = Attachment(
            project_id=selected_project,
            parent_type=parent_type,
            parent_id=parent_id or selected_project,
            original_filename="plans.pdf",
            storage_key=key,
            storage_provider="memory",
            mime_type="application/pdf",
            size_bytes=3,
            uploaded_by=1,
            sha256="0" * 64,
        )
        db.add(attachment)
        db.flush()
        return attachment

    def add_job(
        self,
        db,
        *,
        key,
        provider="memory",
        status="Pending",
        attempt_count=0,
        next_attempt_at=None,
        updated_at=None,
        completed_at=None,
    ):
        job = AttachmentCleanupJob(
            project_id=self.project_id,
            storage_provider=provider,
            storage_key=key,
            status=status,
            attempt_count=attempt_count,
            next_attempt_at=next_attempt_at
            or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
            completed_at=completed_at,
        )
        db.add(job)
        db.flush()
        return job

    def test_queue_is_idempotent_and_metadata_change_is_transactional(self):
        with self.Session() as db:
            attachment = self.add_attachment(db, key="a" * 32)
            db.commit()
            plan = queue_attachments_for_cleanup(db, [attachment])
            self.assertEqual(plan.attachment_count, 1)
            db.rollback()

        with self.Session() as db:
            self.assertEqual(db.query(Attachment).count(), 1)
            self.assertEqual(db.query(AttachmentCleanupJob).count(), 0)
            first = enqueue_cleanup_job(
                db,
                attachment_id=None,
                project_id=self.project_id,
                storage_provider="memory",
                storage_key="b" * 32,
            )
            second = enqueue_cleanup_job(
                db,
                attachment_id=None,
                project_id=self.project_id,
                storage_provider="memory",
                storage_key="b" * 32,
            )
            self.assertEqual(first.id, second.id)
            db.commit()
            self.assertEqual(db.query(AttachmentCleanupJob).count(), 1)

    def test_immediate_cleanup_completes_success_and_missing_object(self):
        with self.Session() as db:
            present = self.add_job(db, key="c" * 32)
            missing = self.add_job(db, key="d" * 32)
            db.commit()
            self.storage.put_stream("c" * 32, [b"content"])

            result = process_cleanup_job_ids(
                db,
                [present.id, missing.id],
                self.storage,
                self.config,
            )

            self.assertEqual(result.claimed, 2)
            self.assertEqual(result.completed, 2)
            jobs = db.query(AttachmentCleanupJob).all()
            self.assertTrue(
                all(job.status == "Completed" for job in jobs)
            )
            self.assertTrue(
                all(job.completed_at is not None for job in jobs)
            )
            self.assertTrue(
                all(job.attempt_count == 1 for job in jobs)
            )

    def test_immediate_cleanup_does_not_use_the_wrong_provider(self):
        with self.Session() as db:
            job = self.add_job(
                db,
                key="u" * 32,
                provider="s3",
            )
            db.commit()

            result = process_cleanup_job_ids(
                db,
                [job.id],
                self.storage,
                self.config,
            )

            self.assertEqual(result.claimed, 0)
            db.refresh(job)
            self.assertEqual(job.status, "Pending")
            self.assertEqual(self.storage.delete_calls, [])

    def test_retryable_and_nonretryable_failures_are_scheduled_safely(self):
        with self.Session() as db:
            retryable = self.add_job(db, key="e" * 32)
            db.commit()
            self.storage.delete_error = AttachmentStorageError(
                "secret endpoint and object key"
            )

            result = process_cleanup_job_ids(
                db,
                [retryable.id],
                self.storage,
                self.config,
            )
            db.refresh(retryable)

            self.assertEqual(result.retryable, 1)
            self.assertEqual(retryable.status, "Pending")
            self.assertEqual(retryable.attempt_count, 1)
            self.assertGreater(
                retryable.next_attempt_at,
                retryable.updated_at,
            )
            self.assertNotIn("secret", retryable.last_error)
            self.assertLessEqual(len(retryable.last_error), 500)

            failed = self.add_job(db, key="f" * 32)
            db.commit()
            self.storage.delete_error = (
                AttachmentStorageConfigurationError(
                    "credential must-not-appear"
                )
            )
            result = process_cleanup_job_ids(
                db,
                [failed.id],
                self.storage,
                self.config,
            )
            db.refresh(failed)

            self.assertEqual(result.failed, 1)
            self.assertEqual(failed.status, "Failed")
            self.assertNotIn("credential", failed.last_error)

            exhausted = self.add_job(
                db,
                key="v" * 32,
                attempt_count=2,
            )
            db.commit()
            self.storage.delete_error = AttachmentStorageError(
                "temporary outage"
            )
            result = process_cleanup_job_ids(
                db,
                [exhausted.id],
                self.storage,
                self.config,
            )
            db.refresh(exhausted)

            self.assertEqual(result.failed, 1)
            self.assertEqual(exhausted.status, "Failed")
            self.assertEqual(exhausted.attempt_count, 3)

    def test_processor_batching_and_failure_isolation(self):
        with self.Session() as db:
            first = self.add_job(
                db,
                key="g" * 32,
                provider="broken",
            )
            second = self.add_job(db, key="h" * 32)
            third = self.add_job(db, key="i" * 32)
            db.commit()
            self.storage.put_stream("h" * 32, [b"content"])

            def resolve(provider):
                if provider == "broken":
                    raise AttachmentStorageConfigurationError(
                        "invalid configuration"
                    )
                return self.storage

            result = process_cleanup_jobs(
                db,
                resolve,
                self.config,
                batch_size=2,
                max_jobs=2,
            )

            self.assertEqual(result.claimed, 2)
            self.assertEqual(result.failed, 1)
            self.assertEqual(result.completed, 1)
            self.assertEqual(
                db.get(AttachmentCleanupJob, first.id).status,
                "Failed",
            )
            self.assertEqual(
                db.get(AttachmentCleanupJob, second.id).status,
                "Completed",
            )
            self.assertEqual(
                db.get(AttachmentCleanupJob, third.id).status,
                "Pending",
            )

    def test_claim_recovers_expired_lease_and_prevents_double_claim(self):
        current_time = datetime.now(timezone.utc)
        with self.Session() as db:
            stale = self.add_job(
                db,
                key="j" * 32,
                status="Processing",
                updated_at=current_time - timedelta(seconds=31),
            )
            db.commit()

            first_claim = claim_cleanup_jobs(
                db,
                batch_size=1,
                lease_seconds=30,
                now=current_time,
            )
            second_claim = claim_cleanup_jobs(
                db,
                batch_size=1,
                lease_seconds=30,
                now=current_time,
            )

            self.assertEqual(first_claim, (stale.id,))
            self.assertEqual(second_claim, ())
            db.refresh(stale)
            self.assertEqual(stale.status, "Processing")
            self.assertEqual(stale.attempt_count, 1)

    def test_project_cleanup_is_bounded_scoped_and_idempotent(self):
        with self.Session() as db:
            first = self.add_attachment(db, key="k" * 32)
            second = self.add_attachment(
                db,
                key="l" * 32,
                parent_type="rfi",
                parent_id=42,
            )
            other = self.add_attachment(
                db,
                key="m" * 32,
                project_id=self.other_project_id,
            )
            db.commit()
            for key in (first.storage_key, second.storage_key):
                self.storage.put_stream(key, [b"content"])

            removed = delete_attachments_for_project(
                db,
                self.storage,
                self.project_id,
                config=self.config,
                batch_size=1,
            )
            repeated = delete_attachments_for_project(
                db,
                self.storage,
                self.project_id,
                config=self.config,
                batch_size=1,
            )

            self.assertEqual(removed, 2)
            self.assertEqual(repeated, 0)
            self.assertIsNotNone(db.get(Attachment, other.id))
            jobs = db.query(AttachmentCleanupJob).all()
            self.assertEqual(len(jobs), 2)
            self.assertTrue(
                all(job.status == "Completed" for job in jobs)
            )

    def test_reconciliation_is_read_only_and_pruning_honors_retention(self):
        current_time = datetime.now(timezone.utc)
        with self.Session() as db:
            present = self.add_attachment(db, key="n" * 32)
            self.add_attachment(db, key="o" * 32)
            pending_present = self.add_job(db, key="p" * 32)
            self.add_job(db, key="q" * 32)
            old = self.add_job(
                db,
                key="r" * 32,
                status="Completed",
                completed_at=current_time - timedelta(days=31),
            )
            retained = self.add_job(
                db,
                key="s" * 32,
                status="Completed",
                completed_at=current_time - timedelta(days=29),
            )
            db.commit()
            old_id = old.id
            retained_id = retained.id
            self.storage.put_stream(present.storage_key, [b"content"])
            self.storage.put_stream(
                pending_present.storage_key,
                [b"content"],
            )
            before = (
                db.query(Attachment).count(),
                db.query(AttachmentCleanupJob).count(),
            )

            report = reconcile_attachment_storage(
                db,
                lambda provider: self.storage,
                self.config,
                now=current_time,
            )
            after = (
                db.query(Attachment).count(),
                db.query(AttachmentCleanupJob).count(),
            )

            self.assertEqual(report.metadata_present, 1)
            self.assertEqual(report.metadata_missing, 1)
            self.assertEqual(report.cleanup_present, 1)
            self.assertEqual(report.cleanup_missing, 1)
            self.assertEqual(report.completed_prunable, 1)
            self.assertEqual(report.completed_retained, 1)
            self.assertEqual(before, after)

            pruned = prune_completed_cleanup_jobs(
                db,
                self.config,
                now=current_time,
            )
            self.assertEqual(pruned, 1)
            self.assertIsNone(db.get(AttachmentCleanupJob, old_id))
            self.assertIsNotNone(
                db.get(AttachmentCleanupJob, retained_id)
            )

    def test_command_returns_success_with_retryable_work(self):
        with self.Session() as db:
            self.add_job(db, key="t" * 32)
            db.commit()
        self.storage.delete_error = AttachmentStorageError(
            "temporary outage"
        )
        output = StringIO()

        with redirect_stdout(output):
            exit_code = cleanup_main(
                [],
                session_factory=self.Session,
                config=self.config,
                storage_resolver=lambda provider: self.storage,
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("retryable=1", output.getvalue())
        self.assertNotIn("t" * 32, output.getvalue())


if __name__ == "__main__":
    unittest.main()
