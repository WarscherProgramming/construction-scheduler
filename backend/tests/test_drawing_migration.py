from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


BACKEND_DIR = Path(__file__).resolve().parents[1]
DOCUMENT_FOUNDATION_REVISION = "a6d3e9f1b742"
DRAWING_MANAGEMENT_REVISION = "b7e4f2a9c631"
CURRENT_REVISION = "d4e8a1c7f925"
MEMBERSHIP_UNIQUE_NAME = "uq_drawing_issue_revisions_membership"


class DrawingMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        os.environ["SECRET_KEY"] = (
            "drawing-migration-test-secret-key-123456"
        )
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
        if self.previous_secret_key is None:
            os.environ.pop("SECRET_KEY", None)
        else:
            os.environ["SECRET_KEY"] = self.previous_secret_key
        self.database_path.unlink(missing_ok=True)

    def membership_constraint_state(self):
        engine = create_engine(f"sqlite:///{self.database_path.as_posix()}")
        try:
            inspector = inspect(engine)
            primary_key = inspector.get_pk_constraint(
                "drawing_issue_revisions"
            )
            unique_names = {
                constraint["name"]
                for constraint in inspector.get_unique_constraints(
                    "drawing_issue_revisions"
                )
            }
            return primary_key, unique_names
        finally:
            engine.dispose()

    @staticmethod
    def unrelated_schema(connection):
        return connection.execute(
            """
            SELECT type, name, tbl_name, sql
            FROM sqlite_master
            WHERE tbl_name NOT IN (
                'alembic_version',
                'drawing_issue_revisions',
                'entity_relationships',
                'document_extractions',
                'document_page_texts',
                'document_extraction_jobs',
                'project_schedule_settings',
                'schedule_baselines',
                'schedule_baseline_tasks',
                'schedule_baseline_task_dependencies',
                'schedule_template_tasks',
                'schedule_template_task_dependencies',
                'task_dependencies',
                'tasks'
            )
              AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        ).fetchall()

    def test_upgrade_from_document_foundation_preserves_existing_data(self):
        command.upgrade(self.config, DOCUMENT_FOUNDATION_REVISION)
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

    def test_membership_constraint_correction_preserves_data(self):
        command.upgrade(self.config, DRAWING_MANAGEMENT_REVISION)
        primary_key, unique_names = self.membership_constraint_state()
        self.assertEqual(
            primary_key["constrained_columns"],
            ["drawing_issue_id", "drawing_revision_id"],
        )
        self.assertIn(MEMBERSHIP_UNIQUE_NAME, unique_names)

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executemany(
                """
                INSERT INTO drawing_issue_revisions (
                    drawing_issue_id,
                    drawing_revision_id
                ) VALUES (?, ?)
                """,
                [(101, 201), (101, 202)],
            )
            connection.commit()
            schema_before = self.unrelated_schema(connection)

        command.upgrade(self.config, "head")
        command.check(self.config)
        primary_key, unique_names = self.membership_constraint_state()
        self.assertEqual(
            primary_key["constrained_columns"],
            ["drawing_issue_id", "drawing_revision_id"],
        )
        self.assertNotIn(MEMBERSHIP_UNIQUE_NAME, unique_names)

        with closing(sqlite3.connect(self.database_path)) as connection:
            memberships = connection.execute(
                """
                SELECT drawing_issue_id, drawing_revision_id
                FROM drawing_issue_revisions
                ORDER BY drawing_issue_id, drawing_revision_id
                """
            ).fetchall()
            self.assertEqual(memberships, [(101, 201), (101, 202)])
            self.assertEqual(
                schema_before,
                self.unrelated_schema(connection),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO drawing_issue_revisions (
                        drawing_issue_id,
                        drawing_revision_id
                    ) VALUES (101, 201)
                    """
                )
            connection.rollback()
            connection.execute(
                """
                INSERT INTO drawing_issue_revisions (
                    drawing_issue_id,
                    drawing_revision_id
                ) VALUES (102, 201)
                """
            )
            connection.commit()

        command.downgrade(self.config, DRAWING_MANAGEMENT_REVISION)
        primary_key, unique_names = self.membership_constraint_state()
        self.assertEqual(
            primary_key["constrained_columns"],
            ["drawing_issue_id", "drawing_revision_id"],
        )
        self.assertIn(MEMBERSHIP_UNIQUE_NAME, unique_names)

        command.upgrade(self.config, "head")
        command.check(self.config)
        _, unique_names = self.membership_constraint_state()
        self.assertNotIn(MEMBERSHIP_UNIQUE_NAME, unique_names)
        with closing(sqlite3.connect(self.database_path)) as connection:
            memberships = connection.execute(
                """
                SELECT drawing_issue_id, drawing_revision_id
                FROM drawing_issue_revisions
                ORDER BY drawing_issue_id, drawing_revision_id
                """
            ).fetchall()
        self.assertEqual(
            memberships,
            [(101, 201), (101, 202), (102, 201)],
        )

    def test_fresh_upgrade_downgrade_and_reupgrade(self):
        command.upgrade(self.config, "head")
        command.check(self.config)
        with closing(sqlite3.connect(self.database_path)) as connection:
            current_revision = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()
        self.assertEqual(current_revision, (CURRENT_REVISION,))
        _, unique_names = self.membership_constraint_state()
        self.assertNotIn(MEMBERSHIP_UNIQUE_NAME, unique_names)

        command.downgrade(self.config, DOCUMENT_FOUNDATION_REVISION)
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
