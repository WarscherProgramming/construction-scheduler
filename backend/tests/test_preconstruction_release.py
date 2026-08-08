"""M18.7 release closeout guards for the AI Preconstruction platform.

These tests assert the boundaries the M18 documentation claims, so a future
change that quietly breaks one fails here rather than in production. They add
no behaviour: every assertion describes something M18.1-M18.6 already does.
"""

import inspect
import re
import unittest

from app.api import routes_preconstruction as routes
from app.main import app
from app.preconstruction.comparison import (
    FINDING_ORIGINS,
    FINDING_SEVERITIES,
    FINDING_STATUSES,
    FINDING_TYPES,
    MATCH_CLASSES,
)
from app.preconstruction.execution import EXECUTION_KINDS
from app.preconstruction.follow_up import (
    FOLLOW_UP_ACTION_BY_VALUE,
    FOLLOW_UP_STATUSES,
)
from app.preconstruction.roles import (
    ANALYSIS_TYPES,
    DOCUMENT_ROLE_BY_VALUE,
    REVIEW_PURPOSES,
)
from app.models.preconstruction import (
    PreconstructionAnalysisRun,
    PreconstructionReviewSet,
    PreconstructionReviewSource,
)
from app.models.preconstruction_metrics import PreconstructionExecutionMetric
from app.models.scope_comparison import PreconstructionFinding
from app.models.scope_follow_up import PreconstructionFindingFollowUp
from app.schemas.preconstruction import AnalysisType


PRECONSTRUCTION_PREFIX = "/projects/{project_id}/preconstruction"


def check_values(model, constraint_name):
    """The exact literal set one CHECK constraint permits."""
    for constraint in model.__table__.constraints:
        if getattr(constraint, "name", "") == constraint_name:
            return set(re.findall(r"'([^']+)'", str(constraint.sqltext)))
    return None


class LabelTotalityTests(unittest.TestCase):
    """Every stored controlled value must have a display label.

    Response builders look these maps up directly, so a value the database
    permits but the map omits turns a whole listing route into a 500. This
    caught exactly that defect for the two comparison analysis types.
    """

    CASES = (
        ("analysis type", ANALYSIS_TYPES, PreconstructionAnalysisRun,
         "ck_preconstruction_analysis_runs_type"),
        ("review purpose", REVIEW_PURPOSES, PreconstructionReviewSet,
         "ck_preconstruction_review_sets_purpose"),
        ("document role", DOCUMENT_ROLE_BY_VALUE, PreconstructionReviewSource,
         "ck_preconstruction_review_sources_role"),
        ("finding type", FINDING_TYPES, PreconstructionFinding,
         "ck_preconstruction_findings_type"),
        ("finding severity", FINDING_SEVERITIES, PreconstructionFinding,
         "ck_preconstruction_findings_severity"),
        ("finding status", FINDING_STATUSES, PreconstructionFinding,
         "ck_preconstruction_findings_status"),
        ("finding origin", FINDING_ORIGINS, PreconstructionFinding,
         "ck_preconstruction_findings_origin"),
        ("match class", MATCH_CLASSES, PreconstructionFinding,
         "ck_preconstruction_findings_match_class"),
        ("follow-up action", FOLLOW_UP_ACTION_BY_VALUE,
         PreconstructionFindingFollowUp,
         "ck_preconstruction_finding_follow_ups_action"),
        ("follow-up status", FOLLOW_UP_STATUSES, PreconstructionFindingFollowUp,
         "ck_preconstruction_finding_follow_ups_status"),
        ("execution kind", EXECUTION_KINDS, PreconstructionExecutionMetric,
         "ck_preconstruction_execution_metrics_kind"),
    )

    def test_every_label_map_covers_its_database_allowlist(self):
        for label, mapping, model, constraint in self.CASES:
            with self.subTest(vocabulary=label):
                allowed = check_values(model, constraint)
                self.assertIsNotNone(allowed, f"{constraint} not found")
                self.assertEqual(
                    set(mapping),
                    allowed,
                    f"{label}: database permits {sorted(allowed - set(mapping))} "
                    "with no display label",
                )

    def test_labeling_a_type_does_not_make_it_creatable(self):
        """Comparison runs are labeled but still refused over HTTP.

        Labels exist so a stored row renders; the request literal is what
        governs what a client may create, and it deliberately omits both
        comparison types.
        """
        creatable = set(AnalysisType.__args__)
        self.assertNotIn("scope_comparison", creatable)
        self.assertNotIn("scope_comparison_validation", creatable)
        self.assertTrue(creatable.issubset(set(ANALYSIS_TYPES)))


class PreconstructionBoundaryTests(unittest.TestCase):
    """The structural invariants every M18 milestone promised."""

    def preconstruction_routes(self):
        return [
            route
            for route in app.routes
            if getattr(route, "path", "").startswith(PRECONSTRUCTION_PREFIX)
        ]

    def test_every_route_is_project_scoped_and_ownership_gated(self):
        source = inspect.getsource(routes)
        blocks = re.split(r"\n@router\.", source)[1:]
        self.assertEqual(len(blocks), 49)
        for block in blocks:
            name = re.search(r"\ndef (\w+)", block)
            signature = block.split("):")[0]
            with self.subTest(route=name.group(1) if name else "?"):
                self.assertIn("get_owned_project", signature)

    def test_no_route_commits_its_own_transaction(self):
        source = inspect.getsource(routes)
        self.assertNotIn("db.commit()", source)
        self.assertNotIn("db.rollback()", source)

    def test_the_router_is_mounted_once_under_one_prefix(self):
        paths = [route.path for route in self.preconstruction_routes()]
        self.assertEqual(len(paths), 49)
        self.assertEqual(len(paths), len({(p, tuple(sorted(r.methods)))
                                          for p, r in
                                          zip(paths, self.preconstruction_routes())}))

    def test_preconstruction_never_writes_an_authoritative_workflow_table(self):
        """No preconstruction service constructs a construction record."""
        from app.services import (
            preconstruction,
            preconstruction_comparison,
            preconstruction_content,
            preconstruction_execution,
            preconstruction_follow_up,
            preconstruction_scope,
        )

        forbidden = (
            "RFI(",
            "ChangeOrder(",
            "Submittal(",
            "PunchItem(",
            "EntityRelationship(",
            "Task(",
            "DrawingRevision(",
            "Document(",
        )
        for module in (
            preconstruction,
            preconstruction_comparison,
            preconstruction_content,
            preconstruction_execution,
            preconstruction_follow_up,
            preconstruction_scope,
        ):
            source = inspect.getsource(module)
            for symbol in forbidden:
                with self.subTest(module=module.__name__, symbol=symbol):
                    self.assertNotIn(symbol, source)


class ProviderBoundaryTests(unittest.TestCase):
    def test_the_factory_allowlist_admits_no_live_provider(self):
        from app.preconstruction import factory

        source = inspect.getsource(factory)
        self.assertIn('config.provider == "fake_test"', source)
        # No dynamic import, class path, or SDK can reach the factory.
        for forbidden in ("import_module", "__import__", "eval(", "getattr(", "exec("):
            with self.subTest(construct=forbidden):
                self.assertNotIn(forbidden, source)

    def test_production_defaults_disable_the_provider_and_ocr(self):
        from pathlib import Path

        example = Path(__file__).resolve().parents[1] / ".env.example"
        text = example.read_text(encoding="utf-8")
        for required in (
            "PRECONSTRUCTION_AI_ENABLED=false",
            "PRECONSTRUCTION_AI_PROVIDER=disabled",
            "PRECONSTRUCTION_AI_FAKE_PROVIDER_ALLOWED=false",
        ):
            with self.subTest(setting=required):
                self.assertIn(required, text)

    def test_every_documented_setting_exists_in_the_example_env(self):
        """The deployment contract must list every preconstruction setting."""
        from pathlib import Path

        from app.core import config as config_module

        source = inspect.getsource(config_module)
        declared = set(re.findall(r'"(PRECONSTRUCTION_[A-Z0-9_]+)"', source))
        example = (
            Path(__file__).resolve().parents[1] / ".env.example"
        ).read_text(encoding="utf-8")
        documented = set(re.findall(r"^(PRECONSTRUCTION_[A-Z0-9_]+)=", example, re.M))
        missing = sorted(declared - documented)
        self.assertEqual(missing, [], f"undocumented settings: {missing}")


class ImmutableRecordTests(unittest.TestCase):
    """Records the platform promises never to rewrite stay append-only."""

    APPEND_ONLY_MODELS = (
        ("preconstruction_assertion_reviews", "app.models.scope_assertion",
         "PreconstructionAssertionReview"),
        ("preconstruction_finding_reviews", "app.models.scope_comparison",
         "PreconstructionFindingReview"),
        ("preconstruction_execution_metrics", "app.models.preconstruction_metrics",
         "PreconstructionExecutionMetric"),
    )

    def test_append_only_tables_carry_no_update_timestamp(self):
        """An ``updated_at`` column would imply a row may be rewritten."""
        from importlib import import_module

        for table, module_path, class_name in self.APPEND_ONLY_MODELS:
            model = getattr(import_module(module_path), class_name)
            with self.subTest(table=table):
                columns = {column.name for column in model.__table__.columns}
                self.assertNotIn("updated_at", columns)

    def test_immutable_content_is_protected_by_restrict(self):
        """Cited evidence and snapshots cannot be deleted out from under a finding."""
        from app.models.scope_assertion import PreconstructionAssertionEvidence
        from app.models.scope_comparison import PreconstructionFindingEvidence

        for model, column_name in (
            (PreconstructionAssertionEvidence, "content_segment_id"),
            (PreconstructionAssertionEvidence, "content_snapshot_id"),
            (PreconstructionFindingEvidence, "assertion_evidence_id"),
            (PreconstructionFindingEvidence, "content_segment_id"),
        ):
            with self.subTest(table=model.__tablename__, column=column_name):
                column = model.__table__.columns[column_name]
                key = list(column.foreign_keys)[0]
                self.assertEqual(key.ondelete, "RESTRICT")


class MigrationChainTests(unittest.TestCase):
    def test_the_chain_is_linear_with_a_single_head(self):
        from pathlib import Path

        from alembic.config import Config
        from alembic.script import ScriptDirectory

        backend = Path(__file__).resolve().parents[1]
        config = Config(str(backend / "alembic.ini"))
        config.set_main_option("script_location", str(backend / "alembic"))
        script = ScriptDirectory.from_config(config)

        heads = list(script.get_heads())
        self.assertEqual(len(heads), 1, heads)
        self.assertEqual(heads[0], "f3d6a8b2c517")

        # Every revision has exactly one parent, so the chain never branches.
        revisions = list(script.walk_revisions())
        for revision in revisions:
            with self.subTest(revision=revision.revision):
                parents = revision.down_revision
                if parents is None:
                    continue
                self.assertIsInstance(parents, str, "branching migration chain")

    def test_the_six_m18_migrations_are_present_and_ordered(self):
        from pathlib import Path

        from alembic.config import Config
        from alembic.script import ScriptDirectory

        backend = Path(__file__).resolve().parents[1]
        config = Config(str(backend / "alembic.ini"))
        config.set_main_option("script_location", str(backend / "alembic"))
        script = ScriptDirectory.from_config(config)

        expected = [
            "a8f4c2d6e190",
            "b9e5d3f7a201",
            "c1f7b4e28d35",
            "d5a3f9c14e28",
            "e2b8d4f7c103",
            "f3d6a8b2c517",
        ]
        chain = [item.revision for item in script.walk_revisions()]
        positions = [chain.index(revision) for revision in expected]
        # walk_revisions yields newest first, so positions must descend.
        self.assertEqual(positions, sorted(positions, reverse=True))
        for parent, child in zip(expected, expected[1:]):
            with self.subTest(child=child):
                self.assertEqual(script.get_revision(child).down_revision, parent)


if __name__ == "__main__":
    unittest.main()
