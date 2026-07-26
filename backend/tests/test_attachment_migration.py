from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config


BACKEND_DIR = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "f2a8c1d4e6b0"


class AttachmentMigrationTests(unittest.TestCase):
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

    def test_upgrade_preserves_existing_records_and_creates_indexes(self):
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
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(attachments)"
                )
            }
            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(attachments)"
                )
            }

        self.assertEqual(project, (1, "Existing"))
        self.assertIn("storage_key", columns)
        self.assertIn("sha256", columns)
        self.assertIn("ix_attachments_parent_listing", indexes)
        self.assertIn("ix_attachments_id", indexes)

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
        self.assertNotIn("attachments", tables)

        command.upgrade(self.config, "head")
        command.check(self.config)
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertIn("attachments", tables)


if __name__ == "__main__":
    unittest.main()
