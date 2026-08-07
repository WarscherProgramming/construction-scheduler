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
PREVIOUS_REVISION = "c8f1a4d7e290"
CURRENT_REVISION = "e2b8d4f7c103"


class EntityRelationshipMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        os.environ["SECRET_KEY"] = "relationship-migration-test-secret"
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

    def test_fresh_upgrade_has_constraints_indexes_and_one_head(self):
        command.upgrade(self.config, "head")
        command.check(self.config)
        script = ScriptDirectory.from_config(self.config)
        self.assertEqual(script.get_heads(), [CURRENT_REVISION])

        with closing(sqlite3.connect(self.database_path)) as connection:
            current = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(entity_relationships)"
                )
            }
            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(entity_relationships)"
                )
            }
            table_sql = connection.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type = 'table' AND name = 'entity_relationships'
                """
            ).fetchone()[0]

        self.assertEqual(current, (CURRENT_REVISION,))
        self.assertEqual(
            columns,
            {
                "id",
                "project_id",
                "source_type",
                "source_id",
                "target_type",
                "target_id",
                "relationship_type",
                "created_by",
                "created_at",
                "updated_at",
                "deleted_at",
            },
        )
        self.assertTrue(
            {
                "uq_entity_relationships_active_pair",
                "ix_entity_relationships_project_source",
                "ix_entity_relationships_project_target",
                "ix_entity_relationships_project_type",
                "ix_entity_relationships_project_created",
            }.issubset(indexes)
        )
        self.assertIn("ck_entity_relationships_distinct_entities", table_sql)
        self.assertIn("ck_entity_relationships_relationship_type", table_sql)

    def test_active_unique_pair_allows_recreate_after_soft_delete(self):
        command.upgrade(self.config, "head")
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'owner@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Existing', 1);
                INSERT INTO entity_relationships (
                    project_id, source_type, source_id, target_type,
                    target_id, relationship_type, created_by
                ) VALUES (
                    1, 'rfi', 1, 'drawing_revision', 2,
                    'references', 1
                );
                """
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO entity_relationships (
                        project_id, source_type, source_id, target_type,
                        target_id, relationship_type, created_by
                    ) VALUES (1, 'rfi', 1, 'drawing_revision', 2,
                              'references', 1)
                    """
                )
            connection.rollback()
            connection.execute(
                "UPDATE entity_relationships SET deleted_at = CURRENT_TIMESTAMP"
            )
            connection.execute(
                """
                INSERT INTO entity_relationships (
                    project_id, source_type, source_id, target_type,
                    target_id, relationship_type, created_by
                ) VALUES (1, 'rfi', 1, 'drawing_revision', 2,
                          'references', 1)
                """
            )
            connection.commit()
            count = connection.execute(
                "SELECT COUNT(*) FROM entity_relationships"
            ).fetchone()[0]
        self.assertEqual(count, 2)

    def test_upgrade_preserves_data_then_downgrades_and_reupgrades(self):
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
            project = connection.execute(
                "SELECT id, name FROM projects"
            ).fetchone()
            relationship_table = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'entity_relationships'
                """
            ).fetchone()
        self.assertEqual(project, (1, "Existing"))
        self.assertEqual(relationship_table, ("entity_relationships",))

        command.downgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            relationship_table = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'entity_relationships'
                """
            ).fetchone()
            project = connection.execute(
                "SELECT id, name FROM projects"
            ).fetchone()
        self.assertIsNone(relationship_table)
        self.assertEqual(project, (1, "Existing"))

        command.upgrade(self.config, "head")
        command.check(self.config)
        with closing(sqlite3.connect(self.database_path)) as connection:
            current = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()
        self.assertEqual(current, (CURRENT_REVISION,))


if __name__ == "__main__":
    unittest.main()
