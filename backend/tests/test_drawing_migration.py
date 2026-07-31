from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config


BACKEND_DIR = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "a6d3e9f1b742"


class DrawingMigrationTests(unittest.TestCase):
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
            "script_location", str(BACKEND_DIR / "alembic")
        )

    def tearDown(self):
        from app.db.database import engine

        engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.database_path.unlink(missing_ok=True)

    def test_upgrade_from_document_foundation_preserves_existing_data(self):
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
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            project = connection.execute(
                "SELECT id, name FROM projects"
            ).fetchone()
            revision_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(drawing_revisions)"
                )
            }
        self.assertEqual(project, (1, "Existing"))
        self.assertTrue(
            {
                "drawing_sets",
                "drawing_sheets",
                "drawing_revisions",
                "drawing_issues",
                "drawing_issue_revisions",
            }.issubset(tables)
        )
        self.assertIn(
            "uq_drawing_revisions_current_sheet", revision_indexes
        )

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
        self.assertNotIn("drawing_sets", tables)
        self.assertIn("documents", tables)

        command.upgrade(self.config, "head")
        command.check(self.config)
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertIn("drawing_revisions", tables)


if __name__ == "__main__":
    unittest.main()
