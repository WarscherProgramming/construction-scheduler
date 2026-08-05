from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models.document_extraction import (
    DocumentExtraction,
    DocumentExtractionJob,
    DocumentPageText,
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "d9a2f5c8e173"
CURRENT_REVISION = "d4e8a1c7f925"


class DocumentExtractionMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        os.environ["SECRET_KEY"] = "document-search-migration-test-secret"
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

    def test_fresh_upgrade_has_tables_constraints_indexes_and_one_head(self):
        command.upgrade(self.config, "head")
        command.check(self.config)
        self.assertEqual(
            ScriptDirectory.from_config(self.config).get_heads(),
            [CURRENT_REVISION],
        )
        with closing(sqlite3.connect(self.database_path)) as connection:
            current = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            page_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(document_page_texts)"
                )
            }
            job_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(document_extraction_jobs)"
                )
            }
            extraction_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' "
                "AND name = 'document_extractions'"
            ).fetchone()[0]
        self.assertEqual(current, (CURRENT_REVISION,))
        self.assertTrue(
            {
                "document_extractions",
                "document_page_texts",
                "document_extraction_jobs",
            }.issubset(tables)
        )
        self.assertIn("ix_document_page_texts_search_vector", page_indexes)
        self.assertIn("uq_document_extraction_jobs_active_document", job_indexes)
        self.assertIn("ck_document_extractions_status", extraction_sql)

    def test_page_and_active_job_uniqueness_are_enforced(self):
        command.upgrade(self.config, "head")
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(
                """
                INSERT INTO users (id, email, hashed_password)
                VALUES (1, 'owner@example.com', 'hash');
                INSERT INTO projects (id, name, user_id)
                VALUES (1, 'Search', 1);
                INSERT INTO documents (
                    id, project_id, original_filename, display_name,
                    extension, mime_type, size_bytes, checksum_sha256,
                    storage_provider, storage_key, uploaded_by,
                    document_type, status
                ) VALUES (
                    1, 1, 'a.pdf', 'A', '.pdf', 'application/pdf', 1,
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    'memory', 'documents/aa/bb/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    1, 'General', 'Active'
                );
                INSERT INTO document_extractions (
                    id, project_id, document_id, extractor_version,
                    source_checksum
                ) VALUES (
                    1, 1, 1, 'test-1',
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                );
                INSERT INTO document_page_texts (
                    project_id, extraction_id, document_id, page_number,
                    text, normalized_text, extraction_method, character_count
                ) VALUES (1, 1, 1, 1, 'text', 'text', 'embedded_text', 4);
                INSERT INTO document_extraction_jobs (
                    project_id, document_id, requested_by, source_checksum,
                    extractor_version
                ) VALUES (
                    1, 1, 1,
                    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    'test-1'
                );
                """
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO document_page_texts (project_id, extraction_id, "
                    "document_id, page_number, text, normalized_text, "
                    "extraction_method, character_count) "
                    "VALUES (1, 1, 1, 1, 'again', 'again', 'embedded_text', 5)"
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO document_extraction_jobs (project_id, document_id, "
                    "requested_by, source_checksum, extractor_version) VALUES "
                    "(1, 1, 1, "
                    "'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', "
                    "'test-1')"
                )

    def test_upgrade_preserves_documents_then_downgrades_and_reupgrades(self):
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
        command.downgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            project = connection.execute(
                "SELECT id, name FROM projects"
            ).fetchone()
            extraction_table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name = 'document_extractions'"
            ).fetchone()
        self.assertEqual(project, (1, "Existing"))
        self.assertIsNone(extraction_table)
        command.upgrade(self.config, "head")
        command.check(self.config)

    def test_postgresql_model_uses_tsvector_and_gin(self):
        table_sql = str(
            CreateTable(DocumentPageText.__table__).compile(
                dialect=postgresql.dialect()
            )
        )
        search_index = next(
            index
            for index in DocumentPageText.__table__.indexes
            if index.name == "ix_document_page_texts_search_vector"
        )
        index_sql = str(
            CreateIndex(search_index).compile(dialect=postgresql.dialect())
        )
        self.assertIn("TSVECTOR", table_sql)
        self.assertIn("USING gin", index_sql)
        self.assertEqual(
            DocumentExtraction.__table__.c.document_id.unique,
            None,
        )
        self.assertIn(
            "uq_document_extraction_jobs_active_document",
            {index.name for index in DocumentExtractionJob.__table__.indexes},
        )


if __name__ == "__main__":
    unittest.main()
