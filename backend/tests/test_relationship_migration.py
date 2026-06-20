from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config


BACKEND_DIR = Path(__file__).resolve().parents[1]
LEGACY_REVISION = "4b7d9c2a6f10"


class StableRelationshipMigrationTests(unittest.TestCase):
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

    def test_legacy_positions_and_indentation_migrate_to_task_ids(self):
        command.upgrade(self.config, LEGACY_REVISION)

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'test@example.com', 'hash');

                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Legacy', 1);

                INSERT INTO tasks (
                    id, name, duration, predecessor, project_id,
                    order_index, parent_task_id, indent_level, is_collapsed
                ) VALUES
                    (101, 'Foundation', 1, NULL, 1, 1, NULL, 0, 0),
                    (205, '    Excavate', 2, '1', 1, 2, NULL, 1, 0),
                    (309, '    Footings', 1, '2SS+3', 1, 3, NULL, 1, 0);

                INSERT INTO schedule_templates (id, name)
                VALUES (1, 'Legacy Template');

                INSERT INTO schedule_template_tasks (
                    id, template_id, name, duration, predecessor
                ) VALUES
                    (11, 1, 'Foundation', 1, NULL),
                    (22, 1, '    Excavate', 2, '1'),
                    (33, 1, '    Footings', 1, '2SS+3');
                """
            )

        command.upgrade(self.config, "head")
        command.check(self.config)

        with closing(sqlite3.connect(self.database_path)) as connection:
            tasks = connection.execute(
                """
                SELECT id, name, predecessor_task_id, dependency_type,
                       lag_days, parent_task_id
                FROM tasks
                ORDER BY order_index
                """
            ).fetchall()
            template_tasks = connection.execute(
                """
                SELECT id, name, predecessor_template_task_id,
                       dependency_type, lag_days, parent_template_task_id
                FROM schedule_template_tasks
                ORDER BY order_index
                """
            ).fetchall()

        self.assertEqual(
            tasks,
            [
                (101, "Foundation", None, "FS", 0, None),
                (205, "Excavate", 101, "FS", 0, 101),
                (309, "Footings", 205, "SS", 3, 101),
            ],
        )
        self.assertEqual(
            template_tasks,
            [
                (11, "Foundation", None, "FS", 0, None),
                (22, "Excavate", 11, "FS", 0, 11),
                (33, "Footings", 22, "SS", 3, 11),
            ],
        )

        command.downgrade(self.config, LEGACY_REVISION)

        with closing(sqlite3.connect(self.database_path)) as connection:
            restored_tasks = connection.execute(
                """
                SELECT id, name, predecessor, indent_level
                FROM tasks
                ORDER BY order_index
                """
            ).fetchall()

        self.assertEqual(
            restored_tasks,
            [
                (101, "Foundation", None, 0),
                (205, "    Excavate", "1", 1),
                (309, "    Footings", "2SS+3", 1),
            ],
        )


if __name__ == "__main__":
    unittest.main()
