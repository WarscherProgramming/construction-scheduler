from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


BACKEND_DIR = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "b3c9d7e1f5a2"
CURRENT_REVISION = "c1f7b4e28d35"


class AttachmentCleanupMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        os.environ.setdefault("SECRET_KEY", "migration-test-secret")

        self.config = Config(str(BACKEND_DIR / "alembic.ini"))
        self.config.set_main_option(
            "script_location",
            str(BACKEND_DIR / "alembic"),
        )

    def tearDown(self):
        from app.db.database import engine

        engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.database_path.unlink(missing_ok=True)

    def test_upgrade_preserves_attachments_and_creates_queue_contract(self):
        command.upgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'owner@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Existing', 1);
                INSERT INTO attachments (
                    id,
                    project_id,
                    parent_type,
                    parent_id,
                    original_filename,
                    storage_key,
                    storage_provider,
                    mime_type,
                    size_bytes,
                    uploaded_by,
                    sha256
                )
                VALUES (
                    1,
                    1,
                    'project',
                    1,
                    'plans.pdf',
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    'local',
                    'application/pdf',
                    10,
                    1,
                    '0000000000000000000000000000000000000000000000000000000000000000'
                );
                """
            )

        command.upgrade(self.config, "head")
        command.check(self.config)

        with closing(sqlite3.connect(self.database_path)) as connection:
            attachment = connection.execute(
                "SELECT id, storage_key FROM attachments"
            ).fetchone()
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(attachment_cleanup_jobs)"
                )
            }
            indexes = {
                row[1]: row[2]
                for row in connection.execute(
                    "PRAGMA index_list(attachment_cleanup_jobs)"
                )
            }
            unique_index_sql = connection.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type = 'index'
                  AND name = 'uq_attachment_cleanup_jobs_active_object'
                """
            ).fetchone()[0]

        self.assertEqual(
            attachment,
            (1, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
        )
        self.assertTrue(
            {
                "attachment_id",
                "project_id",
                "storage_provider",
                "storage_key",
                "operation",
                "status",
                "attempt_count",
                "last_error",
                "next_attempt_at",
                "created_at",
                "updated_at",
                "completed_at",
            }.issubset(columns)
        )
        self.assertIn("ix_attachment_cleanup_jobs_pending", indexes)
        self.assertIn("ix_attachment_cleanup_jobs_lease", indexes)
        self.assertEqual(
            indexes["uq_attachment_cleanup_jobs_active_object"],
            1,
        )
        self.assertIn("WHERE status IN", unique_index_sql)

    def test_fresh_upgrade_downgrade_reupgrade_and_single_head(self):
        command.upgrade(self.config, "head")
        command.check(self.config)
        self.assertEqual(
            ScriptDirectory.from_config(self.config).get_heads(),
            [CURRENT_REVISION],
        )

        command.downgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertNotIn("attachment_cleanup_jobs", tables)
        self.assertIn("attachments", tables)

        command.upgrade(self.config, "head")
        command.check(self.config)
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertIn("attachment_cleanup_jobs", tables)


if __name__ == "__main__":
    unittest.main()
