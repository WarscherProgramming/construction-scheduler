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
PREVIOUS_REVISION = "d4e8a1c7f925"
LOOK_AHEAD_REVISION = "e6b4c9a2d715"
CURRENT_REVISION = "f3d6a8b2c517"


class LookAheadMigrationTests(unittest.TestCase):
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
            "look-ahead-migration-secret-for-fieldflow-tests"
        )
        self.config = Config(str(BACKEND_DIR / "alembic.ini"))
        self.config.set_main_option(
            "script_location",
            str(BACKEND_DIR / "alembic"),
        )

    def tearDown(self):
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        if self.previous_secret_key is None:
            os.environ.pop("SECRET_KEY", None)
        else:
            os.environ["SECRET_KEY"] = self.previous_secret_key
        self.database_path.unlink(missing_ok=True)

    def test_constraints_indexes_retention_and_lifecycle(self):
        command.upgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'planner@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Look-ahead project', 1);
                INSERT INTO project_schedule_settings (
                    project_id, schedule_start_date, data_date
                ) VALUES (1, '2026-08-03', '2026-08-10');
                INSERT INTO project_companies (id, project_id, name, trade)
                VALUES (1, 1, 'Desert Concrete', 'Concrete');
                INSERT INTO tasks (
                    id, name, duration, project_id, is_collapsed,
                    dependency_type, lag_days, is_milestone,
                    constraint_type, progress_status, percent_complete,
                    remaining_duration
                ) VALUES (
                    1, 'Place concrete', 2, 1, 0, 'FS', 0, 0, 'ASAP',
                    'not_started', 0, 2
                );
                """
            )

        command.upgrade(self.config, LOOK_AHEAD_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertIn("look_ahead_plans", tables)
            self.assertIn("look_ahead_items", tables)
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM look_ahead_plans"
                ).fetchone()[0],
                0,
            )
            plan_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(look_ahead_plans)"
                )
            }
            item_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(look_ahead_items)"
                )
            }
            self.assertIn(
                "ix_look_ahead_plans_project_status_anchor",
                plan_indexes,
            )
            self.assertIn(
                "ix_look_ahead_items_plan_readiness",
                item_indexes,
            )
            item_fks = connection.execute(
                "PRAGMA foreign_key_list(look_ahead_items)"
            ).fetchall()
            self.assertFalse(any(row[3] == "task_id" for row in item_fks))
            company_fk = next(
                row for row in item_fks if row[3] == "responsible_company_id"
            )
            self.assertEqual(company_fk[6].upper(), "SET NULL")

            connection.executescript(
                """
                INSERT INTO look_ahead_plans (
                    id, project_id, name, normalized_name, anchor_date,
                    window_days, status, created_by
                ) VALUES (
                    1, 1, 'Three Week Plan', 'three week plan',
                    '2026-08-10', 21, 'active', 1
                );
                INSERT INTO look_ahead_items (
                    id, project_id, look_ahead_plan_id, task_id,
                    readiness_status, responsible_company_id,
                    manually_included, manually_excluded, created_by
                ) VALUES (
                    1, 1, 1, 1, 'ready', 1, 0, 0, 1
                );
                DELETE FROM tasks WHERE id = 1;
                """
            )
            self.assertEqual(
                connection.execute(
                    "SELECT task_id FROM look_ahead_items"
                ).fetchone(),
                (1,),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE look_ahead_plans SET window_days = 43 WHERE id = 1"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    UPDATE look_ahead_items
                    SET manually_included = 1, manually_excluded = 1
                    WHERE id = 1
                    """
                )

        command.downgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertNotIn("look_ahead_plans", tables)
            self.assertNotIn("look_ahead_items", tables)
            self.assertIn("tasks", tables)

        command.upgrade(self.config, "head")
        command.check(self.config)
        heads = ScriptDirectory.from_config(self.config).get_heads()
        self.assertEqual(heads, [CURRENT_REVISION])


if __name__ == "__main__":
    unittest.main()
