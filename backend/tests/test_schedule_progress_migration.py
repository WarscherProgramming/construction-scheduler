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
PREVIOUS_HEAD = "a2c7e9f4b610"
M17_3_REVISION = "c8d4f1a7b903"
CURRENT_REVISION = "f3d6a8b2c517"


class ScheduleProgressMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        os.environ["SECRET_KEY"] = "schedule-progress-migration-test-secret"
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
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'progress@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Progress project', 1);
                INSERT INTO project_schedule_settings (
                    project_id, schedule_start_date
                ) VALUES (1, '2026-03-02');
                INSERT INTO tasks (
                    id, name, duration, start_date, end_date, project_id,
                    is_collapsed, dependency_type, lag_days
                ) VALUES (
                    1, 'Existing task', 5, '2026-03-02', '2026-03-06',
                    1, 0, 'FS', 0
                );
                INSERT INTO schedule_baselines (
                    id, project_id, name, normalized_name, captured_by,
                    schedule_start_date, task_count, status
                ) VALUES (
                    1, 1, 'Original', 'original', 1,
                    '2026-03-02', 1, 'active'
                );
                INSERT INTO schedule_baseline_tasks (
                    id, baseline_id, project_id, task_id, name,
                    dependency_type, lag_days, duration, start_date,
                    end_date, is_summary, was_critical, wbs_path
                ) VALUES (
                    1, 1, 1, 1, 'Existing task', 'FS', 0, 5,
                    '2026-03-02', '2026-03-06', 0, 1, '1'
                );
                """
            )

        command.upgrade(self.config, M17_3_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            settings = connection.execute(
                """
                SELECT schedule_start_date, data_date
                FROM project_schedule_settings WHERE project_id = 1
                """
            ).fetchone()
            progress = connection.execute(
                """
                SELECT progress_status, percent_complete,
                       actual_start_date, actual_finish_date,
                       remaining_duration, status_updated_at,
                       status_updated_by, start_date, end_date
                FROM tasks WHERE id = 1
                """
            ).fetchone()
            self.assertEqual(settings, ("2026-03-02", "2026-03-02"))
            self.assertEqual(
                progress,
                (
                    "not_started",
                    0,
                    None,
                    None,
                    5,
                    None,
                    None,
                    "2026-03-02",
                    "2026-03-06",
                ),
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM schedule_baselines"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM schedule_baseline_tasks"
                ).fetchone()[0],
                1,
            )

            task_columns = {
                row[1]: row
                for row in connection.execute("PRAGMA table_info(tasks)")
            }
            settings_columns = {
                row[1]: row
                for row in connection.execute(
                    "PRAGMA table_info(project_schedule_settings)"
                )
            }
            task_sql = connection.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type = 'table' AND name = 'tasks'
                """
            ).fetchone()[0]
            task_indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(tasks)")
            }
            task_fks = connection.execute(
                "PRAGMA foreign_key_list(tasks)"
            ).fetchall()

            self.assertEqual(settings_columns["data_date"][3], 1)
            for column in (
                "progress_status",
                "percent_complete",
                "remaining_duration",
            ):
                self.assertEqual(task_columns[column][3], 1)
            for constraint in (
                "ck_tasks_progress_status",
                "ck_tasks_percent_complete_range",
                "ck_tasks_remaining_duration_range",
                "ck_tasks_actual_date_order",
                "ck_tasks_progress_state_consistency",
            ):
                self.assertIn(constraint, task_sql)
            self.assertIn(
                "ix_tasks_project_progress_status",
                task_indexes,
            )
            updater_fk = next(
                row for row in task_fks if row[3] == "status_updated_by"
            )
            self.assertEqual(updater_fk[2], "users")
            self.assertEqual(updater_fk[6].upper(), "SET NULL")

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE project_schedule_settings SET data_date = NULL"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE tasks SET percent_complete = 50 WHERE id = 1"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE tasks SET remaining_duration = 36501 WHERE id = 1"
                )

        command.downgrade(self.config, PREVIOUS_HEAD)
        with closing(sqlite3.connect(self.database_path)) as connection:
            task_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(tasks)")
            }
            settings_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(project_schedule_settings)"
                )
            }
            self.assertNotIn("progress_status", task_columns)
            self.assertNotIn("remaining_duration", task_columns)
            self.assertNotIn("data_date", settings_columns)
            self.assertEqual(
                connection.execute(
                    "SELECT start_date, end_date FROM tasks WHERE id = 1"
                ).fetchone(),
                ("2026-03-02", "2026-03-06"),
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM schedule_baselines"
                ).fetchone()[0],
                1,
            )

        command.upgrade(self.config, "head")
        command.check(self.config)
        heads = ScriptDirectory.from_config(self.config).get_heads()
        self.assertEqual(heads, [CURRENT_REVISION])


if __name__ == "__main__":
    unittest.main()
