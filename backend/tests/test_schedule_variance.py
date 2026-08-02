import unittest

from sqlalchemy import event

from app.models.task import Task
from app.services.schedule_baseline import get_schedule_variance
from tests.test_api import ApiTestCase


class ScheduleVarianceApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers)
        self.tasks_url = f"/projects/{self.project_id}/tasks"
        self.baselines_url = (
            f"/projects/{self.project_id}/schedule-baselines"
        )
        self.variance_url = f"/projects/{self.project_id}/schedule-variance"

    def create_task(self, name, **values):
        response = self.client.post(
            self.tasks_url,
            json={"name": name, "duration": 1, **values},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return next(
            task for task in response.json()["tasks"] if task["name"] == name
        )

    def update_task(self, task_id, **values):
        response = self.client.put(
            f"{self.tasks_url}/{task_id}",
            json=values,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        return next(
            task
            for task in response.json()["tasks"]
            if task["id"] == task_id
        )

    def capture(self, name="Baseline"):
        response = self.client.post(
            self.baselines_url,
            json={"name": name},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["baseline"]

    def variance(self, query=""):
        response = self.client.get(
            f"{self.variance_url}{query}",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_no_baseline_is_factual_not_zero_variance(self):
        self.create_task("Current only")
        payload = self.variance()
        self.assertIsNone(payload["baseline"])
        self.assertIsNone(payload["summary"])
        self.assertEqual(payload["tasks"], [])
        self.assertEqual(payload["total"], 0)

    def test_finish_based_statuses_added_removed_and_workday_units(self):
        unchanged = self.create_task(
            "Unchanged",
            manual_start_date="2026-03-02",
        )
        slipped = self.create_task(
            "Slipped",
            manual_start_date="2026-03-02",
        )
        improved = self.create_task(
            "Improved",
            manual_start_date="2026-03-09",
        )
        removed = self.create_task(
            "Removed",
            manual_start_date="2026-03-03",
        )
        baseline = self.capture()

        self.update_task(slipped["id"], manual_start_date="2026-03-09")
        self.update_task(improved["id"], manual_start_date="2026-03-02")
        # Create before deleting the highest SQLite row ID. PostgreSQL task
        # sequences never reuse deleted IDs; SQLite lacks that production
        # sequence behavior unless a table is declared AUTOINCREMENT.
        added = self.create_task(
            "Added",
            manual_start_date="2026-03-04",
        )
        deleted = self.client.delete(
            f"{self.tasks_url}/{removed['id']}",
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 200)

        payload = self.variance(f"?baseline_id={baseline['id']}&limit=50")
        rows = {row["name"]: row for row in payload["tasks"]}
        self.assertEqual(rows["Unchanged"]["comparison_status"], "unchanged")
        self.assertEqual(rows["Unchanged"]["finish_variance_workdays"], 0)
        self.assertEqual(rows["Slipped"]["comparison_status"], "slipped")
        self.assertEqual(rows["Slipped"]["finish_variance_workdays"], 5)
        self.assertEqual(rows["Improved"]["comparison_status"], "improved")
        self.assertEqual(rows["Improved"]["finish_variance_workdays"], -5)
        self.assertEqual(rows["Added"]["comparison_status"], "added")
        self.assertIsNone(rows["Added"]["baseline_task_id"])
        self.assertIsNone(rows["Added"]["finish_variance_workdays"])
        self.assertEqual(rows["Added"]["task_id"], added["id"])
        self.assertEqual(rows["Removed"]["comparison_status"], "removed")
        self.assertIsNone(rows["Removed"]["current_end_date"])
        self.assertIsNone(rows["Removed"]["finish_variance_workdays"])
        self.assertEqual(rows["Removed"]["task_id"], removed["id"])
        self.assertEqual(payload["summary"]["slipped_count"], 1)
        self.assertEqual(payload["summary"]["improved_count"], 1)
        self.assertEqual(payload["summary"]["unchanged_count"], 1)
        self.assertEqual(payload["summary"]["added_count"], 1)
        self.assertEqual(payload["summary"]["removed_count"], 1)
        self.assertEqual(payload["summary"]["baseline_leaf_task_count"], 4)
        self.assertEqual(payload["summary"]["current_leaf_task_count"], 4)
        self.assertEqual(unchanged["id"], rows["Unchanged"]["task_id"])

    def test_structural_flags_summary_rows_and_leaf_rollups(self):
        parent = self.create_task("Summary")
        child = self.create_task(
            "Child",
            duration=2,
            manual_start_date="2026-03-02",
        )
        self.update_task(child["id"], parent_task_id=parent["id"])
        predecessor = self.create_task(
            "Predecessor",
            manual_start_date="2026-03-02",
        )
        dependent = self.create_task(
            "Dependent",
            predecessor_task_id=predecessor["id"],
        )
        baseline = self.capture()

        self.update_task(
            child["id"],
            parent_task_id=None,
            duration=4,
            manual_start_date="2026-03-03",
        )
        self.update_task(
            dependent["id"],
            predecessor_task_id=None,
            manual_start_date="2026-03-05",
        )
        current = self.client.get(
            self.tasks_url,
            headers=self.headers,
        ).json()["tasks"]
        reordered_ids = [
            child["id"],
            parent["id"],
            predecessor["id"],
            dependent["id"],
        ]
        self.assertEqual({task["id"] for task in current}, set(reordered_ids))
        reordered = self.client.put(
            f"{self.tasks_url}/reorder",
            json={"task_ids": reordered_ids},
            headers=self.headers,
        )
        self.assertEqual(reordered.status_code, 200, reordered.text)

        payload = self.variance(f"?baseline_id={baseline['id']}&limit=50")
        rows = {row["name"]: row for row in payload["tasks"]}
        self.assertTrue(rows["Child"]["hierarchy_changed"])
        self.assertTrue(rows["Child"]["duration_changed"])
        self.assertTrue(rows["Child"]["manual_start_changed"])
        self.assertTrue(rows["Child"]["order_changed"])
        self.assertEqual(rows["Child"]["duration_variance_days"], 2)
        self.assertTrue(rows["Dependent"]["dependency_changed"])
        self.assertTrue(rows["Dependent"]["manual_start_changed"])
        self.assertTrue(rows["Summary"]["is_summary"])

        leaf_only = self.variance(
            f"?baseline_id={baseline['id']}&include_summaries=false&limit=50"
        )
        self.assertNotIn(
            "Summary",
            {row["name"] for row in leaf_only["tasks"]},
        )
        self.assertEqual(payload["summary"], leaf_only["summary"])
        self.assertEqual(payload["summary"]["baseline_task_count"], 4)
        self.assertEqual(payload["summary"]["baseline_leaf_task_count"], 3)

    def test_critical_path_changes_are_derived_for_matched_leaf_tasks(self):
        chain_start = self.create_task(
            "Chain start",
            duration=5,
            manual_start_date="2026-03-02",
        )
        chain_finish = self.create_task(
            "Chain finish",
            duration=5,
            predecessor_task_id=chain_start["id"],
        )
        challenger = self.create_task(
            "Challenger",
            duration=1,
            manual_start_date="2026-03-02",
        )
        baseline = self.capture()

        self.update_task(challenger["id"], duration=20)
        payload = self.variance(f"?baseline_id={baseline['id']}&limit=50")
        rows = {row["name"]: row for row in payload["tasks"]}
        self.assertEqual(
            rows["Challenger"]["critical_change"],
            "newly_critical",
        )
        self.assertEqual(
            rows["Chain start"]["critical_change"],
            "no_longer_critical",
        )
        self.assertEqual(
            rows["Chain finish"]["critical_change"],
            "no_longer_critical",
        )
        self.assertEqual(payload["summary"]["newly_critical_count"], 1)
        self.assertEqual(payload["summary"]["no_longer_critical_count"], 2)
        self.assertEqual(payload["summary"]["baseline_critical_count"], 2)
        self.assertEqual(payload["summary"]["current_critical_count"], 1)
        self.assertIsNotNone(rows["Challenger"]["float_variance_workdays"])

    def test_unscheduled_and_invalid_dates_are_safe(self):
        unscheduled = self.create_task("Unscheduled")
        invalid = self.create_task("Invalid")
        baseline = self.capture()
        with self.TestingSession() as db:
            db.get(Task, unscheduled["id"]).end_date = None
            db.get(Task, invalid["id"]).end_date = "not-a-date"
            db.commit()

        payload = self.variance(f"?baseline_id={baseline['id']}&limit=50")
        rows = {row["name"]: row for row in payload["tasks"]}
        self.assertEqual(
            rows["Unscheduled"]["comparison_status"],
            "unscheduled",
        )
        self.assertEqual(rows["Invalid"]["comparison_status"], "incomparable")
        self.assertEqual(payload["summary"]["unscheduled_count"], 1)
        self.assertEqual(payload["summary"]["incomparable_count"], 1)

    def test_filters_search_sort_pagination_and_stable_order(self):
        for index, name in enumerate(("Alpha", "Beta", "Gamma", "Delta")):
            self.create_task(
                name,
                manual_start_date=f"2026-03-0{index + 2}",
            )
        baseline = self.capture()
        tasks = self.client.get(
            self.tasks_url,
            headers=self.headers,
        ).json()["tasks"]
        self.update_task(tasks[1]["id"], manual_start_date="2026-03-12")
        self.update_task(tasks[2]["id"], duration=12)

        filtered = self.variance(
            f"?baseline_id={baseline['id']}&status=slipped"
            "&sort=finish_variance&order=desc&limit=1&offset=0"
        )
        self.assertGreaterEqual(filtered["total"], 2)
        self.assertEqual(len(filtered["tasks"]), 1)
        next_page = self.variance(
            f"?baseline_id={baseline['id']}&status=slipped"
            "&sort=finish_variance&order=desc&limit=1&offset=1"
        )
        self.assertEqual(len(next_page["tasks"]), 1)
        self.assertNotEqual(
            filtered["tasks"][0]["task_id"],
            next_page["tasks"][0]["task_id"],
        )

        searched = self.variance(
            f"?baseline_id={baseline['id']}&search=gamma&limit=50"
        )
        self.assertEqual(searched["total"], 1)
        self.assertEqual(searched["tasks"][0]["name"], "Gamma")
        critical = self.variance(
            f"?baseline_id={baseline['id']}"
            "&critical_change=newly_critical&limit=50"
        )
        self.assertTrue(
            all(
                row["critical_change"] == "newly_critical"
                for row in critical["tasks"]
            )
        )

        invalid_queries = [
            "?status=late",
            "?critical_change=maybe",
            "?sort=unsafe",
            "?order=sideways",
            "?limit=201",
            "?offset=-1",
            f"?baseline_id={baseline['id']}&search={'x' * 201}",
        ]
        for query in invalid_queries:
            with self.subTest(query=query[:40]):
                response = self.client.get(
                    f"{self.variance_url}{query}",
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_default_selection_archived_history_and_missing_baseline(self):
        first = self.capture("First")
        self.update_task(
            self.create_task("Later task")["id"],
            duration=2,
        )
        second = self.capture("Second")
        selected = self.variance()
        self.assertEqual(selected["baseline"]["id"], second["id"])

        cleared = self.client.put(
            f"/projects/{self.project_id}/schedule-baseline-comparison",
            json={"baseline_id": None},
            headers=self.headers,
        )
        self.assertEqual(cleared.status_code, 200)
        automatic = self.variance()
        self.assertEqual(automatic["baseline"]["id"], second["id"])

        archived = self.client.post(
            f"{self.baselines_url}/{second['id']}/archive",
            headers=self.headers,
        )
        self.assertEqual(archived.status_code, 200)
        fallback = self.variance()
        self.assertEqual(fallback["baseline"]["id"], first["id"])
        historical = self.variance(f"?baseline_id={second['id']}")
        self.assertEqual(historical["baseline"]["status"], "archived")
        self.assertEqual(
            self.client.get(
                f"{self.variance_url}?baseline_id=999999",
                headers=self.headers,
            ).status_code,
            404,
        )

    def test_schedule_start_change_preserves_selected_baseline(self):
        self.create_task("Anchored root")
        baseline = self.capture()
        changed = self.client.put(
            f"/projects/{self.project_id}/schedule-settings",
            json={"schedule_start_date": "2026-04-06"},
            headers=self.headers,
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()["comparison_baseline_id"], baseline["id"])

        payload = self.variance()
        self.assertEqual(payload["baseline"]["id"], baseline["id"])
        self.assertEqual(
            payload["summary"]["current_schedule_start_date"],
            "2026-04-06",
        )
        self.assertNotEqual(
            payload["summary"]["baseline_schedule_start_date"],
            payload["summary"]["current_schedule_start_date"],
        )

    def test_variance_uses_bounded_query_set_without_n_plus_one(self):
        for index in range(25):
            self.create_task(f"Task {index + 1}")
        self.capture()

        statements: list[str] = []

        def record_statement(
            connection,
            cursor,
            statement,
            parameters,
            context,
            executemany,
        ):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", record_statement)
        try:
            with self.TestingSession() as db:
                payload = get_schedule_variance(
                    db,
                    project_id=self.project_id,
                    baseline_id=None,
                    include_summaries=True,
                    status_filter=None,
                    critical_change_filter=None,
                    search=None,
                    sort="wbs",
                    order="asc",
                    limit=50,
                    offset=0,
                )
        finally:
            event.remove(
                self.engine,
                "before_cursor_execute",
                record_statement,
            )

        self.assertEqual(payload["total"], 25)
        self.assertLessEqual(len(statements), 4)

    def test_capture_and_variance_scale_to_two_thousand_tasks(self):
        for count in (100, 500, 2_000):
            with self.subTest(count=count):
                project_id = self.create_project(
                    self.headers,
                    name=f"Scale {count}",
                )
                with self.TestingSession() as db:
                    tasks = []
                    first_id = count * 10_000
                    for index in range(count):
                        tasks.append(
                            Task(
                                id=first_id + index,
                                project_id=project_id,
                                name=f"Scale task {index + 1}",
                                duration=1,
                                predecessor_task_id=(
                                    first_id + index - 1 if index else None
                                ),
                                dependency_type="FS",
                                lag_days=0,
                                order_index=index + 1,
                                is_collapsed=0,
                            )
                        )
                    db.add_all(tasks)
                    db.commit()

                capture = self.client.post(
                    f"/projects/{project_id}/schedule-baselines",
                    json={"name": f"Scale {count}"},
                    headers=self.headers,
                )
                self.assertEqual(capture.status_code, 201, capture.text)
                self.assertEqual(capture.json()["baseline"]["task_count"], count)
                variance = self.client.get(
                    f"/projects/{project_id}/schedule-variance?limit=1",
                    headers=self.headers,
                )
                self.assertEqual(variance.status_code, 200, variance.text)
                self.assertEqual(variance.json()["total"], count)
                self.assertEqual(
                    variance.json()["summary"]["unchanged_count"],
                    count,
                )


if __name__ == "__main__":
    unittest.main()
