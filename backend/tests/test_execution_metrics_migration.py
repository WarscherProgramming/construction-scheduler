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
PREVIOUS_REVISION = "e2b8d4f7c103"
CURRENT_REVISION = "f3d6a8b2c517"

METRICS_TABLE = "preconstruction_execution_metrics"

# M18.1-M18.5 tables a metrics row must never rewrite or restate.
IMMUTABLE_TABLES = (
    "preconstruction_content_snapshots",
    "preconstruction_scope_assertions",
    "preconstruction_assertion_evidence",
    "preconstruction_finding_sets",
    "preconstruction_findings",
    "preconstruction_finding_reviews",
    "preconstruction_finding_follow_ups",
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


class ExecutionMetricsMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path.as_posix()}"
        os.environ["SECRET_KEY"] = "execution-metrics-migration-test-secret"
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

    def seed(self, connection):
        """A complete M18.1-M18.5 graph, so nothing here can be a fresh install."""
        connection.executescript(
            f"""
            INSERT INTO users (id, email, hashed_password)
            VALUES (1, 'metrics@example.com', 'hash');
            INSERT INTO projects (id, name, user_id) VALUES (1, 'Metrics', 1);
            INSERT INTO documents (
                id, project_id, original_filename, display_name, extension,
                mime_type, size_bytes, checksum_sha256, storage_provider,
                storage_key, uploaded_by, version, is_current_version,
                document_type, status
            ) VALUES (
                1, 1, 'spec.pdf', 'Spec', 'pdf', 'application/pdf', 10,
                '{HASH_A}', 'local', 'projects/1/spec', 1, 1, 1, 'General', 'Active'
            );
            INSERT INTO document_extractions (
                id, project_id, document_id, status, extraction_method,
                page_count, pages_processed, text_character_count, searchable,
                language, extractor_version, source_checksum
            ) VALUES (1, 1, 1, 'completed', 'embedded_text', 1, 1, 5, 1, 'eng', 'v1', '{HASH_A}');
            INSERT INTO preconstruction_review_sets (
                id, project_id, name, normalized_name, purpose, status, created_by
            ) VALUES (1, 1, 'Review', 'review', 'bid_scope_review', 'ready', 1);
            INSERT INTO preconstruction_review_sources (
                id, project_id, review_set_id, source_type, document_id,
                document_role, source_checksum, extraction_id, extraction_version,
                extraction_status, display_name_snapshot, added_by
            ) VALUES (1, 1, 1, 'document', 1, 'specification', '{HASH_A}', 1, 'v1',
                      'completed', 'Spec', 1);
            INSERT INTO preconstruction_analysis_runs (
                id, project_id, review_set_id, status, provider_profile,
                analysis_type, manifest_hash, manifest_json, source_count,
                template_version, schema_version, requested_by,
                current_attempt_count, max_attempts
            ) VALUES (1, 1, 1, 'completed', 'fake_test', 'scope_assertion_extraction',
                      '{HASH_B}', '{{}}', 1, 't1', 's1', 1, 1, 3);
            INSERT INTO preconstruction_analysis_attempts (
                id, project_id, run_id, attempt_number, provider_profile,
                provider_name, model_name, status, input_manifest_hash,
                output_schema_version, latency_ms, input_units, output_units
            ) VALUES (1, 1, 1, 1, 'fake_test', 'fake', 'fake-1', 'completed',
                      '{HASH_B}', 's1', 120, 400, 200);
            INSERT INTO preconstruction_preparation_runs (
                id, project_id, review_source_id, status, source_checksum,
                lineage_fingerprint, extraction_id, extraction_method,
                extractor_version, preparation_version,
                segmentation_policy_version, attempt_count, max_attempts, requested_by
            ) VALUES (1, 1, 1, 'completed', '{HASH_A}', '{HASH_C}', 1,
                      'embedded_text', 'v1', 'p1', 'seg1', 1, 3, 1);
            INSERT INTO preconstruction_content_snapshots (
                id, project_id, review_source_id, document_id, source_checksum,
                extraction_id, extraction_method, extractor_version,
                preparation_version, segmentation_policy_version,
                lineage_fingerprint, status, page_count, segment_count,
                total_character_count, content_hash, preparation_run_id
            ) VALUES (1, 1, 1, 1, '{HASH_A}', 1, 'embedded_text', 'v1', 'p1', 'seg1',
                      '{HASH_C}', 'completed', 1, 1, 20, '{HASH_B}', 1);
            INSERT INTO preconstruction_content_pages (
                id, project_id, snapshot_id, page_number, extraction_method,
                character_count, page_text_hash, has_searchable_text, has_visual_content
            ) VALUES (1, 1, 1, 1, 'embedded_text', 20, '{HASH_A}', 1, 0);
            INSERT INTO preconstruction_content_segments (
                id, project_id, snapshot_id, page_id, segment_index, segment_type,
                text, normalized_text, text_hash, extraction_method
            ) VALUES (1, 1, 1, 1, 0, 'page_text', 'Provide LED fixtures',
                      'provide led fixtures', '{HASH_B}', 'embedded_text');
            INSERT INTO preconstruction_scope_assertion_sets (
                id, project_id, analysis_run_id, review_set_id, manifest_hash,
                taxonomy_version, schema_version, provider_profile, status,
                assertion_count, warning_count, content_hash
            ) VALUES (1, 1, 1, 1, '{HASH_B}', 'construction-scope-1',
                      'scope-assertion-1', 'fake_test', 'completed', 1, 0, '{HASH_A}');
            INSERT INTO preconstruction_scope_assertions (
                id, project_id, assertion_set_id, review_set_id, source_id, origin,
                concept_code, taxonomy_version, assertion_type, subject,
                inclusion_state, confidence, provider_assertion_key, status
            ) VALUES (1, 1, 1, 1, 1, 'provider', 'electrical.lighting_fixture',
                      'construction-scope-1', 'physical_item', 'LED fixtures',
                      'included', 0.8, 'key-1', 'accepted');
            INSERT INTO preconstruction_assertion_evidence (
                id, project_id, assertion_id, source_id, content_snapshot_id,
                content_page_id, content_segment_id, page_number, segment_index,
                text_hash, excerpt, evidence_role
            ) VALUES (1, 1, 1, 1, 1, 1, 1, 1, 0, '{HASH_B}', 'Provide LED fixtures', 'primary');
            INSERT INTO preconstruction_assertion_reviews (
                id, project_id, assertion_id, decision, reviewer_note, reviewed_by
            ) VALUES (1, 1, 1, 'accepted', 'Confirmed', 1);
            INSERT INTO preconstruction_comparison_plans (
                id, project_id, review_set_id, name, normalized_name,
                comparison_type, status, taxonomy_version, configuration_json,
                configuration_hash, created_by
            ) VALUES (1, 1, 1, 'Coverage', 'coverage', 'general_scope_coverage',
                      'locked', 'construction-scope-1', '{{}}', '{HASH_A}', 1);
            INSERT INTO preconstruction_finding_sets (
                id, project_id, review_set_id, comparison_plan_id, analysis_run_id,
                comparison_type, comparison_manifest_hash, taxonomy_version,
                schema_version, provider_profile, status, candidate_count,
                finding_count, warning_count, content_hash
            ) VALUES (1, 1, 1, 1, NULL, 'general_scope_coverage', '{HASH_B}',
                      'construction-scope-1', 'scope-comparison-1', 'deterministic',
                      'completed', 1, 1, 0, '{HASH_C}');
            INSERT INTO preconstruction_findings (
                id, project_id, finding_set_id, review_set_id, comparison_plan_id,
                finding_key, finding_type, severity, title, origin,
                deterministic_match_class, status
            ) VALUES (1, 1, 1, 1, 1, 'missing_coverage:1|', 'missing_coverage',
                      'high', 'Potential missing coverage', 'deterministic',
                      'none', 'accepted');
            INSERT INTO preconstruction_finding_reviews (
                id, project_id, finding_id, decision, reason_code,
                reviewer_note, reviewed_by
            ) VALUES (1, 1, 1, 'accepted', 'confirmed_gap', 'Confirmed', 1);
            INSERT INTO preconstruction_finding_follow_ups (
                id, project_id, finding_id, review_set_id, comparison_plan_id,
                finding_review_id, action_type, status, draft_title, draft_body,
                draft_template_version, created_by
            ) VALUES (1, 1, 1, 1, 1, 1, 'rfi', 'planned', 'Draft RFI',
                      'Please clarify.', 'scope-follow-up-draft-1', 1);
            """
        )
        connection.commit()

    def snapshot(self, connection, tables):
        return {
            table: connection.execute(
                f"SELECT * FROM {table} ORDER BY id"
            ).fetchall()
            for table in tables
        }

    def test_table_constraints_no_backfill_and_history_preserved(self):
        command.upgrade(self.config, PREVIOUS_REVISION)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            self.seed(connection)
            existing = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertNotIn(METRICS_TABLE, existing)
            before = self.snapshot(connection, IMMUTABLE_TABLES)

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
            self.assertIn(METRICS_TABLE, tables)

            # No backfill: an existing execution gains no synthesized metric.
            self.assertEqual(
                connection.execute(f"SELECT COUNT(*) FROM {METRICS_TABLE}").fetchone()[0],
                0,
            )

            # Every historical M18.1-M18.5 row is byte-identical.
            after = self.snapshot(connection, IMMUTABLE_TABLES)
            for table in IMMUTABLE_TABLES:
                with self.subTest(unchanged=table):
                    self.assertEqual(before[table], after[table])

            index_names = {
                row[1]
                for row in connection.execute(f"PRAGMA index_list({METRICS_TABLE})")
            }
            self.assertIn(
                "ix_preconstruction_execution_metrics_project_listing", index_names
            )

            ddl = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                (METRICS_TABLE,),
            ).fetchone()[0]
            for constraint in (
                "ck_preconstruction_execution_metrics_kind",
                "ck_preconstruction_execution_metrics_positive",
                "ck_preconstruction_execution_metrics_query_count",
                "ck_preconstruction_execution_metrics_response_bytes",
                "ck_preconstruction_execution_metrics_input_units",
                "ck_preconstruction_execution_metrics_output_units",
                "ck_preconstruction_execution_metrics_cost",
                "ck_preconstruction_execution_metrics_budget_reason",
                "uq_preconstruction_execution_metrics_execution",
            ):
                with self.subTest(constraint=constraint):
                    self.assertIn(constraint, ddl)

            connection.executescript(
                f"""
                INSERT INTO {METRICS_TABLE} (
                    id, project_id, execution_kind, execution_id, metrics_version,
                    duration_ms, phase_durations_json, input_units, output_units,
                    estimated_cost_micros, manifest_reused
                ) VALUES (1, 1, 'scope_comparison', 1, 'preconstruction-execution-1',
                          42, '{{"total":42}}', NULL, NULL, NULL, 0);
                INSERT INTO {METRICS_TABLE} (
                    id, project_id, execution_kind, execution_id, metrics_version,
                    duration_ms, input_units, output_units, estimated_cost_micros
                ) VALUES (2, 1, 'analysis_attempt', 1, 'preconstruction-execution-1',
                          120, 400, 200, 6000);
                """
            )
            connection.commit()

            invalid = {
                "execution kind": f"""
                    INSERT INTO {METRICS_TABLE} (
                        id, project_id, execution_kind, execution_id,
                        metrics_version, duration_ms
                    ) VALUES (90, 1, 'invented', 1, 'v1', 1)
                """,
                "negative duration": f"""
                    INSERT INTO {METRICS_TABLE} (
                        id, project_id, execution_kind, execution_id,
                        metrics_version, duration_ms
                    ) VALUES (91, 1, 'scope_comparison', 2, 'v1', -1)
                """,
                "negative cost": f"""
                    INSERT INTO {METRICS_TABLE} (
                        id, project_id, execution_kind, execution_id,
                        metrics_version, duration_ms, estimated_cost_micros
                    ) VALUES (92, 1, 'scope_comparison', 3, 'v1', 1, -5)
                """,
                "budget reason": f"""
                    INSERT INTO {METRICS_TABLE} (
                        id, project_id, execution_kind, execution_id,
                        metrics_version, duration_ms, budget_stop_reason
                    ) VALUES (93, 1, 'scope_comparison', 4, 'v1', 1, 'invented')
                """,
                "duplicate execution": f"""
                    INSERT INTO {METRICS_TABLE} (
                        id, project_id, execution_kind, execution_id,
                        metrics_version, duration_ms
                    ) VALUES (94, 1, 'scope_comparison', 1, 'v1', 1)
                """,
                "zero execution id": f"""
                    INSERT INTO {METRICS_TABLE} (
                        id, project_id, execution_kind, execution_id,
                        metrics_version, duration_ms
                    ) VALUES (95, 1, 'scope_comparison', 0, 'v1', 1)
                """,
            }
            for label, statement in invalid.items():
                with self.subTest(constraint=label):
                    with self.assertRaises(sqlite3.IntegrityError):
                        connection.execute(statement)
                    connection.rollback()

            # A metric never restricts the execution it measures: deleting the
            # measured finding set leaves the metric row intact.
            connection.execute("DELETE FROM preconstruction_finding_sets WHERE id = 1")
            connection.commit()
            self.assertEqual(
                connection.execute(
                    f"SELECT COUNT(*) FROM {METRICS_TABLE} "
                    "WHERE execution_kind = 'scope_comparison'"
                ).fetchone()[0],
                1,
            )

            # Project deletion cascades metrics with the rest of the graph.
            connection.execute("DELETE FROM projects WHERE id = 1")
            connection.commit()
            self.assertEqual(
                connection.execute(f"SELECT COUNT(*) FROM {METRICS_TABLE}").fetchone()[0],
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
            self.assertNotIn(METRICS_TABLE, tables)
            # M18.5 and earlier survive the downgrade untouched.
            self.assertIn("preconstruction_finding_follow_ups", tables)
            self.assertIn("preconstruction_findings", tables)

        command.upgrade(self.config, "head")
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertIn(METRICS_TABLE, tables)

        script = ScriptDirectory.from_config(self.config)
        heads = list(script.get_heads())
        self.assertEqual(heads, [CURRENT_REVISION])


if __name__ == "__main__":
    unittest.main()
