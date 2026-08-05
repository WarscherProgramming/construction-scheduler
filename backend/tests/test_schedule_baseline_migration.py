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
PREVIOUS_HEAD = "f6a1c9d3e742"
M17_2_REVISION = "a2c7e9f4b610"
CURRENT_REVISION = "d4e8a1c7f925"


class ScheduleBaselineMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        os.environ["SECRET_KEY"] = "schedule-baseline-migration-test-secret"
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

    def test_tables_constraints_indexes_pointer_and_lifecycle(self):
        command.upgrade(self.config, PREVIOUS_HEAD)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'baseline@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Baseline project', 1);
                INSERT INTO project_schedule_settings (
                    project_id, schedule_start_date
                ) VALUES (1, '2026-03-02');
                INSERT INTO tasks (
                    id, name, duration, project_id, is_collapsed,
                    dependency_type, lag_days
                ) VALUES (1, 'Existing task', 1, 1, 0, 'FS', 0);
                """
            )

        command.upgrade(self.config, M17_2_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertIn("schedule_baselines", tables)
            self.assertIn("schedule_baseline_tasks", tables)
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM schedule_baselines"
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT start_date, end_date FROM tasks WHERE id = 1"
                ).fetchone(),
                (None, None),
            )

            settings_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(project_schedule_settings)"
                )
            }
            self.assertIn("comparison_baseline_id", settings_columns)
            settings_fks = connection.execute(
                "PRAGMA foreign_key_list(project_schedule_settings)"
            ).fetchall()
            comparison_fk = next(
                row for row in settings_fks if row[3] == "comparison_baseline_id"
            )
            self.assertEqual(comparison_fk[2], "schedule_baselines")
            self.assertEqual(comparison_fk[6].upper(), "SET NULL")

            baseline_sql = connection.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type = 'table' AND name = 'schedule_baselines'
                """
            ).fetchone()[0]
            task_sql = connection.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type = 'table' AND name = 'schedule_baseline_tasks'
                """
            ).fetchone()[0]
            for constraint in (
                "ck_schedule_baselines_name_nonblank",
                "ck_schedule_baselines_status",
                "ck_schedule_baselines_task_count_nonnegative",
                "uq_schedule_baselines_project_normalized_name",
            ):
                self.assertIn(constraint, baseline_sql)
            for constraint in (
                "ck_schedule_baseline_tasks_task_id_positive",
                "ck_schedule_baseline_tasks_duration_range",
                "ck_schedule_baseline_tasks_lag_range",
                "ck_schedule_baseline_tasks_dependency_type",
                "ck_schedule_baseline_tasks_order_nonnegative",
                "ck_schedule_baseline_tasks_float_nonnegative",
                "uq_schedule_baseline_tasks_baseline_task",
            ):
                self.assertIn(constraint, task_sql)

            baseline_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(schedule_baselines)"
                )
            }
            task_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(schedule_baseline_tasks)"
                )
            }
            settings_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(project_schedule_settings)"
                )
            }
            self.assertTrue(
                {
                    "ix_schedule_baselines_project_captured",
                    "ix_schedule_baselines_project_status",
                }.issubset(baseline_indexes)
            )
            self.assertTrue(
                {
                    "ix_schedule_baseline_tasks_baseline_order",
                    "ix_schedule_baseline_tasks_baseline_parent",
                    "ix_schedule_baseline_tasks_baseline_predecessor",
                }.issubset(task_indexes)
            )
            self.assertIn(
                "ix_project_schedule_settings_comparison_baseline",
                settings_indexes,
            )

            connection.executescript(
                """
                INSERT INTO schedule_baselines (
                    id, project_id, name, normalized_name, captured_by,
                    schedule_start_date, task_count, status
                ) VALUES (
                    1, 1, 'Initial', 'initial', 1,
                    '2026-03-02', 1, 'active'
                );
                INSERT INTO schedule_baseline_tasks (
                    id, baseline_id, project_id, task_id, name,
                    dependency_type, lag_days, duration, is_summary,
                    was_critical, wbs_path
                ) VALUES (
                    1, 1, 1, 1, 'Existing task',
                    'FS', 0, 1, 0, 1, '1'
                );
                UPDATE project_schedule_settings
                SET comparison_baseline_id = 1 WHERE project_id = 1;
                DELETE FROM schedule_baselines WHERE id = 1;
                """
            )
            self.assertIsNone(
                connection.execute(
                    """
                    SELECT comparison_baseline_id
                    FROM project_schedule_settings WHERE project_id = 1
                    """
                ).fetchone()[0]
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM schedule_baseline_tasks"
                ).fetchone()[0],
                0,
            )

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO schedule_baselines (
                        project_id, name, normalized_name, captured_by,
                        schedule_start_date, task_count, status
                    ) VALUES (1, '', '', 1, '2026-03-02', 0, 'active')
                    """
                )

        command.downgrade(self.config, PREVIOUS_HEAD)
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertNotIn("schedule_baselines", tables)
            self.assertNotIn("schedule_baseline_tasks", tables)
            settings_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(project_schedule_settings)"
                )
            }
            self.assertNotIn("comparison_baseline_id", settings_columns)

        command.upgrade(self.config, "head")
        command.check(self.config)
        heads = ScriptDirectory.from_config(self.config).get_heads()
        self.assertEqual(heads, [CURRENT_REVISION])


if __name__ == "__main__":
    unittest.main()
