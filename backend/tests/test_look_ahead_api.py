import unittest

from sqlalchemy import event

from app.models.look_ahead import LookAheadItem, LookAheadPlan
from app.models.task import Task
from tests.test_api import ApiTestCase


class LookAheadApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers)
        self.base_url = f"/projects/{self.project_id}/look-ahead-plans"
        response = self.client.put(
            f"/projects/{self.project_id}/schedule-settings",
            json={
                "schedule_start_date": "2026-08-03",
                "data_date": "2026-08-10",
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)

    def create_task(self, name, **values):
        response = self.client.post(
            f"/projects/{self.project_id}/tasks",
            json={"name": name, "duration": 1, **values},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return next(
            row for row in response.json()["tasks"] if row["name"] == name
        )

    def create_plan(self, name="Three-Week Look-Ahead", **values):
        response = self.client.post(
            self.base_url,
            json={"name": name, **values},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["plan"]

    def detail(self, plan_id):
        response = self.client.get(
            f"{self.base_url}/{plan_id}",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def update_item(self, plan_id, task_id, **values):
        return self.client.put(
            f"{self.base_url}/{plan_id}/items/{task_id}",
            json=values,
            headers=self.headers,
        )

    def test_create_defaults_to_data_date_and_lists_newest_first(self):
        task = self.create_task(
            "Week one work",
            manual_start_date="2026-08-10",
        )
        before = self.TestingSession().get(Task, task["id"])
        before_dates = (before.start_date, before.end_date)
        plan = self.create_plan(description="Coordination plan")

        self.assertEqual(plan["anchor_date"], "2026-08-10")
        self.assertEqual(plan["window_days"], 21)
        self.assertEqual(plan["status"], "active")
        self.assertNotIn("normalized_name", plan)
        second = self.create_plan(
            "Four-Week Look-Ahead",
            anchor_date="2026-08-17",
            window_days=28,
        )
        listing = self.client.get(
            f"{self.base_url}?status=all&limit=10&offset=0",
            headers=self.headers,
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            [row["id"] for row in listing.json()["plans"]],
            [second["id"], plan["id"]],
        )
        after = self.TestingSession().get(Task, task["id"])
        self.assertEqual((after.start_date, after.end_date), before_dates)

    def test_duplicate_validation_and_mass_assignment_are_safe(self):
        self.create_plan("Coordination Plan")
        duplicate = self.client.post(
            self.base_url,
            json={"name": "coordination plan"},
            headers=self.headers,
        )
        self.assertEqual(duplicate.status_code, 409)

        invalid_payloads = [
            {"name": "Short", "window_days": 6},
            {"name": "Long", "window_days": 43},
            {"name": "Bad date", "anchor_date": "08/10/2026"},
            {"name": "Owned", "project_id": self.project_id},
            {"name": "Derived", "total_items": 9},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    self.base_url,
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_inclusion_grouping_carryover_milestone_and_exclusions(self):
        carryover = self.create_task(
            "Carryover",
            duration=10,
            manual_start_date="2026-08-03",
        )
        carryover_progress = self.client.put(
            f"/projects/{self.project_id}/tasks/{carryover['id']}/progress",
            json={
                "progress_status": "in_progress",
                "percent_complete": 50,
                "actual_start_date": "2026-08-03",
                "remaining_duration": 5,
            },
            headers=self.headers,
        )
        self.assertEqual(carryover_progress.status_code, 200)
        week_one = self.create_task(
            "Week one",
            manual_start_date="2026-08-10",
        )
        week_two = self.create_task(
            "Week two",
            manual_start_date="2026-08-17",
        )
        week_three = self.create_task(
            "Week three",
            manual_start_date="2026-08-24",
        )
        milestone = self.create_task(
            "Inspection milestone",
            duration=0,
            is_milestone=True,
            manual_start_date="2026-08-18",
        )
        completed = self.create_task(
            "Already complete",
            manual_start_date="2026-08-03",
        )
        completed_response = self.client.put(
            f"/projects/{self.project_id}/tasks/{completed['id']}/progress",
            json={
                "progress_status": "completed",
                "percent_complete": 100,
                "actual_start_date": "2026-08-03",
                "actual_finish_date": "2026-08-03",
                "remaining_duration": 0,
            },
            headers=self.headers,
        )
        self.assertEqual(completed_response.status_code, 200)
        plan = self.create_plan()
        detail = self.detail(plan["id"])

        self.assertEqual(detail["window_end_date"], "2026-08-30")
        self.assertEqual(len(detail["weeks"]), 3)
        self.assertEqual(
            [(week["start_date"], week["end_date"]) for week in detail["weeks"]],
            [
                ("2026-08-10", "2026-08-16"),
                ("2026-08-17", "2026-08-23"),
                ("2026-08-24", "2026-08-30"),
            ],
        )
        self.assertEqual(
            [item["task_id"] for item in detail["carryover_items"]],
            [carryover["id"]],
        )
        self.assertEqual(
            [[item["task_id"] for item in week["items"]] for week in detail["weeks"]],
            [[week_one["id"]], [week_two["id"], milestone["id"]], [week_three["id"]]],
        )
        self.assertEqual(detail["summary"]["total_items"], 5)
        self.assertEqual(detail["summary"]["week_counts"], [1, 2, 1])
        self.assertEqual(detail["summary"]["milestones_count"], 1)
        visible_ids = {
            item["task_id"]
            for week in detail["weeks"]
            for item in week["items"]
        }
        self.assertNotIn(completed["id"], visible_ids)

    def test_metadata_company_attention_and_progress_separation(self):
        task = self.create_task(
            "Coordinate embeds",
            manual_start_date="2026-08-10",
        )
        company = self.client.post(
            f"/projects/{self.project_id}/companies",
            json={"name": "Desert Concrete", "trade": "Concrete"},
            headers=self.headers,
        ).json()
        plan = self.create_plan()
        updated = self.update_item(
            plan["id"],
            task["id"],
            readiness_status="blocked",
            blocking_reason="Approved embed layout is missing",
            constraint_category="design_information",
            constraint_owner="Architect",
            target_resolution_date="2026-08-12",
            commitment_note="Layout due before Wednesday coordination",
            responsible_company_id=company["id"],
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        item = updated.json()["weeks"][0]["items"][0]
        self.assertEqual(item["readiness_status"], "blocked")
        self.assertTrue(item["blocked"])
        self.assertTrue(item["constraint_due"])
        self.assertFalse(item["commitment_missing"])
        self.assertEqual(item["responsible_company"]["trade"], "Concrete")
        self.assertEqual(item["progress_status"], "not_started")
        persisted = self.TestingSession().get(Task, task["id"])
        self.assertEqual(persisted.progress_status, "not_started")

    def test_manual_include_exclude_and_live_schedule_changes(self):
        in_window = self.create_task(
            "Window task",
            manual_start_date="2026-08-10",
        )
        future = self.create_task(
            "Future task",
            manual_start_date="2026-09-14",
        )
        plan = self.create_plan()
        initial = self.detail(plan["id"])
        self.assertEqual(initial["summary"]["total_items"], 1)

        included = self.update_item(
            plan["id"],
            future["id"],
            manually_included=True,
            override_reason="Early procurement coordination",
            readiness_status="at_risk",
        )
        self.assertEqual(included.status_code, 200, included.text)
        self.assertEqual(
            included.json()["manual_items"][0]["task_id"],
            future["id"],
        )
        excluded = self.update_item(
            plan["id"],
            in_window["id"],
            manually_excluded=True,
            override_reason="Work moved to the next planning cycle",
        )
        self.assertEqual(excluded.status_code, 200, excluded.text)
        self.assertEqual(
            excluded.json()["excluded_items"][0]["task_id"],
            in_window["id"],
        )
        self.assertEqual(excluded.json()["summary"]["total_items"], 1)

        shifted = self.client.put(
            f"/projects/{self.project_id}/tasks/{future['id']}",
            json={"manual_start_date": "2026-08-24"},
            headers=self.headers,
        )
        self.assertEqual(shifted.status_code, 200)
        refreshed = self.detail(plan["id"])
        week_three_ids = [
            item["task_id"] for item in refreshed["weeks"][2]["items"]
        ]
        self.assertIn(future["id"], week_three_ids)

    def test_invalid_item_fields_summary_tasks_and_cross_project_company(self):
        parent = self.create_task("Summary")
        child = self.create_task("Child", parent_task_id=parent["id"])
        plan = self.create_plan()
        invalid_payloads = [
            {"readiness_status": "waiting"},
            {"constraint_category": "money"},
            {"start_date": "2026-08-10"},
            {"percent_complete": 50},
            {"manually_included": True, "manually_excluded": True},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.update_item(plan["id"], child["id"], **payload)
                self.assertEqual(response.status_code, 422)

        summary = self.update_item(
            plan["id"], parent["id"], readiness_status="ready"
        )
        self.assertEqual(summary.status_code, 422)
        other_project = self.create_project(self.headers, "Other")
        other_company = self.client.post(
            f"/projects/{other_project}/companies",
            json={"name": "Foreign Company"},
            headers=self.headers,
        ).json()
        cross_project = self.update_item(
            plan["id"],
            child["id"],
            responsible_company_id=other_company["id"],
        )
        self.assertEqual(cross_project.status_code, 422)

    def test_update_archive_and_archived_plan_is_read_only(self):
        task = self.create_task("Active work", manual_start_date="2026-08-10")
        plan = self.create_plan()
        updated = self.client.put(
            f"{self.base_url}/{plan['id']}",
            json={
                "name": "Updated Look-Ahead",
                "anchor_date": "2026-08-17",
                "window_days": 14,
            },
            headers=self.headers,
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["plan"]["window_days"], 14)
        archived = self.client.post(
            f"{self.base_url}/{plan['id']}/archive",
            headers=self.headers,
        )
        self.assertEqual(archived.status_code, 200)
        self.assertEqual(archived.json()["plan"]["status"], "archived")
        self.assertIsNotNone(archived.json()["plan"]["archived_at"])
        item_update = self.update_item(
            plan["id"], task["id"], readiness_status="ready"
        )
        self.assertEqual(item_update.status_code, 409)
        plan_update = self.client.put(
            f"{self.base_url}/{plan['id']}",
            json={"name": "Too late"},
            headers=self.headers,
        )
        self.assertEqual(plan_update.status_code, 409)
        self.assertEqual(self.detail(plan["id"])["plan"]["status"], "archived")

    def test_ownership_missing_ids_and_authentication(self):
        task = self.create_task("Owned task", manual_start_date="2026-08-10")
        plan = self.create_plan()
        intruder = self.register_and_login("intruder-lookahead@example.com")
        for method, url, payload in [
            ("get", self.base_url, None),
            ("get", f"{self.base_url}/{plan['id']}", None),
            ("put", f"{self.base_url}/{plan['id']}", {"name": "Foreign"}),
            (
                "put",
                f"{self.base_url}/{plan['id']}/items/{task['id']}",
                {"readiness_status": "ready"},
            ),
        ]:
            with self.subTest(method=method, url=url):
                kwargs = {"headers": intruder}
                if payload is not None:
                    kwargs["json"] = payload
                response = getattr(self.client, method)(url, **kwargs)
                self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.client.get(f"{self.base_url}/99999", headers=self.headers).status_code,
            404,
        )
        self.assertEqual(self.client.get(self.base_url).status_code, 401)

    def test_detail_query_count_is_bounded(self):
        first = self.create_task("First", manual_start_date="2026-08-10")
        for index in range(12):
            self.create_task(
                f"Task {index}",
                dependencies=[{"predecessor_task_id": first["id"]}],
            )
        plan = self.create_plan()
        statements = []

        def record_statement(_connection, _cursor, statement, *_args):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", record_statement)
        try:
            response = self.client.get(
                f"{self.base_url}/{plan['id']}",
                headers=self.headers,
            )
        finally:
            event.remove(self.engine, "before_cursor_execute", record_statement)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertLessEqual(len(statements), 8)

    def test_detail_scales_to_supported_schedule_sizes(self):
        for task_count in (100, 500, 2000):
            with self.subTest(task_count=task_count):
                with self.TestingSession() as session:
                    session.add_all(
                        Task(
                            project_id=self.project_id,
                            name=f"Scale task {index + 1}",
                            duration=1,
                            remaining_duration=1,
                            start_date="2026-08-10",
                            end_date="2026-08-10",
                            order_index=index,
                        )
                        for index in range(task_count)
                    )
                    session.commit()

                plan = self.create_plan(f"Scale {task_count}")
                response = self.client.get(
                    f"{self.base_url}/{plan['id']}",
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(
                    response.json()["summary"]["total_items"],
                    task_count,
                )
                self.assertLess(len(response.content), 5_000_000)

                with self.TestingSession() as session:
                    session.query(LookAheadPlan).filter(
                        LookAheadPlan.project_id == self.project_id
                    ).delete(synchronize_session=False)
                    session.query(Task).filter(
                        Task.project_id == self.project_id
                    ).delete(synchronize_session=False)
                    session.commit()

    def test_deleted_task_metadata_remains_factual(self):
        task = self.create_task("Temporary task", manual_start_date="2026-08-10")
        plan = self.create_plan()
        updated = self.update_item(
            plan["id"], task["id"], readiness_status="ready"
        )
        self.assertEqual(updated.status_code, 200)
        deleted = self.client.delete(
            f"/projects/{self.project_id}/tasks/{task['id']}",
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 200)
        detail = self.detail(plan["id"])
        unavailable = detail["manual_items"][0]
        self.assertEqual(unavailable["task_id"], task["id"])
        self.assertFalse(unavailable["task_available"])
        self.assertIsNone(unavailable["name"])
        with self.TestingSession() as session:
            self.assertEqual(session.query(LookAheadItem).count(), 1)
            self.assertEqual(session.query(LookAheadPlan).count(), 1)


if __name__ == "__main__":
    unittest.main()
