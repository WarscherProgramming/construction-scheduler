from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config


BACKEND_DIR = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "f8c2d6e0a315"


class DocumentMigrationTests(unittest.TestCase):
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

    def test_current_head_upgrade_preserves_data_and_creates_schema(self):
        command.upgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'owner@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Existing', 1);
                """
            )

        command.upgrade(self.config, "head")
        command.check(self.config)

        with closing(sqlite3.connect(self.database_path)) as connection:
            project = connection.execute(
                "SELECT id, name FROM projects"
            ).fetchone()
            document_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(documents)"
                )
            }
            document_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(documents)"
                )
            }
            folder_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(folders)"
                )
            }

        self.assertEqual(project, (1, "Existing"))
        self.assertTrue(
            {
                "checksum_sha256",
                "storage_key",
                "parent_document_id",
                "version",
                "is_current_version",
                "deleted_at",
            }.issubset(document_columns)
        )
        self.assertIn("ix_documents_project_listing", document_indexes)
        self.assertIn("ix_documents_version_lineage", document_indexes)
        self.assertIn("uq_folders_active_root_name", folder_indexes)
        self.assertIn("uq_folders_active_child_name", folder_indexes)

    def test_fresh_upgrade_downgrade_and_reupgrade(self):
        command.upgrade(self.config, "head")
        command.check(self.config)
        command.downgrade(self.config, PREVIOUS_REVISION)

        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertNotIn("documents", tables)
        self.assertNotIn("folders", tables)

        command.upgrade(self.config, "head")
        command.check(self.config)
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertIn("documents", tables)
        self.assertIn("folders", tables)


if __name__ == "__main__":
    unittest.main()
