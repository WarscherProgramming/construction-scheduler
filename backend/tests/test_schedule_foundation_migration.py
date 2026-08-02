from contextlib import closing
from datetime import date
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config


BACKEND_DIR = Path(__file__).resolve().parents[1]
PREVIOUS_HEAD = "e4b7c2d9f651"
M17_1_REVISION = "f6a1c9d3e742"


class ScheduleFoundationMigrationTests(unittest.TestCase):
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
            "schedule-foundation-migration-test-secret-key"
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
        if self.previous_secret_key is None:
            os.environ.pop("SECRET_KEY", None)
        else:
            os.environ["SECRET_KEY"] = self.previous_secret_key
        self.database_path.unlink(missing_ok=True)

    def test_backfill_constraints_indexes_and_lifecycle(self):
        command.upgrade(self.config, PREVIOUS_HEAD)

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'scheduler@example.com', 'hash');

                INSERT INTO projects (id, name, user_id) VALUES
                    (1, 'Root date', 1),
                    (2, 'No tasks', 1),
                    (3, 'Summary date excluded', 1);

                INSERT INTO tasks (
                    id, name, duration, start_date, end_date,
                    manual_start_date, project_id, order_index,
                    parent_task_id, is_collapsed, predecessor_task_id,
                    dependency_type, lag_days
                ) VALUES
                    (10, 'Legacy zero', 0, '2026-03-02', '2026-03-02',
                     NULL, 1, 1, NULL, 0, NULL, 'FS', 0),
                    (20, 'Summary', 1, '2026-01-05', '2026-02-02',
                     NULL, 3, 1, NULL, 0, NULL, 'FS', 0),
                    (21, 'Child', 1, '2026-02-02', '2026-02-02',
                     NULL, 3, 2, 20, 0, NULL, 'FS', 0);
                """
            )

        command.upgrade(self.config, M17_1_REVISION)

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            settings = connection.execute(
                """
                SELECT project_id, schedule_start_date
                FROM project_schedule_settings
                ORDER BY project_id
                """
            ).fetchall()
            task_columns = {
                row[1]: row
                for row in connection.execute("PRAGMA table_info(tasks)")
            }
            check_sql = connection.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type = 'table' AND name = 'tasks'
                """
            ).fetchone()[0]
            indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(tasks)")
            }
            duration = connection.execute(
                "SELECT duration FROM tasks WHERE id = 10"
            ).fetchone()[0]

            self.assertEqual(settings[0], (1, "2026-03-02"))
            date.fromisoformat(settings[1][1])
            self.assertEqual(settings[2], (3, "2026-02-02"))
            self.assertEqual(duration, 1)
            self.assertEqual(task_columns["duration"][3], 1)
            self.assertEqual(task_columns["is_collapsed"][3], 1)
            for constraint in (
                "ck_tasks_duration_range",
                "ck_tasks_lag_days_range",
                "ck_tasks_dependency_type",
                "ck_tasks_order_index_nonnegative",
                "ck_tasks_is_collapsed",
                "ck_tasks_not_own_predecessor",
                "ck_tasks_not_own_parent",
            ):
                self.assertIn(constraint, check_sql)
            self.assertTrue(
                {
                    "ix_tasks_project_order_id",
                    "ix_tasks_project_predecessor",
                    "ix_tasks_project_parent",
                }.issubset(indexes)
            )

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO tasks (
                        id, name, duration, project_id, is_collapsed,
                        dependency_type, lag_days
                    ) VALUES (99, 'Invalid', 0, 1, 0, 'FS', 0)
                    """
                )

            connection.execute("DELETE FROM projects WHERE id = 2")
            self.assertIsNone(
                connection.execute(
                    """
                    SELECT project_id FROM project_schedule_settings
                    WHERE project_id = 2
                    """
                ).fetchone()
            )

        command.downgrade(self.config, PREVIOUS_HEAD)
        with closing(sqlite3.connect(self.database_path)) as connection:
            self.assertIsNone(
                connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table'
                      AND name = 'project_schedule_settings'
                    """
                ).fetchone()
            )

        command.upgrade(self.config, "head")
        command.check(self.config)


if __name__ == "__main__":
    unittest.main()
