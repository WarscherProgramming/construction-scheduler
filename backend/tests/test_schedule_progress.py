import unittest
from unittest.mock import patch

from app.models.task import Task
from tests.test_api import ApiTestCase


class ScheduleProgressApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers)
        self.tasks_url = f"/projects/{self.project_id}/tasks"
        self.settings_url = (
            f"/projects/{self.project_id}/schedule-settings"
        )
        response = self.client.put(
            self.settings_url,
            json={
                "schedule_start_date": "2026-03-02",
                "data_date": "2026-03-09",
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.text)

    def create_task(self, name="Task", duration=5, **values):
        response = self.client.post(
            self.tasks_url,
            json={"name": name, "duration": duration, **values},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return next(
            task
            for task in response.json()["tasks"]
            if task["name"] == name
        )

    def update_progress(self, task_id, **values):
        return self.client.put(
            f"{self.tasks_url}/{task_id}/progress",
            json=values,
            headers=self.headers,
        )

    def task_from(self, response, task_id):
        return next(
            task
            for task in response.json()["tasks"]
            if task["id"] == task_id
        )

    def test_default_progress_and_project_summary(self):
        task = self.create_task(duration=5)
        payload = self.client.get(
            self.tasks_url,
            headers=self.headers,
        ).json()

        self.assertEqual(task["progress_status"], "not_started")
        self.assertEqual(task["percent_complete"], 0)
        self.assertEqual(task["remaining_duration"], 5)
        self.assertIsNone(task["actual_start_date"])
        self.assertIsNone(task["actual_finish_date"])
        self.assertFalse(task["out_of_sequence"])
        self.assertEqual(task["start_date"], "2026-03-09")
        self.assertEqual(
            payload["summary"],
            {
                "total_leaf_tasks": 1,
                "not_started_count": 1,
                "in_progress_count": 0,
                "completed_count": 0,
                "out_of_sequence_count": 0,
                "percent_complete_weighted": 0.0,
                "data_date": "2026-03-09",
                "forecast_project_finish": "2026-03-13",
                "completed_through_data_date": 0,
                "tasks_started_last_7_days": 0,
                "tasks_completed_last_7_days": 0,
            },
        )

    def test_in_progress_completed_and_correction_transitions(self):
        task = self.create_task(duration=5)
        active_response = self.update_progress(
            task["id"],
            progress_status="in_progress",
            actual_start_date="2026-03-05",
            percent_complete=40,
            remaining_duration=3,
        )
        self.assertEqual(active_response.status_code, 200, active_response.text)
        active = self.task_from(active_response, task["id"])
        self.assertEqual(active["start_date"], "2026-03-05")
        self.assertEqual(active["end_date"], "2026-03-11")
        self.assertIsNotNone(active["status_updated_at"])

        completed_response = self.update_progress(
            task["id"],
            progress_status="completed",
            actual_finish_date="2026-03-07",
        )
        self.assertEqual(completed_response.status_code, 200)
        completed = self.task_from(completed_response, task["id"])
        self.assertEqual(completed["progress_status"], "completed")
        self.assertEqual(completed["percent_complete"], 100)
        self.assertEqual(completed["remaining_duration"], 0)
        self.assertEqual(completed["start_date"], "2026-03-05")
        self.assertEqual(completed["end_date"], "2026-03-07")
        self.assertEqual(completed["total_float"], 0)
        self.assertFalse(completed["is_critical"])

        corrected_response = self.update_progress(
            task["id"],
            progress_status="in_progress",
            percent_complete=80,
            remaining_duration=1,
        )
        self.assertEqual(corrected_response.status_code, 200)
        corrected = self.task_from(corrected_response, task["id"])
        self.assertEqual(corrected["progress_status"], "in_progress")
        self.assertIsNone(corrected["actual_finish_date"])

        reset_response = self.update_progress(
            task["id"],
            progress_status="not_started",
        )
        reset = self.task_from(reset_response, task["id"])
        self.assertEqual(reset["percent_complete"], 0)
        self.assertEqual(reset["remaining_duration"], 5)
        self.assertIsNone(reset["actual_start_date"])
        self.assertIsNone(reset["actual_finish_date"])

        with self.TestingSession() as db:
            persisted = db.get(Task, task["id"])
            self.assertIsNotNone(persisted.status_updated_by)

    def test_invalid_states_dates_bounds_and_mass_assignment_are_rejected(self):
        task = self.create_task()
        invalid_payloads = [
            {},
            {"progress_status": "in_progress"},
            {
                "progress_status": "in_progress",
                "actual_start_date": "2026-03-10",
                "percent_complete": 50,
                "remaining_duration": 1,
            },
            {
                "progress_status": "in_progress",
                "actual_start_date": "2026-03-05",
                "percent_complete": 0,
                "remaining_duration": 1,
            },
            {
                "progress_status": "in_progress",
                "actual_start_date": "2026-03-05",
                "percent_complete": 50,
                "remaining_duration": 0,
            },
            {
                "progress_status": "completed",
                "actual_start_date": "2026-03-06",
                "actual_finish_date": "2026-03-05",
            },
            {
                "progress_status": "completed",
                "actual_start_date": "2026-03-05",
                "actual_finish_date": "2026-03-10",
            },
            {"progress_status": "unknown"},
            {"percent_complete": 101},
            {"remaining_duration": 36_501},
            {"remaining_duration": 4},
            {"progress_status": None},
            {"status_updated_by": 999},
            {"start_date": "2026-03-01"},
            {"out_of_sequence": True},
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.update_progress(task["id"], **payload)
                self.assertEqual(response.status_code, 422, response.text)

        generic = self.client.put(
            f"{self.tasks_url}/{task['id']}",
            json={"percent_complete": 50},
            headers=self.headers,
        )
        self.assertEqual(generic.status_code, 422)

    def test_planned_duration_updates_reset_only_not_started_remaining_work(self):
        task = self.create_task(duration=5)
        updated = self.client.put(
            f"{self.tasks_url}/{task['id']}",
            json={"duration": 8},
            headers=self.headers,
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        row = self.task_from(updated, task["id"])
        self.assertEqual(row["duration"], 8)
        self.assertEqual(row["remaining_duration"], 8)

        self.update_progress(
            task["id"],
            progress_status="in_progress",
            actual_start_date="2026-03-05",
            percent_complete=50,
            remaining_duration=3,
        )
        active_update = self.client.put(
            f"{self.tasks_url}/{task['id']}",
            json={"duration": 10},
            headers=self.headers,
        )
        self.assertEqual(active_update.status_code, 200, active_update.text)
        active = self.task_from(active_update, task["id"])
        self.assertEqual(active["duration"], 10)
        self.assertEqual(active["remaining_duration"], 3)

    def test_summary_progress_is_derived_and_cannot_be_updated(self):
        parent = self.create_task("Summary", duration=1)
        child_a = self.create_task("Complete", duration=4)
        child_b = self.create_task("Active", duration=2)
        for child in (child_a, child_b):
            nested = self.client.put(
                f"{self.tasks_url}/{child['id']}",
                json={"parent_task_id": parent["id"]},
                headers=self.headers,
            )
            self.assertEqual(nested.status_code, 200)

        self.update_progress(
            child_a["id"],
            progress_status="completed",
            actual_start_date="2026-03-02",
            actual_finish_date="2026-03-05",
        )
        active_response = self.update_progress(
            child_b["id"],
            progress_status="in_progress",
            actual_start_date="2026-03-06",
            percent_complete=50,
            remaining_duration=1,
        )
        derived = self.task_from(active_response, parent["id"])
        self.assertEqual(derived["progress_status"], "in_progress")
        self.assertEqual(derived["percent_complete"], 83)
        self.assertEqual(derived["actual_start_date"], "2026-03-02")
        self.assertIsNone(derived["actual_finish_date"])
        self.assertIsNone(derived["remaining_duration"])
        self.assertEqual(
            active_response.json()["summary"]["percent_complete_weighted"],
            83.3,
        )

        rejected = self.update_progress(
            parent["id"],
            progress_status="in_progress",
            actual_start_date="2026-03-05",
            percent_complete=25,
            remaining_duration=1,
        )
        self.assertEqual(rejected.status_code, 422)

    def test_retained_logic_flags_fs_and_ss_progress(self):
        predecessor = self.create_task("Predecessor", duration=3)
        finish_successor = self.create_task(
            "FS successor",
            duration=2,
            predecessor_task_id=predecessor["id"],
        )
        start_successor = self.create_task(
            "SS successor",
            duration=2,
            predecessor_task_id=predecessor["id"],
            dependency_type="SS",
            lag_days=2,
        )

        fs_response = self.update_progress(
            finish_successor["id"],
            progress_status="in_progress",
            actual_start_date="2026-03-05",
            percent_complete=25,
            remaining_duration=2,
        )
        fs_task = self.task_from(fs_response, finish_successor["id"])
        self.assertTrue(fs_task["out_of_sequence"])
        self.assertIn("FS predecessor boundary", fs_task["out_of_sequence_reason"])
        self.assertEqual(fs_task["end_date"], "2026-03-13")

        ss_response = self.update_progress(
            start_successor["id"],
            progress_status="completed",
            actual_start_date="2026-03-09",
            actual_finish_date="2026-03-09",
        )
        ss_task = self.task_from(ss_response, start_successor["id"])
        self.assertTrue(ss_task["out_of_sequence"])
        self.assertIn("SS predecessor boundary", ss_task["out_of_sequence_reason"])
        self.assertEqual(ss_response.json()["summary"]["out_of_sequence_count"], 2)

    def test_data_date_update_is_atomic_independent_and_idempotent(self):
        task = self.create_task(duration=2)
        before = self.client.get(
            self.settings_url,
            headers=self.headers,
        ).json()
        moved = self.client.put(
            self.settings_url,
            json={"data_date": "2026-03-11"},
            headers=self.headers,
        )
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(moved.json()["schedule_start_date"], "2026-03-02")
        self.assertEqual(moved.json()["data_date"], "2026-03-11")
        refreshed = self.client.get(
            self.tasks_url,
            headers=self.headers,
        ).json()
        refreshed_task = next(
            item for item in refreshed["tasks"] if item["id"] == task["id"]
        )
        self.assertEqual(refreshed_task["start_date"], "2026-03-11")

        with patch(
            "app.api.routes_schedule_settings.recalculate_schedule"
        ) as recalculate:
            unchanged = self.client.put(
                self.settings_url,
                json={"data_date": "2026-03-11"},
                headers=self.headers,
            )
        self.assertEqual(unchanged.status_code, 200)
        recalculate.assert_not_called()
        self.assertEqual(before["comparison_baseline_id"], None)

    def test_data_date_cannot_move_before_actuals_and_rolls_back(self):
        task = self.create_task()
        self.update_progress(
            task["id"],
            progress_status="in_progress",
            actual_start_date="2026-03-08",
            percent_complete=25,
            remaining_duration=2,
        )
        response = self.client.put(
            self.settings_url,
            json={"data_date": "2026-03-07"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 422)
        current = self.client.get(
            self.settings_url,
            headers=self.headers,
        ).json()
        self.assertEqual(current["data_date"], "2026-03-09")

    def test_progress_rollback_ownership_missing_and_authentication(self):
        task = self.create_task()
        with patch(
            "app.services.task_progress.recalculate_schedule",
            side_effect=RuntimeError("calculation failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.update_progress(
                    task["id"],
                    progress_status="in_progress",
                    actual_start_date="2026-03-05",
                    percent_complete=25,
                    remaining_duration=2,
                )
        persisted = self.client.get(
            self.tasks_url,
            headers=self.headers,
        ).json()["tasks"][0]
        self.assertEqual(persisted["progress_status"], "not_started")
        self.assertIsNone(persisted["status_updated_at"])

        self.assertEqual(
            self.client.put(
                f"{self.tasks_url}/{task['id']}/progress",
                json={"progress_status": "not_started"},
            ).status_code,
            401,
        )
        other_headers = self.register_and_login("other-progress@example.com")
        self.assertEqual(
            self.client.put(
                f"{self.tasks_url}/{task['id']}/progress",
                json={"progress_status": "not_started"},
                headers=other_headers,
            ).status_code,
            403,
        )
        other_project = self.create_project(self.headers, "Other owned")
        self.assertEqual(
            self.client.put(
                f"/projects/{other_project}/tasks/{task['id']}/progress",
                json={"progress_status": "not_started"},
                headers=self.headers,
            ).status_code,
            404,
        )
        self.assertEqual(
            self.update_progress(999_999, progress_status="not_started").status_code,
            404,
        )

    def test_template_and_baseline_keep_planning_boundaries(self):
        task = self.create_task("Statused", duration=4)
        active = self.update_progress(
            task["id"],
            progress_status="in_progress",
            actual_start_date="2026-03-05",
            percent_complete=50,
            remaining_duration=2,
        )
        self.assertEqual(active.status_code, 200)
        baseline = self.client.post(
            f"/projects/{self.project_id}/schedule-baselines",
            json={"name": "Progress forecast"},
            headers=self.headers,
        )
        self.assertEqual(baseline.status_code, 201, baseline.text)
        baseline_id = baseline.json()["baseline"]["id"]
        detail = self.client.get(
            f"/projects/{self.project_id}/schedule-baselines/{baseline_id}",
            headers=self.headers,
        ).json()
        self.assertNotIn("progress_status", detail["tasks"][0])

        template = self.client.post(
            f"/projects/{self.project_id}/templates",
            json={"name": "Planning only"},
            headers=self.headers,
        ).json()
        target = self.create_project(self.headers, "Template target")
        self.client.put(
            f"/projects/{target}/schedule-settings",
            json={
                "schedule_start_date": "2026-04-06",
                "data_date": "2026-04-06",
            },
            headers=self.headers,
        )
        applied = self.client.post(
            f"/projects/{target}/templates/{template['id']}/apply",
            headers=self.headers,
        )
        self.assertEqual(applied.status_code, 200)
        target_task = self.client.get(
            f"/projects/{target}/tasks",
            headers=self.headers,
        ).json()["tasks"][0]
        self.assertEqual(target_task["progress_status"], "not_started")
        self.assertEqual(target_task["percent_complete"], 0)
        self.assertEqual(target_task["remaining_duration"], 4)
        self.assertIsNone(target_task["actual_start_date"])

    def test_variance_exposes_live_progress_without_mutating_baseline(self):
        completed = self.create_task("Completed", duration=3)
        predecessor = self.create_task("Predecessor", duration=3)
        active = self.create_task(
            "Active",
            duration=2,
            predecessor_task_id=predecessor["id"],
        )
        captured = self.client.post(
            f"/projects/{self.project_id}/schedule-baselines",
            json={"name": "Planned state"},
            headers=self.headers,
        ).json()["baseline"]

        self.update_progress(
            completed["id"],
            progress_status="completed",
            actual_start_date="2026-03-02",
            actual_finish_date="2026-03-06",
        )
        self.update_progress(
            active["id"],
            progress_status="in_progress",
            actual_start_date="2026-03-05",
            percent_complete=50,
            remaining_duration=2,
        )
        variance = self.client.get(
            f"/projects/{self.project_id}/schedule-variance"
            f"?baseline_id={captured['id']}&limit=50",
            headers=self.headers,
        )
        self.assertEqual(variance.status_code, 200, variance.text)
        payload = variance.json()
        rows = {row["name"]: row for row in payload["tasks"]}
        self.assertEqual(rows["Completed"]["progress_status"], "completed")
        self.assertEqual(rows["Completed"]["actual_finish_date"], "2026-03-06")
        self.assertEqual(rows["Completed"]["current_end_date"], "2026-03-06")
        self.assertEqual(rows["Active"]["progress_status"], "in_progress")
        self.assertEqual(rows["Active"]["remaining_duration"], 2)
        self.assertTrue(rows["Active"]["out_of_sequence"])
        self.assertEqual(payload["summary"]["completed_count"], 1)
        self.assertEqual(payload["summary"]["in_progress_count"], 1)
        self.assertEqual(payload["summary"]["not_started_count"], 1)
        self.assertEqual(payload["summary"]["out_of_sequence_count"], 1)
        self.assertEqual(payload["summary"]["current_data_date"], "2026-03-09")

        detail = self.client.get(
            f"/projects/{self.project_id}/schedule-baselines/{captured['id']}",
            headers=self.headers,
        ).json()
        baseline_rows = {task["name"]: task for task in detail["tasks"]}
        self.assertEqual(baseline_rows["Completed"]["end_date"], "2026-03-11")
        self.assertNotIn("progress_status", baseline_rows["Completed"])


if __name__ == "__main__":
    unittest.main()
