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
PREVIOUS_REVISION = "c4d8e2f6a1b3"
CURRENT_REVISION = "c1f7b4e28d35"


class SecurityHardeningMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = (
            f"sqlite:///{self.database_path.as_posix()}"
        )

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

    def test_upgrade_normalizes_email_and_quarantines_legacy_templates(self):
        command.upgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, '  Owner@Example.COM  ', 'hash');
                INSERT INTO schedule_templates (id, name)
                VALUES (1, 'Legacy template');
                INSERT INTO schedule_template_tasks (
                    id, template_id, name, duration, dependency_type, lag_days
                ) VALUES (1, 1, 'Preserved task', 1, 'FS', 0);
                """
            )

        command.upgrade(self.config, "head")
        command.check(self.config)

        with closing(sqlite3.connect(self.database_path)) as connection:
            email = connection.execute(
                "SELECT email FROM users WHERE id = 1"
            ).fetchone()[0]
            template = connection.execute(
                "SELECT id, name, user_id FROM schedule_templates"
            ).fetchone()
            task = connection.execute(
                "SELECT name FROM schedule_template_tasks"
            ).fetchone()
            template_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(schedule_templates)"
                )
            }

        self.assertEqual(email, "owner@example.com")
        self.assertEqual(template, (1, "Legacy template", None))
        self.assertEqual(task, ("Preserved task",))
        self.assertIn(
            "ix_schedule_templates_user_id",
            template_indexes,
        )

    def test_upgrade_rejects_canonical_email_collisions_without_changes(self):
        command.upgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES
                    (1, 'Owner@Example.com', 'hash'),
                    (2, ' owner@example.COM ', 'hash');
                """
            )

        with self.assertRaisesRegex(
            RuntimeError,
            "Canonical email collisions",
        ):
            command.upgrade(self.config, "head")

        with closing(sqlite3.connect(self.database_path)) as connection:
            emails = connection.execute(
                "SELECT email FROM users ORDER BY id"
            ).fetchall()
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(schedule_templates)"
                )
            }

        self.assertEqual(
            emails,
            [("Owner@Example.com",), (" owner@example.COM ",)],
        )
        self.assertNotIn("user_id", columns)

    def test_fresh_upgrade_downgrade_reupgrade_and_single_head(self):
        command.upgrade(self.config, "head")
        command.check(self.config)
        command.downgrade(self.config, PREVIOUS_REVISION)

        with closing(sqlite3.connect(self.database_path)) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(schedule_templates)"
                )
            }

        self.assertNotIn("user_id", columns)

        command.upgrade(self.config, "head")
        command.check(self.config)
        heads = ScriptDirectory.from_config(self.config).get_heads()
        self.assertEqual(heads, [CURRENT_REVISION])


if __name__ == "__main__":
    unittest.main()
