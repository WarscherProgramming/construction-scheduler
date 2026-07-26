from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config


BACKEND_DIR = Path(__file__).resolve().parents[1]
LEGACY_REVISION = "d94f7a2b6e31"


class ChangeOrderMigrationTests(unittest.TestCase):
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

    def test_legacy_rows_migrate_without_data_loss(self):
        command.upgrade(self.config, LEGACY_REVISION)

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'test@example.com', 'hash');

                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Legacy', 1);

                INSERT INTO change_orders (
                    id, project_id, date, co_number, company, status,
                    description, amount, responsible_party
                ) VALUES
                    (
                        1, 1, '2026-06-01', 'CO-001', 'Alpha', 'Pending',
                        'First', '$1,234.50', 'Owner'
                    ),
                    (
                        2, 1, '2026-06-02', 'CO-001', 'Beta', 'Void',
                        'Duplicate', 'not-money', 'Owner'
                    ),
                    (
                        3, 1, '2026-06-03', 'legacy-7', 'Gamma', 'Approved',
                        'Malformed number', '-10', 'Owner'
                    ),
                    (
                        4, 1, '2026-06-04', '   ', 'Delta', 'Custom Legacy',
                        'Blank number', '0', 'Owner'
                    );
                """
            )

        command.upgrade(self.config, "head")
        command.check(self.config)

        with closing(sqlite3.connect(self.database_path)) as connection:
            rows = connection.execute(
                """
                SELECT id, co_number, status, amount, proposed_amount,
                       requested_date, created_at, updated_at
                FROM change_orders
                ORDER BY id
                """
            ).fetchall()
            sequence = connection.execute(
                """
                SELECT project_id, last_number
                FROM change_order_number_sequences
                """
            ).fetchall()

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO change_orders (
                        project_id, date, co_number, status,
                        description, created_at, updated_at
                    ) VALUES (
                        1, '2026-06-05', 'CO-001', 'Pending',
                        'Conflict', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                )

        self.assertEqual(len(rows), 4)
        self.assertEqual(
            [(row[0], row[1]) for row in rows],
            [
                (1, "CO-001"),
                (2, "CO-002"),
                (3, "legacy-7"),
                (4, "CO-003"),
            ],
        )
        self.assertEqual([row[2] for row in rows], [
            "Pending",
            "Void",
            "Approved",
            "Custom Legacy",
        ])
        self.assertEqual([row[3] for row in rows], [
            "$1,234.50",
            "not-money",
            "-10",
            "0",
        ])
        self.assertEqual(
            [row[4] for row in rows],
            [1234.5, None, None, 0],
        )
        self.assertTrue(all(row[5] is None for row in rows))
        self.assertTrue(all(row[6] and row[7] for row in rows))
        self.assertEqual(sequence, [(1, 3)])

        command.downgrade(self.config, LEGACY_REVISION)

        with closing(sqlite3.connect(self.database_path)) as connection:
            restored = connection.execute(
                """
                SELECT id, co_number, status, amount
                FROM change_orders
                ORDER BY id
                """
            ).fetchall()
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(change_orders)"
                )
            }

        self.assertEqual(len(restored), 4)
        self.assertNotIn("proposed_amount", columns)
        self.assertNotIn("created_at", columns)

        command.upgrade(self.config, "head")
        with closing(sqlite3.connect(self.database_path)) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM change_orders"
                ).fetchone()[0],
                4,
            )

    def test_fresh_database_upgrade_and_downgrade(self):
        command.upgrade(self.config, "head")
        command.check(self.config)

        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                )
            }
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(change_orders)"
                )
            }

        self.assertIn("change_order_number_sequences", tables)
        self.assertIn("approved_amount", columns)
        self.assertIn("executed_date", columns)

        command.downgrade(self.config, LEGACY_REVISION)
        command.upgrade(self.config, "head")
        command.check(self.config)


if __name__ == "__main__":
    unittest.main()
