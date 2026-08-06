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
PREVIOUS_REVISION = "a8f4c2d6e190"
CURRENT_REVISION = "c1f7b4e28d35"


class PreconstructionContentMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path.as_posix()}"
        os.environ["SECRET_KEY"] = "preconstruction-content-migration-test-secret"
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

    def test_tables_constraints_indexes_no_backfill_and_lifecycle(self):
        command.upgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'content@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Content', 1);
                INSERT INTO documents (
                    id, project_id, original_filename, display_name,
                    extension, mime_type, size_bytes, checksum_sha256,
                    storage_provider, storage_key, uploaded_by,
                    version, is_current_version, document_type, status
                ) VALUES (
                    1, 1, 'scope.pdf', 'Scope', 'pdf', 'application/pdf',
                    10, 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    'local', 'projects/1/scope', 1, 1, 1, 'General', 'Active'
                );
                INSERT INTO document_extractions (
                    id, project_id, document_id, status, extraction_method,
                    page_count, pages_processed, text_character_count,
                    searchable, language, extractor_version, source_checksum
                ) VALUES (
                    1, 1, 1, 'completed', 'embedded_text', 1, 1, 5,
                    1, 'eng', 'v1',
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                );
                INSERT INTO preconstruction_review_sets (
                    id, project_id, name, normalized_name, purpose, status, created_by
                ) VALUES (
                    1, 1, 'Scope Review', 'scope review', 'general_scope_review', 'draft', 1
                );
                INSERT INTO preconstruction_review_sources (
                    id, project_id, review_set_id, source_type, document_id,
                    document_role, source_checksum, extraction_id,
                    extraction_version, extraction_status,
                    display_name_snapshot, added_by
                ) VALUES (
                    1, 1, 1, 'document', 1, 'specification',
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    1, 'v1', 'completed', 'Scope', 1
                );
                """
            )

        command.upgrade(self.config, CURRENT_REVISION)
        expected = {
            "preconstruction_preparation_runs",
            "preconstruction_content_snapshots",
            "preconstruction_content_pages",
            "preconstruction_content_segments",
        }
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertTrue(expected.issubset(tables))
            for table in expected:
                self.assertEqual(
                    connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
                    0,
                )
            run_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(preconstruction_preparation_runs)"
                )
            }
            segment_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(preconstruction_content_segments)"
                )
            }
            self.assertIn("uq_preconstruction_preparation_runs_active_lineage", run_indexes)
            self.assertIn("ix_preconstruction_content_segments_snapshot_order", segment_indexes)
            connection.executescript(
                """
                INSERT INTO preconstruction_preparation_runs (
                    id, project_id, review_source_id, status, source_checksum,
                    lineage_fingerprint, extraction_id, extraction_method,
                    extractor_version, preparation_version,
                    segmentation_policy_version, attempt_count, max_attempts,
                    requested_by
                ) VALUES (
                    1, 1, 1, 'completed',
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                    1, 'embedded_text', 'v1', 'prepare-v1', 'segment-v1', 1, 3, 1
                );
                INSERT INTO preconstruction_content_snapshots (
                    id, project_id, review_source_id, document_id,
                    source_checksum, extraction_id, extraction_method,
                    extractor_version, preparation_version,
                    segmentation_policy_version, lineage_fingerprint, status,
                    page_count, segment_count, total_character_count,
                    content_hash, preparation_run_id, warning_count
                ) VALUES (
                    1, 1, 1, 1,
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    1, 'embedded_text', 'v1', 'prepare-v1', 'segment-v1',
                    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                    'completed', 1, 1, 5,
                    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
                    1, 0
                );
                INSERT INTO preconstruction_content_pages (
                    id, project_id, snapshot_id, page_number, extraction_method,
                    character_count, page_text_hash, has_searchable_text,
                    has_visual_content
                ) VALUES (
                    1, 1, 1, 1, 'embedded_text', 5,
                    'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
                    1, 0
                );
                INSERT INTO preconstruction_content_segments (
                    id, project_id, snapshot_id, page_id, segment_index,
                    segment_type, text, normalized_text, text_hash,
                    character_start, character_end, token_estimate,
                    extraction_method
                ) VALUES (
                    1, 1, 1, 1, 0, 'page_text', 'Scope', 'scope',
                    'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
                    0, 5, 2, 'embedded_text'
                );
                """
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO preconstruction_content_pages "
                    "(project_id, snapshot_id, page_number, extraction_method, character_count, "
                    "page_text_hash, has_searchable_text, has_visual_content) "
                    "VALUES (1, 1, 0, 'embedded_text', 0, 'x', 0, 0)"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE preconstruction_content_segments SET segment_type = 'finding' WHERE id = 1"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO preconstruction_preparation_runs "
                    "(project_id, review_source_id, status, source_checksum, lineage_fingerprint, "
                    "extraction_method, extractor_version, preparation_version, "
                    "segmentation_policy_version, attempt_count, max_attempts, requested_by) "
                    "VALUES (1, 1, 'pending', 'a', 'f', 'embedded_text', 'v1', 'v1', 'v1', 4, 3, 1)"
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
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM preconstruction_review_sources"
                ).fetchone()[0],
                1,
            )

        command.upgrade(self.config, "head")
        command.check(self.config)
        self.assertEqual(
            ScriptDirectory.from_config(self.config).get_heads(),
            [CURRENT_REVISION],
        )


if __name__ == "__main__":
    unittest.main()
