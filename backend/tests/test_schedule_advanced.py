import unittest
from unittest.mock import patch

from app.models.task import Task, TaskDependency
from tests.test_api import ApiTestCase


class AdvancedSchedulingApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers)
        self.tasks_url = f"/projects/{self.project_id}/tasks"

    def create_task(self, name, duration=1, **values):
        response = self.client.post(
            self.tasks_url,
            json={"name": name, "duration": duration, **values},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return next(
            task for task in response.json()["tasks"] if task["name"] == name
        )

    def update_task(self, task_id, **values):
        return self.client.put(
            f"{self.tasks_url}/{task_id}",
            json=values,
            headers=self.headers,
        )

    def test_create_and_update_multiple_dependencies(self):
        first = self.create_task("First", duration=3)
        second = self.create_task("Second", duration=2)
        successor = self.create_task(
            "Successor",
            duration=2,
            dependencies=[
                {
                    "predecessor_task_id": first["id"],
                    "dependency_type": "FF",
                    "lag_days": -1,
                },
                {
                    "predecessor_task_id": second["id"],
                    "dependency_type": "SF",
                    "lag_days": 4,
                },
            ],
        )

        self.assertEqual(
            [
                (
                    row["predecessor_task_id"],
                    row["dependency_type"],
                    row["lag_days"],
                )
                for row in successor["dependencies"]
            ],
            [(first["id"], "FF", -1), (second["id"], "SF", 4)],
        )
        self.assertEqual(successor["predecessor_task_id"], first["id"])
        self.assertEqual(successor["dependency_type"], "FF")
        self.assertEqual(successor["lag_days"], -1)

        updated = self.update_task(
            successor["id"],
            dependencies=[
                {
                    "predecessor_task_id": second["id"],
                    "dependency_type": "SS",
                    "lag_days": -2,
                }
            ],
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        row = next(
            task
            for task in updated.json()["tasks"]
            if task["id"] == successor["id"]
        )
        self.assertEqual(len(row["dependencies"]), 1)
        self.assertEqual(row["predecessor"], f"{second['id']}SS-2")

    def test_legacy_predecessor_contract_supports_new_types_and_lead(self):
        predecessor = self.create_task("Predecessor", duration=3)
        successor = self.create_task(
            "Legacy successor",
            predecessor=f"{predecessor['id']}FF-2",
        )

        self.assertEqual(successor["dependency_type"], "FF")
        self.assertEqual(successor["lag_days"], -2)
        self.assertEqual(len(successor["dependencies"]), 1)

    def test_dependency_validation_rejects_duplicate_self_and_cycle(self):
        first = self.create_task("First")
        second = self.create_task(
            "Second",
            dependencies=[{"predecessor_task_id": first["id"]}],
        )
        invalid_payloads = [
            [
                {"predecessor_task_id": first["id"]},
                {
                    "predecessor_task_id": first["id"],
                    "dependency_type": "SS",
                },
            ],
            [{"predecessor_task_id": second["id"]}],
        ]
        for dependencies in invalid_payloads:
            with self.subTest(dependencies=dependencies):
                response = self.update_task(
                    second["id"],
                    dependencies=dependencies,
                )
                self.assertEqual(response.status_code, 422)

        cycle = self.update_task(
            first["id"],
            dependencies=[{"predecessor_task_id": second["id"]}],
        )
        self.assertEqual(cycle.status_code, 422)
        persisted = self.client.get(
            self.tasks_url,
            headers=self.headers,
        ).json()["tasks"]
        first_row = next(row for row in persisted if row["id"] == first["id"])
        self.assertEqual(first_row["dependencies"], [])

    def test_cross_project_and_summary_dependencies_are_rejected(self):
        predecessor = self.create_task("Predecessor")
        other_project = self.create_project(self.headers, "Other project")
        other = self.client.post(
            f"/projects/{other_project}/tasks",
            json={"name": "Other", "duration": 1},
            headers=self.headers,
        ).json()["tasks"][0]
        cross_project = self.create_task_response(
            "Cross project",
            dependencies=[{"predecessor_task_id": other["id"]}],
        )
        self.assertEqual(cross_project.status_code, 422)

        parent = self.create_task("Summary")
        child = self.create_task("Child", parent_task_id=parent["id"])
        self.assertIsNotNone(child)
        summary = self.update_task(
            parent["id"],
            dependencies=[{"predecessor_task_id": predecessor["id"]}],
        )
        self.assertEqual(summary.status_code, 422)

    def create_task_response(self, name, duration=1, **values):
        return self.client.post(
            self.tasks_url,
            json={"name": name, "duration": duration, **values},
            headers=self.headers,
        )

    def test_dependency_count_and_unknown_fields_are_rejected(self):
        predecessors = [self.create_task(f"Task {index}") for index in range(2)]
        too_many = [
            {"predecessor_task_id": predecessors[index % 2]["id"]}
            for index in range(51)
        ]
        response = self.create_task_response(
            "Bounded",
            dependencies=too_many,
        )
        self.assertEqual(response.status_code, 422)

        unknown = self.create_task_response(
            "Unknown",
            dependencies=[
                {
                    "predecessor_task_id": predecessors[0]["id"],
                    "relationship": "FS",
                }
            ],
        )
        self.assertEqual(unknown.status_code, 422)

    def test_milestone_creation_progress_and_conversion_rules(self):
        milestone = self.create_task(
            "Notice to proceed",
            duration=0,
            is_milestone=True,
        )
        self.assertEqual(milestone["start_date"], milestone["end_date"])
        self.assertEqual(milestone["remaining_duration"], 0)
        self.assertTrue(milestone["is_milestone"])

        invalid_progress = self.client.put(
            f"{self.tasks_url}/{milestone['id']}/progress",
            json={
                "progress_status": "in_progress",
                "percent_complete": 50,
                "actual_start_date": milestone["start_date"],
                "remaining_duration": 0,
            },
            headers=self.headers,
        )
        self.assertEqual(invalid_progress.status_code, 422)
        regular = self.create_task("Active task", duration=2)
        started = self.client.put(
            f"{self.tasks_url}/{regular['id']}/progress",
            json={
                "progress_status": "in_progress",
                "percent_complete": 50,
                "actual_start_date": regular["start_date"],
                "remaining_duration": 1,
            },
            headers=self.headers,
        )
        self.assertEqual(started.status_code, 200)
        invalid_conversion = self.update_task(
            regular["id"],
            is_milestone=True,
            duration=0,
        )
        self.assertEqual(invalid_conversion.status_code, 422)
        invalid_duration = self.create_task_response(
            "Invalid milestone",
            duration=1,
            is_milestone=True,
        )
        self.assertEqual(invalid_duration.status_code, 422)
        invalid_regular = self.create_task_response("Invalid regular", duration=0)
        self.assertEqual(invalid_regular.status_code, 422)

    def test_constraint_validation_and_derived_violation(self):
        settings = self.client.put(
            f"/projects/{self.project_id}/schedule-settings",
            json={
                "schedule_start_date": "2026-03-02",
                "data_date": "2026-03-02",
            },
            headers=self.headers,
        )
        self.assertEqual(settings.status_code, 200)
        invalid_payloads = [
            {"constraint_type": "SNET"},
            {
                "constraint_type": "ASAP",
                "constraint_date": "2026-03-02",
            },
            {
                "constraint_type": "SNET",
                "constraint_date": "2026-03-07",
            },
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.create_task_response("Invalid", **payload)
                self.assertEqual(response.status_code, 422)

        constrained = self.create_task(
            "Constrained",
            constraint_type="SNET",
            constraint_date="2026-03-09",
        )
        self.assertEqual(constrained["start_date"], "2026-03-09")
        self.assertFalse(constrained["constraint_violated"])

    def test_dependency_update_rolls_back_atomically(self):
        first = self.create_task("First")
        second = self.create_task("Second")
        successor = self.create_task(
            "Successor",
            dependencies=[{"predecessor_task_id": first["id"]}],
        )

        with patch(
            "app.api.routes_task.recalculate_schedule",
            side_effect=RuntimeError("calculation failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.update_task(
                    successor["id"],
                    dependencies=[
                        {"predecessor_task_id": second["id"]}
                    ],
                )

        with self.TestingSession() as db:
            dependencies = (
                db.query(TaskDependency)
                .filter(TaskDependency.task_id == successor["id"])
                .all()
            )
            self.assertEqual(len(dependencies), 1)
            self.assertEqual(
                dependencies[0].predecessor_task_id,
                first["id"],
            )
            task = db.get(Task, successor["id"])
            self.assertEqual(task.predecessor_task_id, first["id"])

    def test_deleting_primary_predecessor_promotes_next_dependency(self):
        first = self.create_task("First")
        second = self.create_task("Second")
        successor = self.create_task(
            "Successor",
            dependencies=[
                {"predecessor_task_id": first["id"]},
                {
                    "predecessor_task_id": second["id"],
                    "dependency_type": "SS",
                    "lag_days": -1,
                },
            ],
        )

        deleted = self.client.delete(
            f"{self.tasks_url}/{first['id']}",
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 200, deleted.text)
        row = next(
            task
            for task in deleted.json()["tasks"]
            if task["id"] == successor["id"]
        )
        self.assertEqual(row["predecessor_task_id"], second["id"])
        self.assertEqual(row["dependency_type"], "SS")
        self.assertEqual(row["lag_days"], -1)
        self.assertEqual(len(row["dependencies"]), 1)

    def test_authentication_and_project_ownership_are_preserved(self):
        self.assertEqual(self.client.get(self.tasks_url).status_code, 401)
        other_headers = self.register_and_login("advanced-other@example.com")
        response = self.client.get(self.tasks_url, headers=other_headers)
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
