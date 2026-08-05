import unittest

from sqlalchemy import event

from app.models.resource_planning import TaskResourceAssignment
from app.models.task import Task
from tests.test_api import ApiTestCase


class ResourcePlanningApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers, "Resource Plan")
        settings = self.client.put(
            f"/projects/{self.project_id}/schedule-settings",
            json={
                "schedule_start_date": "2026-08-03",
                "data_date": "2026-08-10",
            },
            headers=self.headers,
        )
        self.assertEqual(settings.status_code, 200, settings.text)

    def create_task(self, name="Install work", **values):
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

    def create_crew(self, name="Electrical Crew", **values):
        response = self.client.post(
            f"/projects/{self.project_id}/crews",
            json={"name": name, "default_capacity": 4, **values},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["crew"]

    def create_equipment(self, name="Lift 1", **values):
        response = self.client.post(
            f"/projects/{self.project_id}/equipment-resources",
            json={
                "name": name,
                "equipment_type": "Scissor Lift",
                "default_capacity": 1,
                **values,
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["equipment"]

    def assign(self, task_id, resource_type, resource_id, amount=1):
        response = self.client.post(
            f"/projects/{self.project_id}/tasks/{task_id}/resource-assignments",
            json={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "allocation_amount": amount,
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["assignment"]

    def test_authentication_and_project_ownership_are_enforced(self):
        self.assertEqual(
            self.client.get(f"/projects/{self.project_id}/crews").status_code,
            401,
        )
        intruder = self.register_and_login("resource-intruder@example.com")
        urls = [
            f"/projects/{self.project_id}/crews",
            f"/projects/{self.project_id}/equipment-resources",
            f"/projects/{self.project_id}/resource-loading",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url, headers=intruder).status_code,
                    403,
                )

    def test_crew_and_equipment_crud_archive_and_uniqueness(self):
        company = self.client.post(
            f"/projects/{self.project_id}/companies",
            json={"name": "Desert Electric", "trade": "Electrical"},
            headers=self.headers,
        ).json()
        crew = self.create_crew(
            trade="Electrical",
            company_id=company["id"],
            description="Day shift",
        )
        self.assertEqual(crew["company"]["name"], "Desert Electric")
        self.assertEqual(crew["capacity_unit"], "workers")
        duplicate = self.client.post(
            f"/projects/{self.project_id}/crews",
            json={"name": "electrical crew", "default_capacity": 8},
            headers=self.headers,
        )
        self.assertEqual(duplicate.status_code, 409)
        updated = self.client.put(
            f"/projects/{self.project_id}/crews/{crew['id']}",
            json={"name": "Electrical A", "default_capacity": 6},
            headers=self.headers,
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["crew"]["default_capacity"], 6)

        equipment = self.create_equipment(identifier="SL-01")
        self.assertEqual(equipment["capacity_unit"], "units")
        duplicate_identifier = self.client.post(
            f"/projects/{self.project_id}/equipment-resources",
            json={
                "name": "Lift 2",
                "equipment_type": "Scissor Lift",
                "identifier": "sl-01",
            },
            headers=self.headers,
        )
        self.assertEqual(duplicate_identifier.status_code, 409)
        listing = self.client.get(
            f"/projects/{self.project_id}/equipment-resources?limit=1&offset=0",
            headers=self.headers,
        ).json()
        self.assertEqual((listing["total"], listing["limit"]), (1, 1))

        archived = self.client.post(
            f"/projects/{self.project_id}/crews/{crew['id']}/archive",
            headers=self.headers,
        )
        self.assertEqual(archived.status_code, 200)
        self.assertEqual(archived.json()["crew"]["status"], "archived")
        rejected_update = self.client.put(
            f"/projects/{self.project_id}/crews/{crew['id']}",
            json={"default_capacity": 7},
            headers=self.headers,
        )
        self.assertEqual(rejected_update.status_code, 409)

    def test_resource_and_assignment_validation_is_strict(self):
        invalid_resources = [
            ("crews", {"name": " ", "default_capacity": 1}),
            ("crews", {"name": "Crew", "default_capacity": 0}),
            (
                "equipment-resources",
                {"name": "Lift", "equipment_type": " ", "default_capacity": 1},
            ),
            (
                "equipment-resources",
                {"name": "Lift", "equipment_type": "Lift", "status": "active"},
            ),
        ]
        for path, payload in invalid_resources:
            with self.subTest(path=path, payload=payload):
                response = self.client.post(
                    f"/projects/{self.project_id}/{path}",
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

        task = self.create_task()
        crew = self.create_crew()
        for payload in [
            {"resource_type": "company", "resource_id": crew["id"], "allocation_amount": 1},
            {"resource_type": "crew", "resource_id": crew["id"], "allocation_amount": 0},
            {
                "resource_type": "crew",
                "resource_id": crew["id"],
                "allocation_amount": 1,
                "allocation_unit": "workers",
            },
        ]:
            with self.subTest(payload=payload):
                response = self.client.post(
                    f"/projects/{self.project_id}/tasks/{task['id']}/resource-assignments",
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_assignment_lifecycle_preserves_schedule_and_rejects_invalid_targets(self):
        task = self.create_task()
        crew = self.create_crew()
        equipment = self.create_equipment()
        schedule_before = (task["start_date"], task["end_date"])
        crew_assignment = self.assign(task["id"], "crew", crew["id"], 3)
        equipment_assignment = self.assign(task["id"], "equipment", equipment["id"])
        duplicate = self.client.post(
            f"/projects/{self.project_id}/tasks/{task['id']}/resource-assignments",
            json={"resource_type": "crew", "resource_id": crew["id"], "allocation_amount": 2},
            headers=self.headers,
        )
        self.assertEqual(duplicate.status_code, 409)
        listing = self.client.get(
            f"/projects/{self.project_id}/tasks/{task['id']}/resource-assignments",
            headers=self.headers,
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()["assignments"]), 2)
        self.assertEqual(
            {row["allocation_unit"] for row in listing.json()["assignments"]},
            {"workers", "units"},
        )
        updated = self.client.put(
            f"/projects/{self.project_id}/tasks/{task['id']}/resource-assignments/{crew_assignment['id']}",
            json={"allocation_amount": 4, "notes": "Full crew"},
            headers=self.headers,
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["assignment"]["allocation_amount"], 4)
        with self.TestingSession() as session:
            persisted = session.get(Task, task["id"])
            self.assertEqual((persisted.start_date, persisted.end_date), schedule_before)

        deleted = self.client.delete(
            f"/projects/{self.project_id}/tasks/{task['id']}/resource-assignments/{equipment_assignment['id']}",
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.delete(
                f"/projects/{self.project_id}/tasks/{task['id']}/resource-assignments/99999",
                headers=self.headers,
            ).status_code,
            404,
        )

        milestone = self.create_task(
            "Inspection",
            duration=0,
            is_milestone=True,
        )
        summary = self.create_task("Summary")
        self.create_task("Summary child", parent_task_id=summary["id"])
        for task_id in (milestone["id"], summary["id"]):
            response = self.client.post(
                f"/projects/{self.project_id}/tasks/{task_id}/resource-assignments",
                json={"resource_type": "crew", "resource_id": crew["id"], "allocation_amount": 1},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 422)

    def test_cross_project_and_archived_resources_cannot_be_assigned(self):
        task = self.create_task()
        crew = self.create_crew()
        self.client.post(
            f"/projects/{self.project_id}/crews/{crew['id']}/archive",
            headers=self.headers,
        )
        archived = self.client.post(
            f"/projects/{self.project_id}/tasks/{task['id']}/resource-assignments",
            json={"resource_type": "crew", "resource_id": crew["id"], "allocation_amount": 1},
            headers=self.headers,
        )
        self.assertEqual(archived.status_code, 409)

        other_project = self.create_project(self.headers, "Other resource project")
        foreign = self.client.post(
            f"/projects/{other_project}/crews",
            json={"name": "Foreign Crew", "default_capacity": 2},
            headers=self.headers,
        ).json()["crew"]
        cross_project = self.client.post(
            f"/projects/{self.project_id}/tasks/{task['id']}/resource-assignments",
            json={"resource_type": "crew", "resource_id": foreign["id"], "allocation_amount": 1},
            headers=self.headers,
        )
        self.assertEqual(cross_project.status_code, 404)

    def test_availability_crud_overlap_zero_capacity_and_pagination(self):
        crew = self.create_crew()
        base = f"/projects/{self.project_id}/resources/crew/{crew['id']}/availability"
        created = self.client.post(
            base,
            json={
                "start_date": "2026-08-10",
                "end_date": "2026-08-12",
                "capacity": 0,
                "notes": "Unavailable",
            },
            headers=self.headers,
        )
        self.assertEqual(created.status_code, 201, created.text)
        row = created.json()["availability"]
        self.assertEqual(row["capacity"], 0)
        overlap = self.client.post(
            base,
            json={"start_date": "2026-08-12", "end_date": "2026-08-13", "capacity": 2},
            headers=self.headers,
        )
        self.assertEqual(overlap.status_code, 409)
        adjacent = self.client.post(
            base,
            json={"start_date": "2026-08-13", "end_date": "2026-08-13", "capacity": 2},
            headers=self.headers,
        )
        self.assertEqual(adjacent.status_code, 201, adjacent.text)
        listing = self.client.get(f"{base}?limit=1&offset=1", headers=self.headers)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual((listing.json()["total"], len(listing.json()["availability"])), (2, 1))
        invalid_update = self.client.put(
            f"{base}/{row['id']}",
            json={"end_date": "2026-08-09"},
            headers=self.headers,
        )
        self.assertEqual(invalid_update.status_code, 422)
        updated = self.client.put(
            f"{base}/{row['id']}",
            json={"capacity": 3, "notes": "Reduced shift"},
            headers=self.headers,
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["availability"]["capacity"], 3)
        self.assertEqual(
            self.client.delete(f"{base}/{row['id']}", headers=self.headers).status_code,
            200,
        )

    def test_loading_detects_overallocation_unavailability_and_filters(self):
        first = self.create_task("Electrical rough-in")
        second = self.create_task("Branch wiring")
        crew = self.create_crew(default_capacity=4)
        equipment = self.create_equipment()
        self.assign(first["id"], "crew", crew["id"], 3)
        self.assign(second["id"], "crew", crew["id"], 2)
        self.assign(first["id"], "equipment", equipment["id"], 1)
        unavailable = self.client.post(
            f"/projects/{self.project_id}/resources/equipment/{equipment['id']}/availability",
            json={"start_date": "2026-08-11", "end_date": "2026-08-11", "capacity": 0},
            headers=self.headers,
        )
        self.assertEqual(unavailable.status_code, 201, unavailable.text)

        response = self.client.get(
            f"/projects/{self.project_id}/resource-loading?start_date=2026-08-10&end_date=2026-08-16",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        crew_row = next(row for row in body["resources"] if row["resource"]["resource_type"] == "crew")
        monday = next(day for day in crew_row["days"] if day["date"] == "2026-08-10")
        saturday = next(day for day in crew_row["days"] if day["date"] == "2026-08-15")
        self.assertEqual((monday["demand"], monday["capacity"], monday["overage"]), (5, 4, 1))
        self.assertEqual(monday["status"], "over_allocated")
        self.assertEqual((saturday["demand"], saturday["capacity"]), (0, 0))
        equipment_conflict = next(
            row for row in body["conflicts"]
            if row["resource"]["resource_type"] == "equipment"
        )
        self.assertEqual((equipment_conflict["date"], equipment_conflict["status"]), ("2026-08-11", "unavailable"))
        self.assertEqual(body["summary"]["peak_labor_demand"], 5)
        self.assertGreaterEqual(body["summary"]["over_allocated_resource_days"], 4)

        filtered = self.client.get(
            f"/projects/{self.project_id}/resource-loading?resource_type=equipment&resource_id={equipment['id']}&over_allocated_only=true",
            headers=self.headers,
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        self.assertEqual(filtered.json()["total_resources"], 1)
        self.assertTrue(all(row["resource"]["resource_type"] == "equipment" for row in filtered.json()["resources"]))
        self.assertEqual(
            self.client.get(
                f"/projects/{self.project_id}/resource-loading?resource_id={crew['id']}",
                headers=self.headers,
            ).status_code,
            422,
        )

    def test_loading_is_progress_aware_and_summary_is_filter_independent(self):
        active = self.create_task(
            "Carryover work",
            duration=10,
            manual_start_date="2026-08-03",
        )
        completed = self.create_task("Completed work")
        crew = self.create_crew(default_capacity=5)
        self.assign(active["id"], "crew", crew["id"], 2)
        self.assign(completed["id"], "crew", crew["id"], 4)
        progress = self.client.put(
            f"/projects/{self.project_id}/tasks/{active['id']}/progress",
            json={
                "progress_status": "in_progress",
                "percent_complete": 70,
                "actual_start_date": "2026-08-03",
                "remaining_duration": 3,
            },
            headers=self.headers,
        )
        self.assertEqual(progress.status_code, 200, progress.text)
        complete = self.client.put(
            f"/projects/{self.project_id}/tasks/{completed['id']}/progress",
            json={
                "progress_status": "completed",
                "percent_complete": 100,
                "actual_start_date": "2026-08-10",
                "actual_finish_date": "2026-08-10",
                "remaining_duration": 0,
            },
            headers=self.headers,
        )
        self.assertEqual(complete.status_code, 200, complete.text)
        self.create_task("Unassigned work")

        visible = self.client.get(
            f"/projects/{self.project_id}/resource-loading?start_date=2026-08-03&end_date=2026-08-14",
            headers=self.headers,
        ).json()
        hidden = self.client.get(
            f"/projects/{self.project_id}/resource-loading?start_date=2026-08-03&end_date=2026-08-14&include_unassigned=false",
            headers=self.headers,
        ).json()
        row = visible["resources"][0]
        demand = {day["date"]: day["demand"] for day in row["days"]}
        self.assertTrue(all(demand[f"2026-08-0{day}"] == 0 for day in range(3, 8)))
        self.assertEqual(demand["2026-08-10"], 2)
        self.assertEqual(visible["summary"]["unassigned_executable_tasks"], 1)
        self.assertEqual(hidden["summary"]["unassigned_executable_tasks"], 1)
        self.assertEqual(hidden["unassigned_tasks"], [])

    def test_loading_date_bounds_and_filter_validation(self):
        invalid_urls = [
            "?start_date=2026-08-10&end_date=2026-08-09",
            "?start_date=2026-08-01&end_date=2026-11-01",
            "?start_date=08/01/2026",
            "?resource_type=company",
        ]
        for query in invalid_urls:
            with self.subTest(query=query):
                response = self.client.get(
                    f"/projects/{self.project_id}/resource-loading{query}",
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_look_ahead_resource_labels_are_batched(self):
        first = self.create_task("First assignment")
        second = self.create_task("Second assignment", manual_start_date="2026-08-11")
        crew = self.create_crew()
        equipment = self.create_equipment()
        self.assign(first["id"], "crew", crew["id"], 3)
        self.assign(second["id"], "equipment", equipment["id"], 1)
        plan = self.client.post(
            f"/projects/{self.project_id}/look-ahead-plans",
            json={"name": "Resource Coordination"},
            headers=self.headers,
        ).json()["plan"]
        statements = []

        def record_statement(_connection, _cursor, statement, *_args):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", record_statement)
        try:
            response = self.client.get(
                f"/projects/{self.project_id}/look-ahead-plans/{plan['id']}",
                headers=self.headers,
            )
        finally:
            event.remove(self.engine, "before_cursor_execute", record_statement)
        self.assertEqual(response.status_code, 200, response.text)
        items = [item for week in response.json()["weeks"] for item in week["items"]]
        labels = {
            item["name"]: item["resource_assignments"][0]["name"] for item in items
        }
        self.assertEqual(labels, {"First assignment": "Electrical Crew", "Second assignment": "Lift 1"})
        self.assertLessEqual(len(statements), 10)

    def test_task_deletion_cascades_assignments(self):
        task = self.create_task()
        crew = self.create_crew()
        self.assign(task["id"], "crew", crew["id"])
        deleted = self.client.delete(
            f"/projects/{self.project_id}/tasks/{task['id']}",
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 200)
        with self.TestingSession() as session:
            self.assertEqual(session.query(TaskResourceAssignment).count(), 0)


if __name__ == "__main__":
    unittest.main()
