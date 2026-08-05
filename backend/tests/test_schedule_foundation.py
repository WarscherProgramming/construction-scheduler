from datetime import date
import unittest
from unittest.mock import patch

from sqlalchemy import text

from app.models.project import Project
from app.models.project_schedule_settings import ProjectScheduleSettings
from app.models.task import Task
from tests.test_api import ApiTestCase


class ScheduleSettingsApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers)
        self.url = f"/projects/{self.project_id}/schedule-settings"

    def test_project_creation_seeds_gettable_schedule_settings(self):
        response = self.client.get(self.url, headers=self.headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["project_id"], self.project_id)
        date.fromisoformat(payload["schedule_start_date"])
        self.assertEqual(
            payload["data_date"],
            payload["schedule_start_date"],
        )
        self.assertEqual(
            set(payload),
            {
                "project_id",
                "schedule_start_date",
                "data_date",
                "comparison_baseline_id",
                "created_at",
                "updated_at",
            },
        )

    def test_schedule_settings_require_authentication_and_ownership(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)

        other_headers = self.register_and_login("other@example.com")
        forbidden = self.client.get(self.url, headers=other_headers)
        self.assertEqual(forbidden.status_code, 403)

    def test_update_recalculates_root_dependency_and_preserves_manual_root(self):
        root = self.client.post(
            f"/projects/{self.project_id}/tasks",
            json={"name": "Root", "duration": 2},
            headers=self.headers,
        ).json()["tasks"][0]
        self.client.post(
            f"/projects/{self.project_id}/tasks",
            json={
                "name": "Manual",
                "duration": 1,
                "manual_start_date": "2026-03-10",
            },
            headers=self.headers,
        )
        self.client.post(
            f"/projects/{self.project_id}/tasks",
            json={
                "name": "Dependent",
                "duration": 1,
                "predecessor_task_id": root["id"],
            },
            headers=self.headers,
        )

        updated = self.client.put(
            self.url,
            json={
                "schedule_start_date": "2026-03-02",
                "data_date": "2026-03-02",
            },
            headers=self.headers,
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["schedule_start_date"], "2026-03-02")
        tasks = self.client.get(
            f"/projects/{self.project_id}/tasks",
            headers=self.headers,
        ).json()["tasks"]
        by_name = {task["name"]: task for task in tasks}
        self.assertEqual(by_name["Root"]["start_date"], "2026-03-02")
        self.assertEqual(by_name["Root"]["end_date"], "2026-03-03")
        self.assertEqual(by_name["Dependent"]["start_date"], "2026-03-04")
        self.assertEqual(by_name["Manual"]["start_date"], "2026-03-10")

    def test_invalid_date_unknown_field_and_cross_project_input_are_rejected(self):
        payloads = [
            {"schedule_start_date": "2026-02-30"},
            {"data_date": "2026-02-30"},
            {"data_date": None},
            {
                "schedule_start_date": "2026-03-02",
                "project_id": self.project_id,
            },
            {},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.put(
                    self.url,
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_unchanged_update_is_idempotent(self):
        before = self.client.get(self.url, headers=self.headers).json()

        with patch(
            "app.api.routes_schedule_settings.recalculate_schedule"
        ) as recalculate:
            response = self.client.put(
                self.url,
                json={
                    "schedule_start_date": before["schedule_start_date"]
                },
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), before)
        recalculate.assert_not_called()

    def test_settings_update_rolls_back_on_recalculation_failure(self):
        before = self.client.get(self.url, headers=self.headers).json()

        with patch(
            "app.api.routes_schedule_settings.recalculate_schedule",
            side_effect=RuntimeError("calculation failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.put(
                    self.url,
                    json={"data_date": "2026-03-09"},
                    headers=self.headers,
                )

        after = self.client.get(self.url, headers=self.headers).json()
        self.assertEqual(
            after["schedule_start_date"],
            before["schedule_start_date"],
        )
        self.assertEqual(after["data_date"], before["data_date"])

    def test_project_deletion_cascades_schedule_settings(self):
        with self.TestingSession() as db:
            db.execute(text("PRAGMA foreign_keys = ON"))
            project = db.get(Project, self.project_id)
            db.delete(project)
            db.commit()
            self.assertIsNone(
                db.get(ProjectScheduleSettings, self.project_id)
            )


class TaskFoundationApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers)
        self.tasks_url = f"/projects/{self.project_id}/tasks"

    def create_task(self, name, **values):
        response = self.client.post(
            self.tasks_url,
            json={"name": name, "duration": 1, **values},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201)
        return next(
            task for task in response.json()["tasks"] if task["name"] == name
        )

    def test_computational_update_fields_reject_explicit_null(self):
        task = self.create_task("Task")
        for field in (
            "name",
            "duration",
            "dependency_type",
            "lag_days",
            "is_collapsed",
        ):
            with self.subTest(field=field):
                response = self.client.put(
                    f"{self.tasks_url}/{task['id']}",
                    json={field: None},
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_nullable_relationship_and_manual_fields_can_be_cleared(self):
        predecessor = self.create_task("Predecessor")
        dependent = self.create_task(
            "Dependent",
            predecessor_task_id=predecessor["id"],
            dependency_type="SS",
            lag_days=3,
            manual_start_date="2026-04-01",
        )

        cleared = self.client.put(
            f"{self.tasks_url}/{dependent['id']}",
            json={
                "predecessor_task_id": None,
                "manual_start_date": None,
            },
            headers=self.headers,
        )

        self.assertEqual(cleared.status_code, 200)
        updated = next(
            task
            for task in cleared.json()["tasks"]
            if task["id"] == dependent["id"]
        )
        self.assertIsNone(updated["predecessor_task_id"])
        self.assertEqual(updated["dependency_type"], "FS")
        self.assertEqual(updated["lag_days"], 0)
        self.assertIsNone(updated["manual_start_date"])

        parent = self.create_task("Parent")
        child = self.create_task("Child")
        nested = self.client.put(
            f"{self.tasks_url}/{child['id']}",
            json={"parent_task_id": parent["id"]},
            headers=self.headers,
        )
        self.assertEqual(nested.status_code, 200)
        unnested = self.client.put(
            f"{self.tasks_url}/{child['id']}",
            json={"parent_task_id": None},
            headers=self.headers,
        )
        self.assertEqual(unnested.status_code, 200)

    def test_nested_hierarchy_reorder_requires_contiguous_preorder(self):
        parent = self.create_task("Parent")
        child = self.create_task("Child")
        grandchild = self.create_task("Grandchild")
        other_root = self.create_task("Other root")
        self.client.put(
            f"{self.tasks_url}/{child['id']}",
            json={"parent_task_id": parent["id"]},
            headers=self.headers,
        )
        self.client.put(
            f"{self.tasks_url}/{grandchild['id']}",
            json={"parent_task_id": child["id"]},
            headers=self.headers,
        )

        valid_ids = [
            other_root["id"],
            parent["id"],
            child["id"],
            grandchild["id"],
        ]
        valid = self.client.put(
            f"{self.tasks_url}/reorder",
            json={"task_ids": valid_ids},
            headers=self.headers,
        )
        self.assertEqual(valid.status_code, 200)

        invalid_orders = [
            [child["id"], parent["id"], grandchild["id"], other_root["id"]],
            [parent["id"], child["id"], other_root["id"], grandchild["id"]],
        ]
        for task_ids in invalid_orders:
            with self.subTest(task_ids=task_ids):
                response = self.client.put(
                    f"{self.tasks_url}/reorder",
                    json={"task_ids": task_ids},
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

        listing = self.client.get(
            self.tasks_url,
            headers=self.headers,
        ).json()["tasks"]
        self.assertEqual([task["id"] for task in listing], valid_ids)

    def test_update_and_delete_roll_back_on_recalculation_failure(self):
        task = self.create_task("Atomic")
        task_url = f"{self.tasks_url}/{task['id']}"

        with patch(
            "app.api.routes_task.recalculate_schedule",
            side_effect=RuntimeError("calculation failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.put(
                    task_url,
                    json={"duration": 5},
                    headers=self.headers,
                )
            with self.assertRaises(RuntimeError):
                self.client.delete(task_url, headers=self.headers)

        with self.TestingSession() as db:
            persisted = db.get(Task, task["id"])
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.duration, 1)

    def test_template_apply_uses_target_anchor_and_preserves_structure(self):
        parent = self.create_task("Summary")
        child = self.create_task(
            "Manual source child",
            manual_start_date="2026-01-05",
        )
        self.client.put(
            f"{self.tasks_url}/{child['id']}",
            json={"parent_task_id": parent["id"]},
            headers=self.headers,
        )
        successor = self.create_task(
            "Successor",
            predecessor_task_id=parent["id"],
        )
        template = self.client.post(
            f"/projects/{self.project_id}/templates",
            json={"name": "Foundation sequence"},
            headers=self.headers,
        ).json()

        target_project = self.create_project(self.headers, "Target")
        self.client.put(
            f"/projects/{target_project}/schedule-settings",
            json={
                "schedule_start_date": "2026-04-06",
                "data_date": "2026-04-06",
            },
            headers=self.headers,
        )
        applied = self.client.post(
            f"/projects/{target_project}/templates/{template['id']}/apply",
            headers=self.headers,
        )
        self.assertEqual(applied.status_code, 200)

        tasks = self.client.get(
            f"/projects/{target_project}/tasks",
            headers=self.headers,
        ).json()["tasks"]
        by_name = {task["name"]: task for task in tasks}
        target_parent = by_name["Summary"]
        target_child = by_name["Manual source child"]
        target_successor = by_name["Successor"]
        self.assertEqual(target_child["parent_task_id"], target_parent["id"])
        self.assertIsNone(target_child["manual_start_date"])
        self.assertEqual(target_child["start_date"], "2026-04-06")
        self.assertEqual(
            target_successor["predecessor_task_id"],
            target_parent["id"],
        )
        self.assertEqual(target_successor["start_date"], "2026-04-07")
        self.assertEqual(successor["duration"], target_successor["duration"])

    def test_template_preserves_advanced_planning_fields(self):
        milestone = self.create_task(
            "Contract award",
            duration=0,
            is_milestone=True,
        )
        predecessor = self.create_task("Procurement", duration=3)
        successor = self.create_task(
            "Delivery",
            duration=2,
            dependencies=[
                {
                    "predecessor_task_id": milestone["id"],
                    "dependency_type": "FS",
                    "lag_days": 0,
                },
                {
                    "predecessor_task_id": predecessor["id"],
                    "dependency_type": "FF",
                    "lag_days": -1,
                },
            ],
            constraint_type="SNET",
            constraint_date="2026-08-10",
        )
        template = self.client.post(
            f"/projects/{self.project_id}/templates",
            json={"name": "Advanced planning"},
            headers=self.headers,
        ).json()
        target_project = self.create_project(self.headers, "Template target")

        applied = self.client.post(
            f"/projects/{target_project}/templates/{template['id']}/apply",
            headers=self.headers,
        )
        self.assertEqual(applied.status_code, 200, applied.text)
        tasks = self.client.get(
            f"/projects/{target_project}/tasks",
            headers=self.headers,
        ).json()["tasks"]
        by_name = {task["name"]: task for task in tasks}
        target_milestone = by_name["Contract award"]
        target_predecessor = by_name["Procurement"]
        target_successor = by_name["Delivery"]

        self.assertTrue(target_milestone["is_milestone"])
        self.assertEqual(target_milestone["duration"], 0)
        self.assertEqual(target_successor["constraint_type"], "SNET")
        self.assertEqual(target_successor["constraint_date"], "2026-08-10")
        self.assertEqual(
            [
                (
                    dependency["predecessor_task_id"],
                    dependency["dependency_type"],
                    dependency["lag_days"],
                )
                for dependency in target_successor["dependencies"]
            ],
            [
                (target_milestone["id"], "FS", 0),
                (target_predecessor["id"], "FF", -1),
            ],
        )
        self.assertEqual(successor["progress_status"], "not_started")

    def test_pdf_export_uses_persisted_deterministic_dates(self):
        self.client.put(
            f"/projects/{self.project_id}/schedule-settings",
            json={
                "schedule_start_date": "2026-04-06",
                "data_date": "2026-04-06",
            },
            headers=self.headers,
        )
        task = self.create_task("Exported")
        self.assertEqual(task["start_date"], "2026-04-06")

        response = self.client.get(
            f"/projects/{self.project_id}/export/pdf",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")


if __name__ == "__main__":
    unittest.main()
