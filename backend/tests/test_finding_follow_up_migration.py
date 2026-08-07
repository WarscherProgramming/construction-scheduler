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
PREVIOUS_REVISION = "d5a3f9c14e28"
CURRENT_REVISION = "e2b8d4f7c103"

FOLLOW_UP_TABLE = "preconstruction_finding_follow_ups"

# Historical M18.1-M18.4 tables that a follow-up must never rewrite.
IMMUTABLE_TABLES = (
    "preconstruction_scope_assertions",
    "preconstruction_assertion_evidence",
    "preconstruction_assertion_reviews",
    "preconstruction_finding_sets",
    "preconstruction_findings",
    "preconstruction_finding_assertions",
    "preconstruction_finding_evidence",
    "preconstruction_finding_reviews",
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


class FindingFollowUpMigrationTests(unittest.TestCase):
    def setUp(self):
        handle, database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.database_path = Path(database_path)
        self.previous_database_url = os.environ.get("DATABASE_URL")
        self.previous_secret_key = os.environ.get("SECRET_KEY")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path.as_posix()}"
        os.environ["SECRET_KEY"] = "follow-up-migration-test-secret-value"
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
        """A complete M18.1-M18.4 graph with one accepted finding."""
        connection.executescript(
            f"""
            INSERT INTO users (id, email, hashed_password)
            VALUES (1, 'follow@example.com', 'hash');
            INSERT INTO projects (id, name, user_id) VALUES (1, 'Follow', 1);
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
            INSERT INTO rfis (
                id, project_id, number, subject, question, submitted_date, status
            ) VALUES (1, 1, 'RFI-001', 'Lighting scope', 'Please clarify.',
                      '2026-08-06', 'Open');
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
            INSERT INTO preconstruction_finding_assertions (
                id, project_id, finding_id, assertion_id, assertion_review_id,
                side, link_role, match_class
            ) VALUES (1, 1, 1, 1, 1, 'requirement', 'primary', 'none');
            INSERT INTO preconstruction_finding_evidence (
                id, project_id, finding_id, assertion_id, assertion_evidence_id,
                source_id, content_snapshot_id, content_page_id,
                content_segment_id, page_number, segment_index, text_hash,
                excerpt, evidence_role
            ) VALUES (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, '{HASH_B}',
                      'Provide LED fixtures', 'primary');
            INSERT INTO preconstruction_finding_reviews (
                id, project_id, finding_id, decision, reason_code,
                reviewer_note, reviewed_by
            ) VALUES (1, 1, 1, 'accepted', 'confirmed_gap', 'Confirmed', 1);
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

    def test_table_constraints_indexes_no_backfill_and_history_preserved(self):
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
            self.assertNotIn(FOLLOW_UP_TABLE, existing)
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
            self.assertIn(FOLLOW_UP_TABLE, tables)

            # No backfill: no accepted finding silently gains a follow-up.
            self.assertEqual(
                connection.execute(
                    f"SELECT COUNT(*) FROM {FOLLOW_UP_TABLE}"
                ).fetchone()[0],
                0,
            )

            # Every historical M18.1-M18.4 row is byte-identical.
            after = self.snapshot(connection, IMMUTABLE_TABLES)
            for table in IMMUTABLE_TABLES:
                with self.subTest(unchanged=table):
                    self.assertEqual(before[table], after[table])

            index_names = {
                row[1]
                for row in connection.execute(f"PRAGMA index_list({FOLLOW_UP_TABLE})")
            }
            for expected in (
                "uq_preconstruction_finding_follow_ups_active_action",
                "ix_preconstruction_finding_follow_ups_plan_listing",
                "ix_preconstruction_finding_follow_ups_finding_order",
                "ix_preconstruction_finding_follow_ups_target",
            ):
                with self.subTest(index=expected):
                    self.assertIn(expected, index_names)

            ddl = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                (FOLLOW_UP_TABLE,),
            ).fetchone()[0]
            for constraint in (
                "ck_preconstruction_finding_follow_ups_action",
                "ck_preconstruction_finding_follow_ups_status",
                "ck_preconstruction_finding_follow_ups_target_type",
                "ck_preconstruction_finding_follow_ups_target_pair",
                "ck_preconstruction_finding_follow_ups_planned_has_no_target",
                "ck_preconstruction_finding_follow_ups_linked_has_target",
                "ck_preconstruction_finding_follow_ups_title_nonblank",
                "ck_preconstruction_finding_follow_ups_note_length",
                "ck_preconstruction_finding_follow_ups_closure_identity",
            ):
                with self.subTest(constraint=constraint):
                    self.assertIn(constraint, ddl)

            connection.executescript(
                f"""
                INSERT INTO {FOLLOW_UP_TABLE} (
                    id, project_id, finding_id, review_set_id, comparison_plan_id,
                    finding_review_id, action_type, status, draft_title, draft_body,
                    draft_template_version, created_by
                ) VALUES (1, 1, 1, 1, 1, 1, 'rfi', 'planned', 'Draft RFI',
                          'Please clarify.', 'scope-follow-up-draft-1', 1);
                INSERT INTO {FOLLOW_UP_TABLE} (
                    id, project_id, finding_id, review_set_id, comparison_plan_id,
                    finding_review_id, action_type, status, target_type, target_id,
                    draft_title, draft_body, draft_template_version, created_by,
                    linked_by, linked_at
                ) VALUES (2, 1, 1, 1, 1, 1, 'change_order', 'linked', 'change_order',
                          1, 'Draft CO', 'Scope difference.',
                          'scope-follow-up-draft-1', 1, 1, '2026-08-06 00:00:00');
                """
            )
            connection.commit()

            invalid = {
                "action type": f"""
                    INSERT INTO {FOLLOW_UP_TABLE} (
                        id, project_id, finding_id, review_set_id,
                        comparison_plan_id, action_type, status, draft_title,
                        draft_body, draft_template_version, created_by
                    ) VALUES (90, 1, 1, 1, 1, 'invented', 'planned', 'T', 'B',
                              'v1', 1)
                """,
                "status": f"""
                    INSERT INTO {FOLLOW_UP_TABLE} (
                        id, project_id, finding_id, review_set_id,
                        comparison_plan_id, action_type, status, draft_title,
                        draft_body, draft_template_version, created_by
                    ) VALUES (91, 1, 1, 1, 1, 'submittal', 'invented', 'T', 'B',
                              'v1', 1)
                """,
                "target type": f"""
                    INSERT INTO {FOLLOW_UP_TABLE} (
                        id, project_id, finding_id, review_set_id,
                        comparison_plan_id, action_type, status, target_type,
                        target_id, draft_title, draft_body,
                        draft_template_version, created_by, linked_by, linked_at
                    ) VALUES (92, 1, 1, 1, 1, 'submittal', 'linked', 'daily_log',
                              1, 'T', 'B', 'v1', 1, 1, '2026-08-06 00:00:00')
                """,
                "half a target": f"""
                    INSERT INTO {FOLLOW_UP_TABLE} (
                        id, project_id, finding_id, review_set_id,
                        comparison_plan_id, action_type, status, target_type,
                        draft_title, draft_body, draft_template_version, created_by
                    ) VALUES (93, 1, 1, 1, 1, 'submittal', 'linked', 'rfi', 'T',
                              'B', 'v1', 1)
                """,
                "planned row carries a target": f"""
                    INSERT INTO {FOLLOW_UP_TABLE} (
                        id, project_id, finding_id, review_set_id,
                        comparison_plan_id, action_type, status, target_type,
                        target_id, draft_title, draft_body,
                        draft_template_version, created_by
                    ) VALUES (94, 1, 1, 1, 1, 'submittal', 'planned', 'rfi', 1,
                              'T', 'B', 'v1', 1)
                """,
                "linked row without a target": f"""
                    INSERT INTO {FOLLOW_UP_TABLE} (
                        id, project_id, finding_id, review_set_id,
                        comparison_plan_id, action_type, status, draft_title,
                        draft_body, draft_template_version, created_by
                    ) VALUES (95, 1, 1, 1, 1, 'submittal', 'linked', 'T', 'B',
                              'v1', 1)
                """,
                "blank draft title": f"""
                    INSERT INTO {FOLLOW_UP_TABLE} (
                        id, project_id, finding_id, review_set_id,
                        comparison_plan_id, action_type, status, draft_title,
                        draft_body, draft_template_version, created_by
                    ) VALUES (96, 1, 1, 1, 1, 'submittal', 'planned', '   ', 'B',
                              'v1', 1)
                """,
                "closed row without a closer": f"""
                    INSERT INTO {FOLLOW_UP_TABLE} (
                        id, project_id, finding_id, review_set_id,
                        comparison_plan_id, action_type, status, draft_title,
                        draft_body, draft_template_version, created_by
                    ) VALUES (97, 1, 1, 1, 1, 'submittal', 'completed', 'T', 'B',
                              'v1', 1)
                """,
                "duplicate active action for one finding": f"""
                    INSERT INTO {FOLLOW_UP_TABLE} (
                        id, project_id, finding_id, review_set_id,
                        comparison_plan_id, action_type, status, draft_title,
                        draft_body, draft_template_version, created_by
                    ) VALUES (98, 1, 1, 1, 1, 'rfi', 'planned', 'T', 'B', 'v1', 1)
                """,
            }
            for label, statement in invalid.items():
                with self.subTest(constraint=label):
                    with self.assertRaises(sqlite3.IntegrityError):
                        connection.execute(statement)
                    connection.rollback()

            # A cancelled row frees the action for a genuinely new round.
            connection.execute(
                f"""
                UPDATE {FOLLOW_UP_TABLE}
                SET status = 'cancelled', closed_by = 1,
                    closed_at = '2026-08-06 01:00:00', closure_note = 'Not needed'
                WHERE id = 1
                """
            )
            connection.execute(
                f"""
                INSERT INTO {FOLLOW_UP_TABLE} (
                    id, project_id, finding_id, review_set_id, comparison_plan_id,
                    action_type, status, draft_title, draft_body,
                    draft_template_version, created_by
                ) VALUES (3, 1, 1, 1, 1, 'rfi', 'planned', 'Second RFI', 'B',
                          'v1', 1)
                """
            )
            connection.commit()

            # A follow-up never restricts the record it points at: the link is
            # an untyped reference, so deleting the RFI leaves history intact.
            connection.execute("DELETE FROM rfis WHERE id = 1")
            connection.commit()
            self.assertEqual(
                connection.execute(
                    f"SELECT COUNT(*) FROM {FOLLOW_UP_TABLE} WHERE target_type = 'change_order'"
                ).fetchone()[0],
                1,
            )

            # Findings still cannot lose their cited evidence.
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM preconstruction_assertion_evidence WHERE id = 1"
                )
            connection.rollback()

            # Project deletion cascades the advisory graph including follow-ups.
            connection.execute("DELETE FROM projects WHERE id = 1")
            connection.commit()
            self.assertEqual(
                connection.execute(
                    f"SELECT COUNT(*) FROM {FOLLOW_UP_TABLE}"
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
            self.assertNotIn(FOLLOW_UP_TABLE, tables)
            # The M18.4 comparison tables survive the downgrade untouched.
            self.assertIn("preconstruction_findings", tables)

        command.upgrade(self.config, "head")
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertIn(FOLLOW_UP_TABLE, tables)

        script = ScriptDirectory.from_config(self.config)
        heads = list(script.get_heads())
        self.assertEqual(heads, [CURRENT_REVISION])


if __name__ == "__main__":
    unittest.main()
