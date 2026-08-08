import json
from time import perf_counter

from sqlalchemy import event

from app.api.dependencies import get_preconstruction_execution_config
from app.core.config import PreconstructionExecutionConfig
from app.main import app
from app.models.preconstruction_metrics import PreconstructionExecutionMetric
from app.preconstruction import evaluation as E
from app.preconstruction import execution as X
from app.preconstruction.matching import tokenize
from tests.test_preconstruction_comparison import ComparisonTestBase


def execution_config(**overrides):
    values = {
        "max_comparison_pairs": 1_000_000,
        "persist_chunk_size": 500,
        "worker_max_runtime_seconds": 240,
        "finding_evidence_limit": 10,
        "finding_max_evidence_limit": 20,
        "metrics_retention_rows": 500,
        "cost_input_micros_per_unit": 0,
        "cost_output_micros_per_unit": 0,
        "metrics_enabled": True,
        "diagnostics_enabled": True,
        "metrics_version": "preconstruction-execution-1",
    }
    values.update(overrides)
    return PreconstructionExecutionConfig(**values)


class ExecutionTestBase(ComparisonTestBase):
    def setUp(self):
        super().setUp()
        self.execution_config = execution_config()
        app.dependency_overrides[get_preconstruction_execution_config] = (
            lambda: self.execution_config
        )

    def comparison_plan(self):
        review, _spec, _proposal, _assertions = self.reviewed_review_set()
        return self.create_plan(review["id"])


class ExecutionPrimitiveTests(ExecutionTestBase):
    def test_pair_budget_is_exact_arithmetic_not_a_heuristic(self):
        budget = X.estimate_pair_budget(100, 50, 10_000)
        self.assertEqual(budget.estimated_pairs, 5_000)
        self.assertTrue(budget.within_budget)
        tight = X.estimate_pair_budget(1_000, 1_000, 10_000)
        self.assertEqual(tight.estimated_pairs, 1_000_000)
        self.assertFalse(tight.within_budget)
        # Degenerate populations never produce a negative or surprising count.
        self.assertEqual(X.estimate_pair_budget(0, 500, 10).estimated_pairs, 0)
        self.assertEqual(X.estimate_pair_budget(-5, 5, 10).estimated_pairs, 0)

    def test_phase_timer_accepts_only_controlled_phases(self):
        timer = X.PhaseTimer()
        with timer.measure("resolve"):
            pass
        timer.record("match", 0.01)
        payload = timer.payload()
        self.assertIn("resolve", payload)
        self.assertGreaterEqual(payload["match"], 10)
        self.assertIn("total", payload)
        for phase in payload:
            with self.subTest(phase=phase):
                self.assertIn(phase, X.EXECUTION_PHASES)
        with self.assertRaises(ValueError):
            timer.record("invented", 1.0)
        with self.assertRaises(ValueError):
            timer.measure("invented")

    def test_cost_is_absent_rather_than_fabricated_when_no_rate_is_set(self):
        # No configured rate means no cost, not a cost of zero.
        self.assertIsNone(X.estimate_cost_micros(1_000, 500, 0, 0))
        self.assertIsNone(X.format_cost_micros(None))
        # A configured rate produces exact integer micro-units.
        self.assertEqual(X.estimate_cost_micros(1_000, 500, 3, 6), 6_000)
        self.assertEqual(X.estimate_cost_micros(None, None, 3, 6), 0)
        self.assertEqual(X.format_cost_micros(6_000), "0.006000")

    def test_execution_metrics_rejects_unknown_vocabulary(self):
        for kwargs in (
            {"execution_kind": "invented", "execution_id": 1},
            {
                "execution_kind": "scope_comparison",
                "execution_id": 1,
                "phase_durations": {"invented": 1},
            },
            {
                "execution_kind": "scope_comparison",
                "execution_id": 1,
                "budget_stop_reason": "invented",
            },
        ):
            with self.subTest(kwargs=sorted(kwargs)):
                with self.assertRaises(ValueError):
                    X.ExecutionMetrics(**kwargs)


class EvaluationSuiteTests(ExecutionTestBase):
    def test_deterministic_golden_suite_passes_and_is_reproducible(self):
        first = E.evaluate_matching()
        second = E.evaluate_matching()
        self.assertGreaterEqual(first.total, 10)
        self.assertEqual(first.failed, 0, first.payload()["failures"])
        # Identical engine behaviour reproduces the digest exactly.
        self.assertEqual(first.digest(), second.digest())
        self.assertEqual(first.payload()["suite"], "deterministic")

    def test_every_fixture_uses_a_real_taxonomy_concept(self):
        from app.preconstruction import taxonomy

        codes = set()
        for case in E.MATCH_CASES:
            codes.add(case.requirement.concept_code)
            codes.add(case.coverage.concept_code)
        for case in E.COVERAGE_CASES:
            for item in (*case.requirements, *case.coverages):
                codes.add(item.concept_code)
        for code in sorted(codes):
            with self.subTest(concept=code):
                self.assertIsNotNone(taxonomy.resolve_concept(code))

    def test_a_regressed_expectation_is_reported_not_hidden(self):
        broken = E.MatchCase(
            "deliberately_wrong_expectation",
            E.MATCH_CASES[0].requirement,
            E.MATCH_CASES[0].coverage,
            "none",
        )
        report = E.evaluate_matching(match_cases=(broken,), coverage_cases=())
        self.assertEqual(report.failed, 1)
        self.assertEqual(report.failures[0].outcome, "wrong_match_class")
        self.assertEqual(report.failures[0].expected, "none")
        self.assertEqual(report.failures[0].observed, "exact")

    def test_provider_evaluation_scores_agreement_never_correctness(self):
        report = E.evaluate_provider_dispositions(
            (
                E.DispositionCase("k1", "retain", "retain"),
                E.DispositionCase("k2", "retain", "reject"),
                E.DispositionCase(
                    "k3",
                    "retain",
                    "retain",
                    observed_finding_type="invented",
                    allowed_finding_types=("missing_coverage",),
                ),
            )
        )
        self.assertEqual(report.total, 3)
        self.assertEqual(report.passed, 1)
        self.assertEqual(
            {item.outcome for item in report.failures},
            {"wrong_disposition", "wrong_finding_type"},
        )
        # No evaluation outcome can accept, reject, or escalate anything.
        serialized = json.dumps(report.payload()).lower()
        for forbidden in ("accepted", "approve", "auto"):
            with self.subTest(term=forbidden):
                self.assertNotIn(forbidden, serialized)

    def test_evaluation_command_is_finite_and_touches_no_project_data(self):
        from app.commands.run_preconstruction_evaluation import main

        statements = []

        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", record)
        try:
            self.assertEqual(main([]), 0)
            self.assertEqual(main(["--json"]), 0)
        finally:
            event.remove(self.engine, "before_cursor_execute", record)
        self.assertEqual(statements, [])


class TokenizationPerformanceTests(ExecutionTestBase):
    def test_tokenization_is_memoized_without_changing_its_result(self):
        tokenize.cache_clear()
        value = "Recessed LED lighting fixtures in the north corridor"
        first = tokenize(value)
        second = tokenize(value)
        # Memoization is transparent: same input, same token set.
        self.assertEqual(first, second)
        self.assertIs(first, second)
        info = tokenize.cache_info()
        self.assertEqual(info.hits, 1)
        self.assertEqual(info.misses, 1)
        # Distinct inputs still tokenize independently.
        self.assertNotEqual(tokenize(value), tokenize("Storm drainage piping"))

    def test_repeated_comparison_reuses_cached_tokens(self):
        from app.preconstruction.matching import compare_assertions

        requirement = E.MATCH_CASES[0].requirement
        coverage = E.MATCH_CASES[0].coverage
        tokenize.cache_clear()
        baseline = compare_assertions(requirement, coverage)
        misses_after_first = tokenize.cache_info().misses
        for _ in range(200):
            self.assertEqual(compare_assertions(requirement, coverage), baseline)
        # 200 further comparisons add no new tokenization work at all.
        self.assertEqual(tokenize.cache_info().misses, misses_after_first)


class ComparisonExecutionTests(ExecutionTestBase):
    def test_a_run_resolves_the_population_once(self):
        plan = self.comparison_plan()
        from app.services import preconstruction_comparison as C

        calls = {"count": 0}
        original = C.resolve_eligible_assertions

        def counted(*args, **kwargs):
            calls["count"] += 1
            return original(*args, **kwargs)

        C.resolve_eligible_assertions = counted
        try:
            response = self.client.post(
                f"{self.base()}/comparison-plans/{plan['id']}/runs",
                json={},
                headers=self.owner_headers,
            )
        finally:
            C.resolve_eligible_assertions = original
        self.assertEqual(response.status_code, 201, response.text)
        # Readiness and candidate generation share one resolution.
        self.assertEqual(calls["count"], 1)

    def test_readiness_diagnostics_are_bounded_and_free_of_timing(self):
        plan = self.comparison_plan()
        path = f"{self.base()}/comparison-plans/{plan['id']}/readiness"
        first = self.client.get(path, headers=self.owner_headers).json()
        second = self.client.get(path, headers=self.owner_headers).json()
        # Readiness stays deterministic: no measured duration may appear.
        self.assertEqual(first, second)
        diagnostics = first["diagnostics"]
        self.assertIn("pair_budget", diagnostics)
        self.assertEqual(
            set(diagnostics),
            {
                "pair_budget",
                "persist_chunk_size",
                "finding_evidence_limit",
                "metrics_enabled",
            },
        )
        serialized = json.dumps(diagnostics)
        for forbidden in ("ms", "duration", "elapsed", "seconds"):
            with self.subTest(term=forbidden):
                self.assertNotIn(forbidden, serialized.lower())

    def test_pair_budget_refuses_rather_than_silently_truncating(self):
        self.execution_config = execution_config(max_comparison_pairs=1)
        app.dependency_overrides[get_preconstruction_execution_config] = (
            lambda: self.execution_config
        )
        plan = self.comparison_plan()
        readiness = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/readiness",
            headers=self.owner_headers,
        ).json()
        self.assertFalse(readiness["ready"])
        self.assertTrue(
            any("pair budget" in item for item in readiness["blockers"]),
            readiness["blockers"],
        )
        self.assertFalse(readiness["diagnostics"]["pair_budget"]["within_budget"])
        refused = self.client.post(
            f"{self.base()}/comparison-plans/{plan['id']}/runs",
            json={},
            headers=self.owner_headers,
        )
        self.assertEqual(refused.status_code, 422, refused.text)

    def test_run_records_one_metric_row_without_restating_counts(self):
        plan = self.comparison_plan()
        finding_set = self.run_comparison(plan["id"])
        with self.TestingSession() as db:
            rows = (
                db.query(PreconstructionExecutionMetric)
                .filter(
                    PreconstructionExecutionMetric.execution_kind == "scope_comparison"
                )
                .all()
            )
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row.execution_id, finding_set["id"])
            self.assertGreaterEqual(row.duration_ms, 0)
            self.assertFalse(row.manifest_reused)
            phases = json.loads(row.phase_durations_json)
            self.assertIn("total", phases)
            for phase in phases:
                with self.subTest(phase=phase):
                    self.assertIn(phase, X.EXECUTION_PHASES)
            columns = {column.name for column in row.__table__.columns}
        # The metric never restates counts the finding set already owns.
        for absent in ("candidate_count", "finding_count", "warning_count"):
            with self.subTest(column=absent):
                self.assertNotIn(absent, columns)

    def test_manifest_reuse_is_opt_in_and_never_rewrites_history(self):
        plan = self.comparison_plan()
        first = self.run_comparison(plan["id"])

        # Default behaviour is unchanged: a re-run creates a new immutable set.
        second = self.run_comparison(plan["id"])
        self.assertNotEqual(first["id"], second["id"])

        reused = self.client.post(
            f"{self.base()}/comparison-plans/{plan['id']}/runs",
            json={"reuse_identical_manifest": True},
            headers=self.owner_headers,
        )
        self.assertEqual(reused.status_code, 201, reused.text)
        body = reused.json()
        self.assertTrue(body["manifest_reused"])
        self.assertEqual(body["id"], second["id"])
        self.assertEqual(
            body["comparison_manifest_hash"], first["comparison_manifest_hash"]
        )

        sets = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/finding-sets",
            headers=self.owner_headers,
        ).json()
        # Reuse wrote nothing: still exactly the two historical sets.
        self.assertEqual(sets["total"], 2)

    def test_reuse_is_refused_once_the_pinned_manifest_changes(self):
        plan = self.comparison_plan()
        first = self.run_comparison(plan["id"])
        review_set_id = plan["review_set_id"]
        target = self.first_assertion(review_set_id)
        self.client.post(
            f"{self.base()}/assertions/{target['id']}/reviews",
            json={
                "decision": "needs_review",
                "reviewer_note": "Revisiting before comparison.",
            },
            headers=self.owner_headers,
        )
        reused = self.client.post(
            f"{self.base()}/comparison-plans/{plan['id']}/runs",
            json={"reuse_identical_manifest": True},
            headers=self.owner_headers,
        )
        self.assertEqual(reused.status_code, 201, reused.text)
        body = reused.json()
        # A changed review changes the manifest, so nothing is reused.
        self.assertFalse(body["manifest_reused"])
        self.assertNotEqual(body["id"], first["id"])
        self.assertNotEqual(
            body["comparison_manifest_hash"], first["comparison_manifest_hash"]
        )


class ResponseSizeTests(ExecutionTestBase):
    def test_evidence_limit_bounds_the_response_and_is_allowlisted(self):
        plan = self.comparison_plan()
        self.run_comparison(plan["id"])
        path = f"{self.base()}/comparison-plans/{plan['id']}/findings"

        default = self.client.get(path, headers=self.owner_headers)
        self.assertEqual(default.status_code, 200, default.text)
        self.assertEqual(default.json()["evidence_limit"], 10)

        trimmed = self.client.get(f"{path}?evidence_limit=0", headers=self.owner_headers)
        self.assertEqual(trimmed.status_code, 200, trimmed.text)
        payload = trimmed.json()
        self.assertEqual(payload["evidence_limit"], 0)
        for item in payload["items"]:
            with self.subTest(finding=item["id"]):
                self.assertEqual(item["evidence"], [])
        self.assertLessEqual(len(trimmed.content), len(default.content))

        # The cap is bounded by configuration even when a larger value is asked for.
        capped = self.client.get(
            f"{path}?evidence_limit=50", headers=self.owner_headers
        ).json()
        self.assertEqual(capped["evidence_limit"], 20)

        rejected = self.client.get(
            f"{path}?evidence_limit=51", headers=self.owner_headers
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)

    def test_summary_counts_use_one_grouped_scan(self):
        plan = self.comparison_plan()
        self.run_comparison(plan["id"])
        from app.services.preconstruction_comparison import finding_summary_counts

        statements = []

        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", record)
        try:
            with self.TestingSession() as db:
                summary = finding_summary_counts(db, self.project_id, plan["id"])
        finally:
            event.remove(self.engine, "before_cursor_execute", record)
        selects = [
            item for item in statements if item.strip().upper().startswith("SELECT")
        ]
        self.assertEqual(len(selects), 1, selects)
        self.assertGreaterEqual(summary["total"], 1)
        self.assertEqual(
            summary["total"],
            summary["proposed"]
            + summary["accepted"]
            + summary["rejected"]
            + summary["needs_review"]
            + summary["intentional_exclusion"]
            + summary["superseded"],
        )


class ExecutionMetricsApiTests(ExecutionTestBase):
    def test_metrics_route_is_bounded_owned_and_text_free(self):
        plan = self.comparison_plan()
        self.run_comparison(plan["id"])
        response = self.client.get(
            f"{self.base()}/execution-metrics", headers=self.owner_headers
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertGreaterEqual(payload["total"], 1)
        self.assertEqual(payload["limit"], 50)
        self.assertTrue(payload["metrics_enabled"])
        self.assertEqual(payload["metrics_version"], "preconstruction-execution-1")

        summary = payload["summary"]
        self.assertGreaterEqual(summary["total_executions"], 1)
        # No rate configured, so cost is reported absent rather than as zero.
        self.assertFalse(summary["cost_rate_configured"])
        self.assertIsNone(summary["estimated_cost_micros"])
        self.assertIsNone(summary["estimated_cost_display"])

        serialized = json.dumps(payload).lower()
        for forbidden in ("excerpt", "reviewer_note", "prompt", "rationale", "subject"):
            with self.subTest(term=forbidden):
                self.assertNotIn(forbidden, serialized)

    def test_metrics_filters_are_allowlisted(self):
        plan = self.comparison_plan()
        self.run_comparison(plan["id"])
        filtered = self.client.get(
            f"{self.base()}/execution-metrics?execution_kind=scope_comparison",
            headers=self.owner_headers,
        ).json()
        self.assertGreaterEqual(filtered["total"], 1)
        empty = self.client.get(
            f"{self.base()}/execution-metrics?execution_kind=evaluation_run",
            headers=self.owner_headers,
        ).json()
        self.assertEqual(empty["total"], 0)
        for query in ("execution_kind=invented", "limit=0", "limit=500"):
            with self.subTest(query=query):
                rejected = self.client.get(
                    f"{self.base()}/execution-metrics?{query}",
                    headers=self.owner_headers,
                )
                self.assertEqual(rejected.status_code, 422, rejected.text)

    def test_metrics_are_project_owned_and_never_mutable(self):
        plan = self.comparison_plan()
        self.run_comparison(plan["id"])
        denied = self.client.get(
            f"{self.base()}/execution-metrics", headers=self.other_headers
        )
        self.assertEqual(denied.status_code, 403, denied.text)
        anonymous = self.client.get(f"{self.base()}/execution-metrics")
        self.assertEqual(anonymous.status_code, 401, anonymous.text)
        # The metrics surface is read-only: there is no write route.
        for method in ("post", "put", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    f"{self.base()}/execution-metrics", headers=self.owner_headers
                )
                self.assertEqual(response.status_code, 405, response.text)

    def test_cost_is_computed_only_from_a_configured_rate(self):
        from app.services.preconstruction_execution import (
            execution_metrics_summary,
            record_execution_metrics,
        )

        priced = execution_config(
            cost_input_micros_per_unit=3, cost_output_micros_per_unit=6
        )
        with self.TestingSession() as db:
            record_execution_metrics(
                db,
                self.project_id,
                X.ExecutionMetrics(
                    execution_kind="analysis_attempt",
                    execution_id=4242,
                    duration_ms=120,
                    input_units=1_000,
                    output_units=500,
                ),
                priced,
                commit=True,
            )
            summary = execution_metrics_summary(
                db, self.project_id, "analysis_attempt"
            )
        self.assertTrue(summary["cost_rate_configured"])
        self.assertEqual(summary["estimated_cost_micros"], 6_000)
        self.assertEqual(summary["estimated_cost_display"], "0.006000")

    def test_metrics_failure_never_rolls_back_the_measured_work(self):
        from app.services.preconstruction_execution import record_execution_metrics

        plan = self.comparison_plan()
        finding_set = self.run_comparison(plan["id"])
        with self.TestingSession() as db:
            # A second row for the same execution is refused, not duplicated,
            # and leaves the session usable.
            duplicate = record_execution_metrics(
                db,
                self.project_id,
                X.ExecutionMetrics(
                    execution_kind="scope_comparison",
                    execution_id=finding_set["id"],
                    duration_ms=999,
                ),
                self.execution_config,
            )
            self.assertIsNotNone(duplicate)
            self.assertNotEqual(duplicate.duration_ms, 999)
            count = (
                db.query(PreconstructionExecutionMetric)
                .filter(
                    PreconstructionExecutionMetric.execution_kind == "scope_comparison",
                    PreconstructionExecutionMetric.execution_id == finding_set["id"],
                )
                .count()
            )
            self.assertEqual(count, 1)

    def test_metrics_can_be_disabled_without_affecting_the_work(self):
        self.execution_config = execution_config(metrics_enabled=False)
        app.dependency_overrides[get_preconstruction_execution_config] = (
            lambda: self.execution_config
        )
        plan = self.comparison_plan()
        finding_set = self.run_comparison(plan["id"])
        self.assertGreaterEqual(finding_set["finding_count"], 0)
        with self.TestingSession() as db:
            self.assertEqual(
                db.query(PreconstructionExecutionMetric)
                .filter(
                    PreconstructionExecutionMetric.execution_kind == "scope_comparison"
                )
                .count(),
                0,
            )


class ExecutionScaleTests(ExecutionTestBase):
    def test_matching_stays_bounded_as_the_population_grows(self):
        from app.preconstruction.matching import generate_coverage_candidates

        def population(count, role, offset):
            return [
                E._assertion(
                    offset + index,
                    concept_code="electrical.lighting_fixture",
                    subject=f"LED lighting fixture type {index}",
                    document_role=role,
                    specification_section="26 51 00",
                )
                for index in range(count)
            ]

        timings = {}
        for size in (10, 40, 80):
            requirements = population(size, "specification", 0)
            coverages = population(size, "proposal", 10_000)
            started = perf_counter()
            candidates, warnings = generate_coverage_candidates(
                requirements, coverages, covered_minimum="strong",
                maximum_candidates=500,
            )
            timings[size] = perf_counter() - started
            with self.subTest(size=size):
                self.assertLessEqual(len(candidates), 500)
                self.assertLess(timings[size], 10.0)
        # Growth stays in the documented quadratic envelope rather than
        # degenerating; this is a regression guard, not a benchmark.
        self.assertLess(timings[80], max(timings[10] * 200, 5.0))

    def test_persist_chunking_writes_every_row_exactly_once(self):
        self.execution_config = execution_config(persist_chunk_size=1)
        app.dependency_overrides[get_preconstruction_execution_config] = (
            lambda: self.execution_config
        )
        plan = self.comparison_plan()
        finding_set = self.run_comparison(plan["id"])
        listing = self.client.get(
            f"{self.base()}/comparison-plans/{plan['id']}/findings?limit=100",
            headers=self.owner_headers,
        ).json()
        self.assertEqual(listing["total"], finding_set["finding_count"])
        keys = [item["id"] for item in listing["items"]]
        self.assertEqual(len(keys), len(set(keys)))
