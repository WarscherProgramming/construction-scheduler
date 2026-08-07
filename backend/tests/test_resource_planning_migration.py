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
PREVIOUS_REVISION = "e6b4c9a2d715"
CURRENT_REVISION = "d5a3f9c14e28"


class ResourcePlanningMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path.as_posix()}"
        os.environ["SECRET_KEY"] = "resource-planning-migration-test-secret"
        self.config = Config(str(BACKEND_DIR / "alembic.ini"))
        self.config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

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

    def test_tables_constraints_indexes_and_lifecycle(self):
        command.upgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'planner@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Resource project', 1);
                INSERT INTO project_schedule_settings (
                    project_id, schedule_start_date, data_date
                ) VALUES (1, '2026-08-03', '2026-08-10');
                INSERT INTO project_companies (id, project_id, name, trade)
                VALUES (1, 1, 'Desert Electric', 'Electrical');
                INSERT INTO tasks (
                    id, name, duration, project_id, is_collapsed,
                    dependency_type, lag_days, is_milestone,
                    constraint_type, progress_status, percent_complete,
                    remaining_duration
                ) VALUES (
                    1, 'Rough-in', 3, 1, 0, 'FS', 0, 0, 'ASAP',
                    'not_started', 0, 3
                );
                """
            )

        command.upgrade(self.config, CURRENT_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertTrue(
                {
                    "crews",
                    "equipment_resources",
                    "task_resource_assignments",
                    "resource_availability",
                }.issubset(tables)
            )
            for table in (
                "crews",
                "equipment_resources",
                "task_resource_assignments",
                "resource_availability",
            ):
                self.assertEqual(
                    connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
                    0,
                )
            assignment_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(task_resource_assignments)"
                )
            }
            availability_indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(resource_availability)")
            }
            self.assertIn("ix_task_resource_assignments_project_task", assignment_indexes)
            self.assertIn("ix_resource_availability_project_crew_dates", availability_indexes)
            connection.executescript(
                """
                INSERT INTO crews (
                    id, project_id, name, normalized_name, trade, company_id,
                    default_capacity, capacity_unit, status, created_by
                ) VALUES (
                    1, 1, 'Electrical A', 'electrical a', 'Electrical', 1,
                    6, 'workers', 'active', 1
                );
                INSERT INTO equipment_resources (
                    id, project_id, name, normalized_name, equipment_type,
                    identifier, normalized_identifier, default_capacity,
                    capacity_unit, status, created_by
                ) VALUES (
                    1, 1, 'Lift 1', 'lift 1', 'Scissor Lift', 'SL-01',
                    'sl-01', 1, 'units', 'active', 1
                );
                INSERT INTO task_resource_assignments (
                    id, project_id, task_id, resource_type, crew_id,
                    allocation_amount, allocation_unit, created_by
                ) VALUES (1, 1, 1, 'crew', 1, 4, 'workers', 1);
                INSERT INTO resource_availability (
                    id, project_id, resource_type, equipment_resource_id,
                    start_date, end_date, capacity, created_by
                ) VALUES (
                    1, 1, 'equipment', 1, '2026-08-10', '2026-08-12', 0, 1
                );
                """
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE crews SET default_capacity = 0 WHERE id = 1")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE task_resource_assignments SET equipment_resource_id = 1 WHERE id = 1"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE resource_availability SET end_date = '2026-08-09' WHERE id = 1"
                )

        command.downgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertNotIn("crews", tables)
            self.assertNotIn("resource_availability", tables)
            self.assertIn("tasks", tables)

        command.upgrade(self.config, "head")
        command.check(self.config)
        self.assertEqual(
            ScriptDirectory.from_config(self.config).get_heads(),
            [CURRENT_REVISION],
        )


if __name__ == "__main__":
    unittest.main()
