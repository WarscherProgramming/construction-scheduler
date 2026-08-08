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
PREVIOUS_REVISION = "b9e5d3f7a201"
CURRENT_REVISION = "f3d6a8b2c517"

SCOPE_TABLES = (
    "preconstruction_scope_assertion_sets",
    "preconstruction_scope_assertions",
    "preconstruction_assertion_evidence",
    "preconstruction_assertion_reviews",
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


class ScopeAssertionMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path.as_posix()}"
        os.environ["SECRET_KEY"] = "scope-assertion-migration-test-secret-value"
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

    def seed_preconstruction_content(self, connection):
        connection.executescript(
            f"""
            INSERT INTO users (id, email, hashed_password)
            VALUES (1, 'scope@example.com', 'hash');
            INSERT INTO projects (id, name, user_id) VALUES (1, 'Scope', 1);
            INSERT INTO documents (
                id, project_id, original_filename, display_name, extension,
                mime_type, size_bytes, checksum_sha256, storage_provider,
                storage_key, uploaded_by, version, is_current_version,
                document_type, status
            ) VALUES (
                1, 1, 'spec.pdf', 'Spec', 'pdf', 'application/pdf', 10,
                '{HASH_A}', 'local', 'projects/1/spec', 1, 1, 1,
                'General', 'Active'
            );
            INSERT INTO document_extractions (
                id, project_id, document_id, status, extraction_method,
                page_count, pages_processed, text_character_count,
                searchable, language, extractor_version, source_checksum
            ) VALUES (
                1, 1, 1, 'completed', 'embedded_text', 1, 1, 5, 1, 'eng',
                'v1', '{HASH_A}'
            );
            INSERT INTO preconstruction_review_sets (
                id, project_id, name, normalized_name, purpose, status, created_by
            ) VALUES (1, 1, 'Scope Review', 'scope review', 'bid_scope_review', 'ready', 1);
            INSERT INTO preconstruction_review_sources (
                id, project_id, review_set_id, source_type, document_id,
                document_role, source_checksum, extraction_id,
                extraction_version, extraction_status,
                display_name_snapshot, added_by
            ) VALUES (
                1, 1, 1, 'document', 1, 'specification', '{HASH_A}', 1, 'v1',
                'completed', 'Spec', 1
            );
            INSERT INTO preconstruction_analysis_runs (
                id, project_id, review_set_id, status, provider_profile,
                analysis_type, manifest_hash, manifest_json, source_count,
                template_version, schema_version, requested_by,
                current_attempt_count, max_attempts
            ) VALUES (
                1, 1, 1, 'completed', 'fake_test', 'content_contract_validation',
                '{HASH_B}', '{{}}', 1, 't1', 's1', 1, 1, 3
            );
            INSERT INTO preconstruction_preparation_runs (
                id, project_id, review_source_id, status, source_checksum,
                lineage_fingerprint, extraction_id, extraction_method,
                extractor_version, preparation_version,
                segmentation_policy_version, attempt_count, max_attempts,
                requested_by
            ) VALUES (
                1, 1, 1, 'completed', '{HASH_A}', '{HASH_C}', 1,
                'embedded_text', 'v1', 'p1', 'seg1', 1, 3, 1
            );
            INSERT INTO preconstruction_content_snapshots (
                id, project_id, review_source_id, document_id, source_checksum,
                extraction_id, extraction_method, extractor_version,
                preparation_version, segmentation_policy_version,
                lineage_fingerprint, status, page_count, segment_count,
                total_character_count, content_hash, preparation_run_id
            ) VALUES (
                1, 1, 1, 1, '{HASH_A}', 1, 'embedded_text', 'v1', 'p1', 'seg1',
                '{HASH_C}', 'completed', 1, 1, 20, '{HASH_B}', 1
            );
            INSERT INTO preconstruction_content_pages (
                id, project_id, snapshot_id, page_number, extraction_method,
                character_count, page_text_hash, has_searchable_text,
                has_visual_content
            ) VALUES (1, 1, 1, 1, 'embedded_text', 20, '{HASH_A}', 1, 0);
            INSERT INTO preconstruction_content_segments (
                id, project_id, snapshot_id, page_id, segment_index,
                segment_type, text, normalized_text, text_hash,
                extraction_method
            ) VALUES (
                1, 1, 1, 1, 0, 'page_text', 'Provide LED fixtures',
                'provide led fixtures', '{HASH_B}', 'embedded_text'
            );
            """
        )
        connection.commit()

    def test_tables_constraints_indexes_no_backfill_and_lifecycle(self):
        command.upgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            self.seed_preconstruction_content(connection)
            existing_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            # The scope tables do not exist before this migration.
            for table in SCOPE_TABLES:
                self.assertNotIn(table, existing_tables)
            # The prior analysis-type allowlist rejects the new type.
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    f"""
                    INSERT INTO preconstruction_analysis_runs (
                        id, project_id, review_set_id, status, provider_profile,
                        analysis_type, manifest_hash, manifest_json, source_count,
                        template_version, schema_version, requested_by,
                        current_attempt_count, max_attempts
                    ) VALUES (
                        99, 1, 1, 'pending', 'fake_test', 'scope_assertion_extraction',
                        '{HASH_C}', '{{}}', 1, 't1', 's1', 1, 1, 3
                    )
                    """
                )
            connection.rollback()

        command.upgrade(self.config, CURRENT_REVISION)
        command.check(self.config)

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertTrue(set(SCOPE_TABLES).issubset(tables))

            # No backfill: existing review sets receive no assertions.
            for table in SCOPE_TABLES:
                with self.subTest(table=table):
                    self.assertEqual(
                        connection.execute(
                            f"SELECT COUNT(*) FROM {table}"
                        ).fetchone()[0],
                        0,
                    )

            # Existing preconstruction rows are untouched.
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM preconstruction_content_segments"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT status FROM preconstruction_analysis_runs WHERE id = 1"
                ).fetchone()[0],
                "completed",
            )

            # Named indexes come from op.create_index.
            expected_indexes = {
                "preconstruction_scope_assertion_sets": {
                    "ix_preconstruction_scope_assertion_sets_review_listing",
                },
                "preconstruction_scope_assertions": {
                    "ix_preconstruction_scope_assertions_review_listing",
                    "ix_preconstruction_scope_assertions_set_order",
                    "ix_preconstruction_scope_assertions_source_concept",
                },
                "preconstruction_assertion_evidence": {
                    "ix_preconstruction_assertion_evidence_assertion_order",
                },
                "preconstruction_assertion_reviews": {
                    "ix_preconstruction_assertion_reviews_assertion_order",
                    "ix_preconstruction_assertion_reviews_project_listing",
                },
            }
            for table, expected in expected_indexes.items():
                with self.subTest(index_table=table):
                    names = {
                        row[1]
                        for row in connection.execute(f"PRAGMA index_list({table})")
                    }
                    self.assertTrue(expected.issubset(names), names)

            # Table-level UNIQUE constraints become autoindexes in SQLite, so
            # assert them against the retained DDL by constraint name.
            expected_constraints = {
                "preconstruction_scope_assertion_sets": (
                    "uq_preconstruction_scope_assertion_sets_run",
                ),
                "preconstruction_scope_assertions": (
                    "uq_preconstruction_scope_assertions_set_provider_key",
                    "ck_preconstruction_scope_assertions_origin_consistency",
                ),
                "preconstruction_assertion_evidence": (
                    "uq_preconstruction_assertion_evidence_segment_role",
                ),
                "preconstruction_assertion_reviews": (
                    "ck_preconstruction_assertion_reviews_decision",
                ),
            }
            for table, names in expected_constraints.items():
                ddl = connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                    (table,),
                ).fetchone()[0]
                for name in names:
                    with self.subTest(constraint_table=table, constraint=name):
                        self.assertIn(name, ddl)

            # The widened allowlist now accepts scope extraction runs.
            connection.executescript(
                f"""
                INSERT INTO preconstruction_analysis_runs (
                    id, project_id, review_set_id, status, provider_profile,
                    analysis_type, manifest_hash, manifest_json, source_count,
                    template_version, schema_version, requested_by,
                    current_attempt_count, max_attempts
                ) VALUES (
                    2, 1, 1, 'completed', 'fake_test', 'scope_assertion_extraction',
                    '{HASH_C}', '{{}}', 1, 't1', 's1', 1, 1, 3
                );
                INSERT INTO preconstruction_scope_assertion_sets (
                    id, project_id, analysis_run_id, review_set_id, manifest_hash,
                    taxonomy_version, schema_version, provider_profile, status,
                    assertion_count, warning_count, content_hash
                ) VALUES (
                    1, 1, 2, 1, '{HASH_C}', 'construction-scope-1',
                    'scope-assertion-1', 'fake_test', 'completed', 1, 0, '{HASH_A}'
                );
                INSERT INTO preconstruction_scope_assertions (
                    id, project_id, assertion_set_id, review_set_id, source_id,
                    origin, concept_code, taxonomy_version, assertion_type,
                    subject, inclusion_state, confidence, provider_assertion_key,
                    status
                ) VALUES (
                    1, 1, 1, 1, 1, 'provider', 'electrical.lighting_fixture',
                    'construction-scope-1', 'physical_item', 'LED fixtures',
                    'included', 0.8, 'key-1', 'proposed'
                );
                INSERT INTO preconstruction_assertion_evidence (
                    id, project_id, assertion_id, source_id, content_snapshot_id,
                    content_page_id, content_segment_id, page_number,
                    segment_index, text_hash, excerpt, evidence_role
                ) VALUES (
                    1, 1, 1, 1, 1, 1, 1, 1, 0, '{HASH_B}',
                    'Provide LED fixtures', 'primary'
                );
                INSERT INTO preconstruction_assertion_reviews (
                    id, project_id, assertion_id, decision, reason_code,
                    reviewer_note, reviewed_by
                ) VALUES (1, 1, 1, 'accepted', NULL, 'Confirmed', 1);
                """
            )
            connection.commit()

            # Controlled-value constraints reject invented values.
            invalid_statements = {
                "assertion type": """
                    INSERT INTO preconstruction_scope_assertions (
                        id, project_id, assertion_set_id, review_set_id, source_id,
                        origin, concept_code, taxonomy_version, assertion_type,
                        subject, inclusion_state, provider_assertion_key, status
                    ) VALUES (90, 1, 1, 1, 1, 'provider', 'x', 'v', 'invented',
                              'S', 'included', 'k90', 'proposed')
                """,
                "inclusion state": """
                    INSERT INTO preconstruction_scope_assertions (
                        id, project_id, assertion_set_id, review_set_id, source_id,
                        origin, concept_code, taxonomy_version, assertion_type,
                        subject, inclusion_state, provider_assertion_key, status
                    ) VALUES (91, 1, 1, 1, 1, 'provider', 'x', 'v', 'requirement',
                              'S', 'invented', 'k91', 'proposed')
                """,
                "confidence range": """
                    INSERT INTO preconstruction_scope_assertions (
                        id, project_id, assertion_set_id, review_set_id, source_id,
                        origin, concept_code, taxonomy_version, assertion_type,
                        subject, inclusion_state, confidence, provider_assertion_key,
                        status
                    ) VALUES (92, 1, 1, 1, 1, 'provider', 'x', 'v', 'requirement',
                              'S', 'included', 1.5, 'k92', 'proposed')
                """,
                "manual origin carries no confidence": """
                    INSERT INTO preconstruction_scope_assertions (
                        id, project_id, assertion_set_id, review_set_id, source_id,
                        origin, concept_code, taxonomy_version, assertion_type,
                        subject, inclusion_state, confidence, status
                    ) VALUES (93, 1, NULL, 1, 1, 'manual', 'x', 'v', 'requirement',
                              'S', 'included', 0.5, 'accepted')
                """,
                "provider origin requires a set": """
                    INSERT INTO preconstruction_scope_assertions (
                        id, project_id, assertion_set_id, review_set_id, source_id,
                        origin, concept_code, taxonomy_version, assertion_type,
                        subject, inclusion_state, provider_assertion_key, status
                    ) VALUES (94, 1, NULL, 1, 1, 'provider', 'x', 'v', 'requirement',
                              'S', 'included', 'k94', 'proposed')
                """,
                "review decision": """
                    INSERT INTO preconstruction_assertion_reviews (
                        id, project_id, assertion_id, decision, reviewed_by
                    ) VALUES (90, 1, 1, 'invented', 1)
                """,
                "review reason code": """
                    INSERT INTO preconstruction_assertion_reviews (
                        id, project_id, assertion_id, decision, reason_code, reviewed_by
                    ) VALUES (91, 1, 1, 'rejected', 'invented', 1)
                """,
                "evidence role": """
                    INSERT INTO preconstruction_assertion_evidence (
                        id, project_id, assertion_id, source_id, content_snapshot_id,
                        content_page_id, content_segment_id, page_number,
                        segment_index, text_hash, excerpt, evidence_role
                    ) VALUES (90, 1, 1, 1, 1, 1, 1, 1, 0, 'z', 'x', 'invented')
                """,
                "assertion set status": """
                    INSERT INTO preconstruction_scope_assertion_sets (
                        id, project_id, analysis_run_id, review_set_id, manifest_hash,
                        taxonomy_version, schema_version, provider_profile, status,
                        assertion_count, warning_count, content_hash
                    ) VALUES (90, 1, 2, 1, 'h', 'v', 's', 'p', 'invented', 0, 0, 'h')
                """,
            }
            for label, statement in invalid_statements.items():
                with self.subTest(constraint=label):
                    with self.assertRaises(sqlite3.IntegrityError):
                        connection.execute(statement)
                    connection.rollback()

            # One assertion set per analysis run.
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    f"""
                    INSERT INTO preconstruction_scope_assertion_sets (
                        id, project_id, analysis_run_id, review_set_id, manifest_hash,
                        taxonomy_version, schema_version, provider_profile, status,
                        assertion_count, warning_count, content_hash
                    ) VALUES (95, 1, 2, 1, '{HASH_C}', 'v', 's', 'p', 'completed',
                              0, 0, '{HASH_A}')
                    """
                )
            connection.rollback()

            # Provider assertion keys are unique inside one assertion set.
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO preconstruction_scope_assertions (
                        id, project_id, assertion_set_id, review_set_id, source_id,
                        origin, concept_code, taxonomy_version, assertion_type,
                        subject, inclusion_state, provider_assertion_key, status
                    ) VALUES (96, 1, 1, 1, 1, 'provider', 'x', 'v', 'requirement',
                              'S', 'included', 'key-1', 'proposed')
                    """
                )
            connection.rollback()

            # Duplicate evidence for one segment and role is refused.
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    f"""
                    INSERT INTO preconstruction_assertion_evidence (
                        id, project_id, assertion_id, source_id, content_snapshot_id,
                        content_page_id, content_segment_id, page_number,
                        segment_index, text_hash, excerpt, evidence_role
                    ) VALUES (97, 1, 1, 1, 1, 1, 1, 1, 0, '{HASH_B}', 'dup', 'primary')
                    """
                )
            connection.rollback()

            # Cited immutable content cannot be deleted out from under evidence.
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM preconstruction_content_segments WHERE id = 1"
                )
            connection.rollback()

            # Project deletion cascades the whole advisory graph.
            connection.execute("DELETE FROM projects WHERE id = 1")
            connection.commit()
            for table in SCOPE_TABLES:
                with self.subTest(cascade=table):
                    self.assertEqual(
                        connection.execute(
                            f"SELECT COUNT(*) FROM {table}"
                        ).fetchone()[0],
                        0,
                    )

    def test_fresh_upgrade_downgrade_reupgrade_and_single_head(self):
        command.upgrade(self.config, "head")
        command.check(self.config)
        command.downgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            for table in SCOPE_TABLES:
                self.assertNotIn(table, tables)
        command.upgrade(self.config, "head")
        command.check(self.config)
        heads = ScriptDirectory.from_config(self.config).get_heads()
        self.assertEqual(heads, [CURRENT_REVISION])
