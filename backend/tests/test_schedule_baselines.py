import unittest
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.models.schedule_baseline import (
    ScheduleBaseline,
    ScheduleBaselineTask,
)
from app.services.task_scheduling import lock_project_schedule
from tests.test_api import ApiTestCase


class ScheduleBaselineApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers)
        self.base_url = f"/projects/{self.project_id}/schedule-baselines"
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

    def capture(self, name="Original Plan", description=None):
        response = self.client.post(
            self.base_url,
            json={"name": name, "description": description},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_capture_snapshots_coherent_nested_schedule_and_selects_it(self):
        parent = self.create_task("Foundation")
        child = self.create_task("Excavate", manual_start_date="2026-03-02")
        nested = self.client.put(
            f"{self.tasks_url}/{child['id']}",
            json={"parent_task_id": parent["id"]},
            headers=self.headers,
        )
        self.assertEqual(nested.status_code, 200)
        successor = self.create_task(
            "Framing",
            predecessor_task_id=parent["id"],
            dependency_type="FS",
            lag_days=2,
        )

        captured = self.capture(
            description="Issued construction schedule"
        )
        baseline = captured["baseline"]
        self.assertEqual(captured["comparison_baseline_id"], baseline["id"])
        self.assertEqual(baseline["task_count"], 3)
        self.assertEqual(baseline["status"], "active")
        self.assertEqual(
            baseline["description"],
            "Issued construction schedule",
        )

        settings = self.client.get(
            f"/projects/{self.project_id}/schedule-settings",
            headers=self.headers,
        ).json()
        self.assertEqual(settings["comparison_baseline_id"], baseline["id"])

        detail = self.client.get(
            f"{self.base_url}/{baseline['id']}?limit=10&offset=0",
            headers=self.headers,
        )
        self.assertEqual(detail.status_code, 200)
        snapshots = detail.json()["tasks"]
        self.assertEqual(detail.json()["total"], 3)
        by_name = {task["name"]: task for task in snapshots}
        self.assertTrue(by_name["Foundation"]["is_summary"])
        self.assertEqual(by_name["Foundation"]["wbs_path"], "1")
        self.assertEqual(by_name["Excavate"]["wbs_path"], "1.1")
        self.assertEqual(
            by_name["Framing"]["predecessor_task_id"],
            parent["id"],
        )
        self.assertGreater(
            by_name["Framing"]["start_date"],
            by_name["Foundation"]["end_date"],
        )
        self.assertIn(by_name["Framing"]["was_critical"], (True, False))
        self.assertIsNotNone(by_name["Framing"]["total_float"])
        self.assertEqual(by_name["Framing"]["task_id"], successor["id"])

    def test_snapshot_is_immutable_after_live_edit_and_delete(self):
        first = self.create_task(
            "Original task",
            duration=2,
            manual_start_date="2026-03-02",
        )
        baseline = self.capture()["baseline"]
        before = self.client.get(
            f"{self.base_url}/{baseline['id']}",
            headers=self.headers,
        ).json()["tasks"][0]

        updated = self.client.put(
            f"{self.tasks_url}/{first['id']}",
            json={"name": "Renamed live task", "duration": 5},
            headers=self.headers,
        )
        self.assertEqual(updated.status_code, 200)
        deleted = self.client.delete(
            f"{self.tasks_url}/{first['id']}",
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 200)

        after = self.client.get(
            f"{self.base_url}/{baseline['id']}",
            headers=self.headers,
        ).json()["tasks"][0]
        self.assertEqual(after, before)
        self.assertEqual(after["name"], "Original task")
        self.assertEqual(after["task_id"], first["id"])

        self.assertEqual(
            self.client.put(
                f"{self.base_url}/{baseline['id']}",
                json={"name": "Replacement"},
                headers=self.headers,
            ).status_code,
            405,
        )
        self.assertEqual(
            self.client.delete(
                f"{self.base_url}/{baseline['id']}",
                headers=self.headers,
            ).status_code,
            405,
        )

    def test_empty_capture_duplicate_name_and_mass_assignment_validation(self):
        empty = self.capture(name="  Bid Plan  ")
        self.assertEqual(empty["baseline"]["name"], "Bid Plan")
        self.assertEqual(empty["baseline"]["task_count"], 0)

        duplicate = self.client.post(
            self.base_url,
            json={"name": "bid plan"},
            headers=self.headers,
        )
        self.assertEqual(duplicate.status_code, 409)

        invalid_payloads = [
            {"name": "   "},
            {"name": "Plan", "project_id": self.project_id},
            {"name": "Plan", "captured_at": "2026-03-02"},
            {"name": "Plan", "task_count": 2},
            {"name": "Plan", "tasks": []},
            {"name": "x" * 121},
            {"name": "Plan", "description": "x" * 2_001},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=list(payload)):
                response = self.client.post(
                    self.base_url,
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

        listing = self.client.get(
            self.base_url,
            headers=self.headers,
        ).json()
        self.assertEqual(listing["total"], 1)

    def test_list_archive_and_selection_lifecycle(self):
        first = self.capture("First")["baseline"]
        second = self.capture("Second")["baseline"]

        listing = self.client.get(
            f"{self.base_url}?status=all&limit=10&offset=0",
            headers=self.headers,
        ).json()
        self.assertEqual(
            [baseline["name"] for baseline in listing["baselines"]],
            ["Second", "First"],
        )
        self.assertEqual(listing["comparison_baseline_id"], second["id"])

        selected = self.client.put(
            f"/projects/{self.project_id}/schedule-baseline-comparison",
            json={"baseline_id": first["id"]},
            headers=self.headers,
        )
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected.json()["comparison_baseline_id"], first["id"])

        archived = self.client.post(
            f"{self.base_url}/{first['id']}/archive",
            headers=self.headers,
        )
        self.assertEqual(archived.status_code, 200)
        self.assertEqual(archived.json()["baseline"]["status"], "archived")
        self.assertIsNone(archived.json()["comparison_baseline_id"])
        archived_again = self.client.post(
            f"{self.base_url}/{first['id']}/archive",
            headers=self.headers,
        )
        self.assertEqual(archived_again.status_code, 200)
        self.assertEqual(
            archived_again.json()["baseline"]["archived_at"],
            archived.json()["baseline"]["archived_at"],
        )

        self.assertEqual(
            self.client.get(
                f"{self.base_url}?status=active",
                headers=self.headers,
            ).json()["total"],
            1,
        )
        self.assertEqual(
            self.client.get(
                f"{self.base_url}?status=archived",
                headers=self.headers,
            ).json()["total"],
            1,
        )
        rejected = self.client.put(
            f"/projects/{self.project_id}/schedule-baseline-comparison",
            json={"baseline_id": first["id"]},
            headers=self.headers,
        )
        self.assertEqual(rejected.status_code, 409)

        cleared = self.client.put(
            f"/projects/{self.project_id}/schedule-baseline-comparison",
            json={"baseline_id": None},
            headers=self.headers,
        )
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.json()["comparison_baseline_id"])

    def test_authentication_ownership_and_guessed_ids_are_safe(self):
        task = self.create_task("Private schedule task")
        baseline = self.capture()["baseline"]
        other_headers = self.register_and_login("other@example.com")
        other_project = self.create_project(other_headers, "Other")
        other_url = f"/projects/{other_project}/schedule-baselines"
        other_baseline = self.client.post(
            other_url,
            json={"name": "Other plan"},
            headers=other_headers,
        ).json()["baseline"]

        protected = [
            ("get", self.base_url, None),
            ("post", self.base_url, {"name": "Unauthorized"}),
            ("get", f"{self.base_url}/{baseline['id']}", None),
            ("post", f"{self.base_url}/{baseline['id']}/archive", None),
            (
                "put",
                f"/projects/{self.project_id}/schedule-baseline-comparison",
                {"baseline_id": baseline["id"]},
            ),
            ("get", f"/projects/{self.project_id}/schedule-variance", None),
        ]
        for method, url, body in protected:
            with self.subTest(method=method, url=url):
                request = getattr(self.client, method)
                response = request(url, json=body) if body else request(url)
                self.assertEqual(response.status_code, 401)

        foreign = self.client.get(self.base_url, headers=other_headers)
        self.assertEqual(foreign.status_code, 403)
        guessed = self.client.get(
            f"{self.base_url}/{other_baseline['id']}",
            headers=self.headers,
        )
        self.assertEqual(guessed.status_code, 404)
        self.assertNotIn("Private schedule task", guessed.text)
        self.assertEqual(
            self.client.post(
                f"{self.base_url}/{other_baseline['id']}/archive",
                headers=self.headers,
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.put(
                f"/projects/{self.project_id}/schedule-baseline-comparison",
                json={"baseline_id": other_baseline["id"]},
                headers=self.headers,
            ).status_code,
            404,
        )
        self.assertGreater(task["id"], 0)

    def test_capture_and_task_mutation_use_the_same_project_lock(self):
        with patch(
            "app.services.schedule_baseline.lock_project_schedule",
            wraps=lock_project_schedule,
        ) as baseline_lock:
            self.capture()
        baseline_lock.assert_called_once()

        with patch(
            "app.api.routes_task.lock_project_schedule",
            wraps=lock_project_schedule,
        ) as task_lock:
            self.create_task("Serialized mutation")
        task_lock.assert_called_once()

    def test_capture_rolls_back_header_snapshot_critical_and_commit_failures(self):
        self.create_task("Stable task", manual_start_date="2026-03-02")
        before = self.client.get(
            self.tasks_url,
            headers=self.headers,
        ).json()

        failures = [
            patch.object(
                Session,
                "add",
                side_effect=RuntimeError("header failed"),
            ),
            patch.object(
                Session,
                "add_all",
                side_effect=RuntimeError("snapshot failed"),
            ),
            patch(
                "app.services.schedule_baseline.annotate_critical_path",
                side_effect=RuntimeError("critical path failed"),
            ),
            patch.object(
                Session,
                "commit",
                side_effect=RuntimeError("commit failed"),
            ),
        ]
        for index, failure in enumerate(failures):
            with self.subTest(index=index):
                with failure:
                    with self.assertRaises(RuntimeError):
                        self.client.post(
                            self.base_url,
                            json={"name": f"Failure {index}"},
                            headers=self.headers,
                        )

                with self.TestingSession() as db:
                    self.assertEqual(db.query(ScheduleBaseline).count(), 0)
                    self.assertEqual(db.query(ScheduleBaselineTask).count(), 0)
                self.assertEqual(
                    self.client.get(
                        self.tasks_url,
                        headers=self.headers,
                    ).json(),
                    before,
                )

    def test_comparison_pointer_update_failure_rolls_back(self):
        first = self.capture("First")["baseline"]
        second = self.capture("Second")["baseline"]
        self.client.put(
            f"/projects/{self.project_id}/schedule-baseline-comparison",
            json={"baseline_id": first["id"]},
            headers=self.headers,
        )

        with patch.object(
            Session,
            "commit",
            side_effect=RuntimeError("pointer commit failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.put(
                    f"/projects/{self.project_id}/schedule-baseline-comparison",
                    json={"baseline_id": second["id"]},
                    headers=self.headers,
                )

        settings = self.client.get(
            f"/projects/{self.project_id}/schedule-settings",
            headers=self.headers,
        ).json()
        self.assertEqual(settings["comparison_baseline_id"], first["id"])


if __name__ == "__main__":
    unittest.main()
