import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import event

from app.models.task import Task
from app.services.pdf_export import build_schedule_executive_pdf
from tests.test_api import ApiTestCase


class ScheduleHealthApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers, "Health Project")
        self.health_url = f"/projects/{self.project_id}/schedule-health"
        settings = self.client.put(
            f"/projects/{self.project_id}/schedule-settings",
            json={
                "schedule_start_date": "2026-08-03",
                "data_date": "2026-08-10",
            },
            headers=self.headers,
        )
        self.assertEqual(settings.status_code, 200, settings.text)

    def create_task(self, name="Health task", **values):
        response = self.client.post(
            f"/projects/{self.project_id}/tasks",
            json={
                "name": name,
                "duration": 3,
                "manual_start_date": "2026-08-10",
                **values,
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return next(row for row in response.json()["tasks"] if row["name"] == name)

    def test_authentication_ownership_and_explicit_baseline_are_enforced(self):
        self.assertEqual(self.client.get(self.health_url).status_code, 401)
        intruder = self.register_and_login("health-intruder@example.com")
        self.assertEqual(
            self.client.get(self.health_url, headers=intruder).status_code,
            403,
        )
        missing = self.client.get(
            f"{self.health_url}?baseline_id=999999",
            headers=self.headers,
        )
        self.assertEqual(missing.status_code, 404)

    def test_missing_baseline_is_factual_attention_not_stable(self):
        response = self.client.get(self.health_url, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["category"], "attention")
        self.assertIsNone(payload["baseline"])
        self.assertIsNone(payload["metrics"]["project_finish_variance_workdays"])
        self.assertEqual(payload["reasons"][0]["code"], "baseline_missing")
        self.assertEqual(payload["data_date"], "2026-08-10")
        self.assertNotIn("tasks", payload)

    def test_empty_baselined_schedule_is_stable(self):
        baseline = self.client.post(
            f"/projects/{self.project_id}/schedule-baselines",
            json={"name": "Contract Baseline"},
            headers=self.headers,
        )
        self.assertEqual(baseline.status_code, 201, baseline.text)
        payload = self.client.get(self.health_url, headers=self.headers).json()
        self.assertEqual(payload["category"], "stable")
        self.assertEqual(payload["reasons"], [])
        self.assertEqual(payload["baseline"]["name"], "Contract Baseline")
        self.assertEqual(payload["executive_summary"]["total_leaf_tasks"], 0)

    def test_unavailable_resource_and_unassigned_work_are_explainable(self):
        task = self.create_task()
        equipment = self.client.post(
            f"/projects/{self.project_id}/equipment-resources",
            json={
                "name": "Lift 1",
                "equipment_type": "Scissor Lift",
                "default_capacity": 1,
            },
            headers=self.headers,
        ).json()["equipment"]
        assignment = self.client.post(
            f"/projects/{self.project_id}/tasks/{task['id']}/resource-assignments",
            json={
                "resource_type": "equipment",
                "resource_id": equipment["id"],
                "allocation_amount": 1,
            },
            headers=self.headers,
        )
        self.assertEqual(assignment.status_code, 201, assignment.text)
        unavailable = self.client.post(
            f"/projects/{self.project_id}/resources/equipment/{equipment['id']}/availability",
            json={
                "start_date": "2026-08-10",
                "end_date": "2026-08-12",
                "capacity": 0,
            },
            headers=self.headers,
        )
        self.assertEqual(unavailable.status_code, 201, unavailable.text)

        payload = self.client.get(self.health_url, headers=self.headers).json()
        self.assertEqual(payload["category"], "critical")
        self.assertEqual(payload["metrics"]["unavailable_resource_conflicts"], 3)
        self.assertEqual(payload["metrics"]["equipment_overallocated_days"], 3)
        self.assertTrue(any(
            item["code"] == "unavailable_resource"
            for item in payload["top_attention_items"]
        ))

    def test_blocked_look_ahead_metrics_use_latest_active_plan(self):
        task = self.create_task("Blocked work")
        plan = self.client.post(
            f"/projects/{self.project_id}/look-ahead-plans",
            json={"name": "Coordination"},
            headers=self.headers,
        ).json()["plan"]
        updated = self.client.put(
            f"/projects/{self.project_id}/look-ahead-plans/{plan['id']}/items/{task['id']}",
            json={
                "readiness_status": "blocked",
                "blocking_reason": "Permit not issued",
                "target_resolution_date": "2026-08-09",
            },
            headers=self.headers,
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        payload = self.client.get(self.health_url, headers=self.headers).json()
        self.assertEqual(payload["metrics"]["blocked_look_ahead_items"], 1)
        self.assertEqual(payload["metrics"]["overdue_look_ahead_blockers"], 1)
        self.assertTrue(any(
            item["reason"] == "Permit not issued"
            for item in payload["top_attention_items"]
        ))

    def test_executive_pdf_is_owned_bounded_and_ascii_named(self):
        self.create_task("<b>Executive & unsafe</b>")
        report_url = (
            f"/projects/{self.project_id}/reports/schedule-executive.pdf"
        )
        with tempfile.TemporaryDirectory() as directory:
            with patch("app.services.pdf_export.tempfile.tempdir", directory):
                response = self.client.get(report_url, headers=self.headers)
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertIn("Health_Project_schedule_executive.pdf", response.headers["content-disposition"])
        intruder = self.register_and_login("report-intruder@example.com")
        self.assertEqual(
            self.client.get(report_url, headers=intruder).status_code,
            403,
        )

    def test_executive_pdf_failure_cleans_temporary_file(self):
        project = type("Project", (), {"id": 1, "name": "<unsafe>"})()
        health = {
            "category": "attention",
            "summary": "Schedule requires attention.",
            "reasons": [],
            "top_attention_items": [],
            "executive_summary": {
                "schedule_start_date": "2026-08-03",
                "data_date": "2026-08-10",
                "baseline_name": None,
                "baseline_project_finish": None,
                "current_forecast_finish": None,
                "project_finish_variance_workdays": None,
                "total_leaf_tasks": 0,
                "not_started_tasks": 0,
                "in_progress_tasks": 0,
                "completed_tasks": 0,
                "slipped_tasks": 0,
                "newly_critical_tasks": 0,
                "negative_float_tasks": 0,
                "out_of_sequence_tasks": 0,
                "milestones_due_next_21_days": 0,
                "blocked_look_ahead_items": 0,
                "committed_look_ahead_items": 0,
                "labor_overallocated_days": 0,
                "equipment_overallocated_days": 0,
                "unassigned_executable_tasks": 0,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch("app.services.pdf_export.tempfile.tempdir", directory),
                patch(
                    "app.services.pdf_export.SimpleDocTemplate.build",
                    side_effect=RuntimeError("failed"),
                ),
            ):
                with self.assertRaises(RuntimeError):
                    build_schedule_executive_pdf(project, health)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_health_query_count_is_bounded_at_scale(self):
        counts = []
        for task_count in (0, 600):
            if task_count:
                with self.TestingSession() as db:
                    db.add_all([
                        Task(
                            project_id=self.project_id,
                            name=f"Scale {index}",
                            duration=1,
                            remaining_duration=1,
                            start_date="2026-08-10",
                            end_date="2026-08-10",
                            manual_start_date="2026-08-10",
                            order_index=index,
                        )
                        for index in range(task_count)
                    ])
                    db.commit()
            count = 0

            def before_cursor(_conn, _cursor, statement, _params, _context, _many):
                nonlocal count
                if statement.lstrip().upper().startswith("SELECT"):
                    count += 1

            event.listen(self.engine, "before_cursor_execute", before_cursor)
            try:
                response = self.client.get(self.health_url, headers=self.headers)
            finally:
                event.remove(self.engine, "before_cursor_execute", before_cursor)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertLessEqual(len(response.content), 15_000)
            counts.append(count)
        self.assertEqual(counts[0], counts[1])
        self.assertLessEqual(counts[1], 12)


if __name__ == "__main__":
    unittest.main()
