from unittest.mock import patch

from app.models.task import Task
from tests.test_api import ApiTestCase


class RouteAuthenticationMatrixTests(ApiTestCase):
    def test_every_protected_route_rejects_missing_authentication(self):
        routes = [
            ("GET", "/projects"),
            ("POST", "/projects"),
            ("GET", "/projects/1/tasks"),
            ("POST", "/projects/1/tasks"),
            ("PUT", "/projects/1/tasks/reorder"),
            ("PUT", "/projects/1/tasks/1"),
            ("DELETE", "/projects/1/tasks/1"),
            ("GET", "/templates"),
            ("POST", "/projects/1/templates"),
            ("POST", "/projects/1/templates/1/apply"),
            ("GET", "/projects/1/daily-logs"),
            ("POST", "/projects/1/daily-logs"),
            ("GET", "/projects/1/inspections"),
            ("POST", "/projects/1/inspections"),
            ("GET", "/projects/1/notes-delays"),
            ("POST", "/projects/1/notes-delays"),
            ("GET", "/projects/1/companies"),
            ("POST", "/projects/1/companies"),
            ("GET", "/projects/1/change-orders"),
            ("POST", "/projects/1/change-orders"),
            ("PUT", "/projects/1/change-orders/1"),
            ("DELETE", "/projects/1/change-orders/1"),
            ("GET", "/projects/1/rfis"),
            ("POST", "/projects/1/rfis"),
            ("PUT", "/projects/1/rfis/1"),
            ("DELETE", "/projects/1/rfis/1"),
            ("GET", "/projects/1/submittals"),
            ("POST", "/projects/1/submittals"),
            ("PUT", "/projects/1/submittals/1"),
            ("DELETE", "/projects/1/submittals/1"),
            ("GET", "/projects/1/punch-items"),
            ("POST", "/projects/1/punch-items"),
            ("PUT", "/projects/1/punch-items/1"),
            ("DELETE", "/projects/1/punch-items/1"),
            ("GET", "/projects/1/attachments?parent_type=project&parent_id=1"),
            ("POST", "/projects/1/attachments"),
            ("GET", "/projects/1/attachments/1/download"),
            ("DELETE", "/projects/1/attachments/1"),
            ("GET", "/projects/1/dashboard?as_of=2026-01-01"),
            ("GET", "/projects/1/export/pdf"),
        ]

        for method, path in routes:
            with self.subTest(method=method, path=path):
                response = self.client.request(method, path)
                self.assertEqual(response.status_code, 401)


class AuthorizationBoundaryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.register_and_login("owner@example.com")
        self.other = self.register_and_login("other@example.com")
        self.owner_project = self.create_project(self.owner, "Owner")
        self.other_project = self.create_project(self.other, "Other")

    def test_project_scoped_reads_hide_foreign_and_missing_projects_equally(self):
        paths = [
            "tasks",
            "daily-logs",
            "inspections",
            "notes-delays",
            "companies",
            "change-orders",
            "rfis",
            "submittals",
            "punch-items",
            "dashboard?as_of=2026-01-01",
            "export/pdf",
        ]

        for suffix in paths:
            with self.subTest(path=suffix):
                foreign = self.client.get(
                    f"/projects/{self.other_project}/{suffix}",
                    headers=self.owner,
                )
                missing = self.client.get(
                    f"/projects/2147483647/{suffix}",
                    headers=self.owner,
                )
                self.assertEqual(foreign.status_code, 403)
                self.assertEqual(missing.status_code, 403)
                self.assertEqual(foreign.json(), missing.json())

        for project_id in (self.other_project, 2147483647):
            response = self.client.get(
                f"/projects/{project_id}/attachments",
                params={"parent_type": "project", "parent_id": project_id},
                headers=self.owner,
            )
            self.assertEqual(response.status_code, 403)

    def test_project_scoped_creates_reject_foreign_project(self):
        cases = [
            ("tasks", {"name": "Task", "duration": 1}),
            (
                "daily-logs",
                {"date": "2026-01-01", "company": "GC", "manpower": 1},
            ),
            (
                "inspections",
                {
                    "date": "2026-01-01",
                    "inspection_type": "Framing",
                    "status": "Pending",
                },
            ),
            (
                "notes-delays",
                {
                    "date": "2026-01-01",
                    "entry_type": "Note",
                    "description": "Note",
                },
            ),
            ("companies", {"name": "Builder"}),
            (
                "change-orders",
                {
                    "date": "2026-01-01",
                    "status": "Draft",
                    "title": "Change",
                },
            ),
            (
                "rfis",
                {
                    "subject": "Question",
                    "question": "Clarify",
                    "submitted_date": "2026-01-01",
                },
            ),
            (
                "submittals",
                {"specification_section": "03 30 00", "title": "Concrete"},
            ),
            (
                "punch-items",
                {"location": "Lobby", "description": "Repair"},
            ),
        ]

        for suffix, payload in cases:
            with self.subTest(path=suffix):
                response = self.client.post(
                    f"/projects/{self.other_project}/{suffix}",
                    json=payload,
                    headers=self.owner,
                )
                self.assertEqual(response.status_code, 403)

    def test_nested_mutations_are_scoped_to_the_owned_project(self):
        cases = [
            (
                "tasks",
                {"name": "Other task", "duration": 1},
                {"duration": 2},
            ),
            (
                "change-orders",
                {
                    "date": "2026-01-01",
                    "status": "Draft",
                    "title": "Other CO",
                },
                {"status": "Pending"},
            ),
            (
                "rfis",
                {
                    "subject": "Other RFI",
                    "question": "Question",
                    "submitted_date": "2026-01-01",
                },
                {"status": "Pending"},
            ),
            (
                "submittals",
                {"specification_section": "03 30 00", "title": "Other sub"},
                {"status": "Submitted"},
            ),
            (
                "punch-items",
                {"location": "Roof", "description": "Other punch"},
                {"status": "In Progress"},
            ),
        ]

        for suffix, create_payload, update_payload in cases:
            with self.subTest(path=suffix):
                created = self.client.post(
                    f"/projects/{self.other_project}/{suffix}",
                    json=create_payload,
                    headers=self.other,
                )
                self.assertIn(created.status_code, (200, 201))
                body = created.json()
                resource_id = (
                    body["tasks"][-1]["id"]
                    if suffix == "tasks"
                    else body["id"]
                )
                foreign_path = (
                    f"/projects/{self.owner_project}/{suffix}/{resource_id}"
                )
                missing_path = (
                    f"/projects/{self.owner_project}/{suffix}/2147483647"
                )

                foreign_update = self.client.put(
                    foreign_path,
                    json=update_payload,
                    headers=self.owner,
                )
                missing_update = self.client.put(
                    missing_path,
                    json=update_payload,
                    headers=self.owner,
                )
                self.assertEqual(foreign_update.status_code, 404)
                self.assertEqual(foreign_update.json(), missing_update.json())

                foreign_delete = self.client.delete(
                    foreign_path,
                    headers=self.owner,
                )
                missing_delete = self.client.delete(
                    missing_path,
                    headers=self.owner,
                )
                self.assertEqual(foreign_delete.status_code, 404)
                self.assertEqual(foreign_delete.json(), missing_delete.json())

                listing = self.client.get(
                    f"/projects/{self.other_project}/{suffix}",
                    headers=self.other,
                )
                items = listing.json()["tasks" if suffix == "tasks" else suffix.replace("-", "_")]
                self.assertTrue(any(item["id"] == resource_id for item in items))

    def test_foreign_task_references_do_not_mutate_the_project(self):
        foreign = self.client.post(
            f"/projects/{self.other_project}/tasks",
            json={"name": "Foreign predecessor", "duration": 1},
            headers=self.other,
        ).json()["tasks"][0]

        response = self.client.post(
            f"/projects/{self.owner_project}/tasks",
            json={
                "name": "Invalid dependency",
                "duration": 1,
                "predecessor_task_id": foreign["id"],
            },
            headers=self.owner,
        )

        self.assertEqual(response.status_code, 422)
        listing = self.client.get(
            f"/projects/{self.owner_project}/tasks",
            headers=self.owner,
        )
        self.assertEqual(listing.json()["tasks"], [])

    def test_user_owned_templates_cannot_be_applied_cross_user(self):
        self.client.post(
            f"/projects/{self.other_project}/tasks",
            json={"name": "Private template task", "duration": 1},
            headers=self.other,
        )
        template = self.client.post(
            f"/projects/{self.other_project}/templates",
            json={"name": "Private"},
            headers=self.other,
        ).json()

        foreign = self.client.post(
            f"/projects/{self.owner_project}/templates/{template['id']}/apply",
            headers=self.owner,
        )
        missing = self.client.post(
            f"/projects/{self.owner_project}/templates/2147483647/apply",
            headers=self.owner,
        )

        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.json(), missing.json())


class MutationValidationTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers)

    def test_create_schemas_reject_ownership_and_audit_fields(self):
        cases = [
            ("/projects", {"name": "Injected", "user_id": 999}),
            (
                f"/projects/{self.project_id}/tasks",
                {
                    "name": "Injected",
                    "duration": 1,
                    "project_id": 999,
                    "created_at": "2026-01-01",
                },
            ),
            (
                f"/projects/{self.project_id}/templates",
                {"name": "Injected", "user_id": 999},
            ),
            (
                f"/projects/{self.project_id}/daily-logs",
                {
                    "date": "2026-01-01",
                    "company": "GC",
                    "manpower": 1,
                    "project_id": 999,
                },
            ),
            (
                f"/projects/{self.project_id}/inspections",
                {
                    "date": "2026-01-01",
                    "inspection_type": "Framing",
                    "status": "Pending",
                    "updated_at": "2026-01-01",
                },
            ),
            (
                f"/projects/{self.project_id}/notes-delays",
                {
                    "date": "2026-01-01",
                    "entry_type": "Note",
                    "description": "Injected",
                    "project_id": 999,
                },
            ),
            (
                f"/projects/{self.project_id}/companies",
                {"name": "Injected", "project_id": 999},
            ),
            (
                f"/projects/{self.project_id}/change-orders",
                {
                    "date": "2026-01-01",
                    "status": "Draft",
                    "title": "Injected",
                    "project_id": 999,
                },
            ),
            (
                f"/projects/{self.project_id}/rfis",
                {
                    "subject": "Injected",
                    "question": "Question",
                    "submitted_date": "2026-01-01",
                    "project_id": 999,
                },
            ),
            (
                f"/projects/{self.project_id}/submittals",
                {
                    "specification_section": "03 30 00",
                    "title": "Injected",
                    "created_at": "2026-01-01",
                },
            ),
            (
                f"/projects/{self.project_id}/punch-items",
                {
                    "location": "Lobby",
                    "description": "Injected",
                    "project_id": 999,
                },
            ),
        ]

        for path, payload in cases:
            with self.subTest(path=path):
                response = self.client.post(
                    path,
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_registration_rejects_owner_assignment(self):
        response = self.client.post(
            "/auth/register",
            json={
                "email": "injected@example.com",
                "password": "Secret123!",
                "user_id": 1,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_task_update_rejects_response_only_and_unknown_fields(self):
        task = self.client.post(
            f"/projects/{self.project_id}/tasks",
            json={"name": "Original", "duration": 1},
            headers=self.headers,
        ).json()["tasks"][0]

        for payload in (
            {"project_id": 999},
            {"created_at": "2026-01-01"},
            {"start_date": "2026-01-01"},
            {"order_index": 999},
            {"unknown": {"nested": True}},
        ):
            with self.subTest(payload=payload):
                response = self.client.put(
                    f"/projects/{self.project_id}/tasks/{task['id']}",
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

        unchanged = self.client.get(
            f"/projects/{self.project_id}/tasks",
            headers=self.headers,
        ).json()["tasks"][0]
        self.assertEqual(unchanged["name"], "Original")
        self.assertIsNone(unchanged["order_index"])

    def test_workflow_updates_reject_empty_or_ownership_payloads(self):
        created = self.client.post(
            f"/projects/{self.project_id}/rfis",
            json={
                "subject": "Original",
                "question": "Question",
                "submitted_date": "2026-01-01",
            },
            headers=self.headers,
        ).json()

        for payload in ({}, {"project_id": 999}, {"created_at": "2026-01-01"}):
            with self.subTest(payload=payload):
                response = self.client.put(
                    f"/projects/{self.project_id}/rfis/{created['id']}",
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_string_enum_date_and_numeric_bounds_are_enforced(self):
        cases = [
            (
                "/projects",
                {"name": "   "},
            ),
            (
                f"/projects/{self.project_id}/tasks",
                {"name": "Too long", "duration": 36501},
            ),
            (
                f"/projects/{self.project_id}/daily-logs",
                {
                    "date": "2026-01-01",
                    "company": "GC",
                    "manpower": -1,
                },
            ),
            (
                f"/projects/{self.project_id}/daily-logs",
                {
                    "date": "2026-01-01",
                    "company": "GC",
                    "manpower": 1,
                    "notes": "x" * 10001,
                },
            ),
            (
                f"/projects/{self.project_id}/inspections",
                {
                    "date": "2026-01-01",
                    "inspection_type": "Framing",
                    "status": "Unknown",
                },
            ),
            (
                f"/projects/{self.project_id}/rfis",
                {
                    "subject": "Dates",
                    "question": "Question",
                    "submitted_date": "2026-03-01",
                    "due_date": "2026-02-28",
                },
            ),
            (
                f"/projects/{self.project_id}/submittals",
                {
                    "specification_section": "03 30 00",
                    "title": "Dates",
                    "submitted_date": "2026-03-01",
                    "reviewed_date": "2026-02-28",
                },
            ),
            (
                f"/projects/{self.project_id}/punch-items",
                {
                    "location": "Lobby",
                    "description": "Dates",
                    "due_date": "2026-03-01",
                    "completed_date": "2026-02-28",
                },
            ),
            (
                f"/projects/{self.project_id}/change-orders",
                {
                    "date": "2026-01-01",
                    "status": "Draft",
                    "title": "Impact",
                    "schedule_impact_days": 36501,
                },
            ),
        ]

        for path, payload in cases:
            with self.subTest(path=path):
                response = self.client.post(
                    path,
                    json=payload,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_money_rejects_nonfinite_and_excess_precision(self):
        path = f"/projects/{self.project_id}/change-orders"
        payloads = [
            '{"date":"2026-01-01","status":"Draft","title":"NaN",'
            '"proposed_amount":NaN}',
            '{"date":"2026-01-01","status":"Draft","title":"Infinity",'
            '"proposed_amount":Infinity}',
            '{"date":"2026-01-01","status":"Draft","title":"Precision",'
            '"proposed_amount":"1.001"}',
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    path,
                    content=payload,
                    headers={
                        **self.headers,
                        "Content-Type": "application/json",
                    },
                )
                self.assertEqual(response.status_code, 422)

    def test_iso_dates_accept_leap_day_and_reject_invalid_dates(self):
        valid = self.client.post(
            f"/projects/{self.project_id}/daily-logs",
            json={"date": "2024-02-29", "company": "GC", "manpower": 1},
            headers=self.headers,
        )
        invalid = self.client.post(
            f"/projects/{self.project_id}/daily-logs",
            json={"date": "2026-02-29", "company": "GC", "manpower": 1},
            headers=self.headers,
        )
        timestamp = self.client.post(
            f"/projects/{self.project_id}/daily-logs",
            json={
                "date": "2026-01-01T00:00:00Z",
                "company": "GC",
                "manpower": 1,
            },
            headers=self.headers,
        )

        self.assertEqual(valid.status_code, 201)
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(timestamp.status_code, 422)


class IdentifierPaginationAndTransactionTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.headers = self.register_and_login()
        self.project_id = self.create_project(self.headers)

    def test_path_and_query_identifiers_require_positive_bounded_integers(self):
        paths = [
            ("GET", "/projects/0/tasks"),
            ("GET", "/projects/-1/tasks"),
            ("GET", "/projects/2147483648/tasks"),
            ("GET", "/projects/not-an-id/tasks"),
            ("GET", "/projects/1.5/tasks"),
            ("DELETE", f"/projects/{self.project_id}/tasks/0"),
            ("DELETE", f"/projects/{self.project_id}/rfis/-1"),
        ]
        for method, path in paths:
            with self.subTest(method=method, path=path):
                self.assertEqual(
                    self.client.request(
                        method,
                        path,
                        headers=self.headers,
                    ).status_code,
                    422,
                )

        for parent_id in ("0", "-1", "2147483648", "abc", "1.5"):
            with self.subTest(parent_id=parent_id):
                response = self.client.get(
                    f"/projects/{self.project_id}/attachments",
                    params={"parent_type": "project", "parent_id": parent_id},
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_pagination_is_bounded_and_stably_ordered(self):
        for day in (1, 2, 3):
            response = self.client.post(
                f"/projects/{self.project_id}/daily-logs",
                json={
                    "date": f"2026-01-0{day}",
                    "company": "GC",
                    "manpower": day,
                },
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 201)

        page = self.client.get(
            f"/projects/{self.project_id}/daily-logs",
            params={"limit": 2, "offset": 1},
            headers=self.headers,
        )
        self.assertEqual(
            [item["date"] for item in page.json()["daily_logs"]],
            ["2026-01-02", "2026-01-01"],
        )

        invalid_queries = [
            {"limit": 0},
            {"limit": 501},
            {"offset": -1},
            {"offset": 2147483648},
        ]
        for params in invalid_queries:
            with self.subTest(params=params):
                response = self.client.get(
                    f"/projects/{self.project_id}/daily-logs",
                    params=params,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    def test_reorder_rejects_duplicates_subsets_and_excessive_lists(self):
        task_ids = []
        for name in ("One", "Two"):
            response = self.client.post(
                f"/projects/{self.project_id}/tasks",
                json={"name": name, "duration": 1},
                headers=self.headers,
            )
            task_ids = [task["id"] for task in response.json()["tasks"]]

        payloads = [
            [task_ids[0], task_ids[0]],
            [task_ids[0]],
            list(range(1, 2002)),
            [],
        ]
        for task_ids_payload in payloads:
            with self.subTest(size=len(task_ids_payload)):
                response = self.client.put(
                    f"/projects/{self.project_id}/tasks/reorder",
                    json={"task_ids": task_ids_payload},
                    headers=self.headers,
                )
                self.assertIn(response.status_code, (404, 422))

        listing = self.client.get(
            f"/projects/{self.project_id}/tasks",
            headers=self.headers,
        )
        self.assertEqual(
            [task["name"] for task in listing.json()["tasks"]],
            ["One", "Two"],
        )

    def test_reorder_rolls_back_when_schedule_calculation_fails(self):
        task_ids = []
        for name in ("One", "Two"):
            response = self.client.post(
                f"/projects/{self.project_id}/tasks",
                json={"name": name, "duration": 1},
                headers=self.headers,
            )
            task_ids = [task["id"] for task in response.json()["tasks"]]

        with patch(
            "app.api.routes_task.recalculate_schedule",
            side_effect=RuntimeError("calculation failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.put(
                    f"/projects/{self.project_id}/tasks/reorder",
                    json={"task_ids": list(reversed(task_ids))},
                    headers=self.headers,
                )

        listing = self.client.get(
            f"/projects/{self.project_id}/tasks",
            headers=self.headers,
        )
        self.assertEqual(
            [task["id"] for task in listing.json()["tasks"]],
            task_ids,
        )

    def test_task_create_rolls_back_when_schedule_calculation_fails(self):
        with patch(
            "app.api.routes_task.recalculate_schedule",
            side_effect=RuntimeError("calculation failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    f"/projects/{self.project_id}/tasks",
                    json={"name": "Not persisted", "duration": 1},
                    headers=self.headers,
                )

        with self.TestingSession() as db:
            self.assertEqual(
                db.query(Task)
                .filter(Task.project_id == self.project_id)
                .count(),
                0,
            )

    def test_template_application_rolls_back_on_schedule_failure(self):
        self.client.post(
            f"/projects/{self.project_id}/tasks",
            json={"name": "Template task", "duration": 1},
            headers=self.headers,
        )
        template = self.client.post(
            f"/projects/{self.project_id}/templates",
            json={"name": "Atomic template"},
            headers=self.headers,
        ).json()
        target_project = self.create_project(self.headers, "Target")

        with patch(
            "app.api.routes_template.recalculate_schedule",
            side_effect=RuntimeError("calculation failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    f"/projects/{target_project}/templates/{template['id']}/apply",
                    headers=self.headers,
                )

        listing = self.client.get(
            f"/projects/{target_project}/tasks",
            headers=self.headers,
        )
        self.assertEqual(listing.json()["tasks"], [])

    def test_pdf_export_rejects_excessive_task_count(self):
        for name in ("One", "Two"):
            response = self.client.post(
                f"/projects/{self.project_id}/tasks",
                json={"name": name, "duration": 1},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 201)

        with patch("app.api.routes_export.MAX_EXPORT_TASKS", 1):
            response = self.client.get(
                f"/projects/{self.project_id}/export/pdf",
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            response.json(),
            {"detail": "Project schedule is too large to export"},
        )
