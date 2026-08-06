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
PREVIOUS_REVISION = "f7c5d0b3e826"
CURRENT_REVISION = "b9e5d3f7a201"


class PreconstructionMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path.as_posix()}"
        os.environ["SECRET_KEY"] = "preconstruction-migration-test-secret"
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

    def test_tables_constraints_indexes_and_upgrade_downgrade_lifecycle(self):
        command.upgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'precon@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Preconstruction', 1);
                INSERT INTO documents (
                    id, project_id, original_filename, display_name,
                    extension, mime_type, size_bytes, checksum_sha256,
                    storage_provider, storage_key, uploaded_by,
                    version, is_current_version, document_type, status
                ) VALUES (
                    1, 1, 'plans.pdf', 'Plans', 'pdf', 'application/pdf',
                    10, 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    'local', 'projects/1/plans', 1, 1, 1, 'Drawing', 'Active'
                );
                INSERT INTO document_extractions (
                    id, project_id, document_id, status, extraction_method,
                    page_count, pages_processed, text_character_count,
                    searchable, language, extractor_version, source_checksum
                ) VALUES (
                    1, 1, 1, 'completed', 'embedded_text', 1, 1, 10,
                    1, 'eng', 'v1',
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
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
            expected = {
                "preconstruction_review_sets",
                "preconstruction_review_sources",
                "preconstruction_analysis_runs",
                "preconstruction_analysis_attempts",
            }
            self.assertTrue(expected.issubset(tables))
            source_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(preconstruction_review_sources)"
                )
            }
            attempt_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(preconstruction_analysis_attempts)"
                )
            }
            self.assertIn(
                "uq_preconstruction_review_sources_active_logical",
                source_indexes,
            )
            self.assertIn(
                "ix_preconstruction_analysis_attempts_pending",
                attempt_indexes,
            )
            connection.executescript(
                """
                INSERT INTO preconstruction_review_sets (
                    id, project_id, name, normalized_name, purpose, status,
                    created_by
                ) VALUES (
                    1, 1, 'Bid Review', 'bid review', 'bid_scope_review',
                    'draft', 1
                );
                INSERT INTO preconstruction_review_sources (
                    id, project_id, review_set_id, source_type, document_id,
                    document_role, source_checksum, extraction_id,
                    extraction_version, extraction_status,
                    display_name_snapshot, added_by
                ) VALUES (
                    1, 1, 1, 'document', 1, 'drawing',
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    1, 'v1', 'completed', 'Plans', 1
                );
                INSERT INTO preconstruction_analysis_runs (
                    id, project_id, review_set_id, status, provider_profile,
                    analysis_type, manifest_hash, manifest_json, source_count,
                    template_version, schema_version, requested_by,
                    current_attempt_count, max_attempts
                ) VALUES (
                    1, 1, 1, 'pending', 'fake_test',
                    'provider_contract_validation',
                    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                    '{}', 1, 'v1', 'v1', 1, 1, 3
                );
                INSERT INTO preconstruction_analysis_attempts (
                    id, project_id, run_id, attempt_number, provider_profile,
                    provider_name, model_name, status, input_manifest_hash,
                    output_schema_version
                ) VALUES (
                    1, 1, 1, 1, 'fake_test', 'deterministic_fake',
                    'fieldflow-fake-v1', 'pending',
                    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                    'v1'
                );
                """
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO preconstruction_review_sets "
                    "(project_id, name, normalized_name, purpose, status, created_by) "
                    "VALUES (1, 'Duplicate', 'bid review', 'bid_scope_review', 'draft', 1)"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE preconstruction_review_sources SET document_role = 'custom' WHERE id = 1"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO preconstruction_analysis_attempts "
                    "(project_id, run_id, attempt_number, provider_profile, provider_name, "
                    "model_name, status, input_manifest_hash, output_schema_version) "
                    "VALUES (1, 1, 2, 'fake_test', 'fake', 'fake', 'pending', "
                    "'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'v1')"
                )

        command.downgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertFalse(expected.intersection(tables))
            self.assertIn("documents", tables)

        command.upgrade(self.config, "head")
        command.check(self.config)
        self.assertEqual(
            ScriptDirectory.from_config(self.config).get_heads(),
            [CURRENT_REVISION],
        )


if __name__ == "__main__":
    unittest.main()
