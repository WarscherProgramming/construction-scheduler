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
PREVIOUS_HEAD = "c8d4f1a7b903"
ADVANCED_REVISION = "d4e8a1c7f925"
CURRENT_REVISION = "b9e5d3f7a201"


class AdvancedSchedulingMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        os.environ["SECRET_KEY"] = "advanced-scheduling-migration-secret"
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

    def test_backfill_constraints_indexes_and_lifecycle(self):
        command.upgrade(self.config, PREVIOUS_HEAD)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'advanced@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Advanced schedule', 1);
                INSERT INTO project_schedule_settings (
                    project_id, schedule_start_date, data_date
                ) VALUES (1, '2026-03-02', '2026-03-02');
                INSERT INTO tasks (
                    id, name, duration, project_id, is_collapsed,
                    dependency_type, lag_days, progress_status,
                    percent_complete, remaining_duration
                ) VALUES
                    (1, 'Existing predecessor', 2, 1, 0, 'FS', 0,
                     'not_started', 0, 2),
                    (2, 'Existing successor', 1, 1, 0, 'SS', 3,
                     'not_started', 0, 1);
                UPDATE tasks SET predecessor_task_id = 1 WHERE id = 2;

                INSERT INTO schedule_templates (id, name, user_id)
                VALUES (1, 'Advanced template', 1);
                INSERT INTO schedule_template_tasks (
                    id, template_id, name, duration,
                    predecessor_template_task_id, dependency_type, lag_days
                ) VALUES
                    (1, 1, 'Template predecessor', 2, NULL, 'FS', 0),
                    (2, 1, 'Template successor', 1, 1, 'SS', 3);

                INSERT INTO schedule_baselines (
                    id, project_id, name, normalized_name, captured_by,
                    schedule_start_date, task_count, status
                ) VALUES (
                    1, 1, 'Existing baseline', 'existing baseline', 1,
                    '2026-03-02', 2, 'active'
                );
                INSERT INTO schedule_baseline_tasks (
                    id, baseline_id, project_id, task_id, name,
                    predecessor_task_id, dependency_type, lag_days,
                    duration, is_summary, was_critical, wbs_path
                ) VALUES
                    (1, 1, 1, 1, 'Existing predecessor', NULL,
                     'FS', 0, 2, 0, 1, '1'),
                    (2, 1, 1, 2, 'Existing successor', 1,
                     'SS', 3, 1, 0, 1, '2');
                """
            )

        command.upgrade(self.config, ADVANCED_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertIn("task_dependencies", tables)
            self.assertIn("schedule_template_task_dependencies", tables)
            self.assertIn("schedule_baseline_task_dependencies", tables)

            task = connection.execute(
                """
                SELECT is_milestone, constraint_type, constraint_date
                FROM tasks WHERE id = 2
                """
            ).fetchone()
            self.assertEqual(task, (0, "ASAP", None))
            self.assertEqual(
                connection.execute(
                    """
                    SELECT project_id, task_id, predecessor_task_id,
                           dependency_type, lag_days
                    FROM task_dependencies
                    """
                ).fetchone(),
                (1, 2, 1, "SS", 3),
            )
            self.assertEqual(
                connection.execute(
                    """
                    SELECT template_id, template_task_id,
                           predecessor_template_task_id,
                           dependency_type, lag_days
                    FROM schedule_template_task_dependencies
                    """
                ).fetchone(),
                (1, 2, 1, "SS", 3),
            )
            self.assertEqual(
                connection.execute(
                    """
                    SELECT baseline_id, project_id, baseline_task_id,
                           task_id, predecessor_task_id,
                           dependency_type, lag_days
                    FROM schedule_baseline_task_dependencies
                    """
                ).fetchone(),
                (1, 1, 2, 2, 1, "SS", 3),
            )

            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(task_dependencies)"
                )
            }
            self.assertIn("ix_task_dependencies_project_task", indexes)
            self.assertIn(
                "ix_task_dependencies_project_predecessor",
                indexes,
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO task_dependencies (
                        project_id, task_id, predecessor_task_id,
                        dependency_type, lag_days
                    ) VALUES (1, 2, 1, 'FF', 0)
                    """
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    UPDATE tasks SET duration = 0, is_milestone = 0
                    WHERE id = 1
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
            self.assertNotIn("task_dependencies", tables)
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(tasks)")
            }
            self.assertNotIn("is_milestone", columns)
            self.assertEqual(
                connection.execute(
                    """
                    SELECT predecessor_task_id, dependency_type, lag_days
                    FROM tasks WHERE id = 2
                    """
                ).fetchone(),
                (1, "SS", 3),
            )

        command.upgrade(self.config, "head")
        command.check(self.config)
        self.assertEqual(
            ScriptDirectory.from_config(self.config).get_heads(),
            [CURRENT_REVISION],
        )


if __name__ == "__main__":
    unittest.main()
