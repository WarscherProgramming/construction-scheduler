import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.database import Base
from app.main import app


class ApiTestCase(unittest.TestCase):
    """End-to-end API tests over the real app with an isolated sqlite DB."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        TestingSession = sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False
        )

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def register_and_login(self, email="super@example.com"):
        self.client.post(
            "/auth/register",
            json={"email": email, "password": "Secret123!"},
        )
        response = self.client.post(
            "/auth/login",
            data={"username": email, "password": "Secret123!"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def create_project(self, headers, name="Riverside"):
        response = self.client.post(
            "/projects", json={"name": name}, headers=headers
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]


class AuthFlowTests(ApiTestCase):
    def test_register_login_and_reject_bad_credentials(self):
        created = self.client.post(
            "/auth/register",
            json={"email": "pm@example.com", "password": "Secret123!"},
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["email"], "pm@example.com")

        duplicate = self.client.post(
            "/auth/register",
            json={"email": "pm@example.com", "password": "Secret123!"},
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.json()["detail"], "Email already registered")

        login = self.client.post(
            "/auth/login",
            data={"username": "pm@example.com", "password": "Secret123!"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()["token_type"], "bearer")

        wrong = self.client.post(
            "/auth/login",
            data={"username": "pm@example.com", "password": "nope"},
        )
        self.assertEqual(wrong.status_code, 401)

    def test_protected_routes_require_a_token(self):
        self.assertEqual(self.client.get("/projects").status_code, 401)
        self.assertEqual(
            self.client.get("/projects/1/tasks").status_code, 401
        )


class ProjectApiTests(ApiTestCase):
    def test_create_and_list_projects(self):
        headers = self.register_and_login()

        project_id = self.create_project(headers, name="North Ridge")

        listing = self.client.get("/projects", headers=headers)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            listing.json(),
            {"projects": [{"id": project_id, "name": "North Ridge"}]},
        )

    def test_project_ownership_is_enforced(self):
        owner = self.register_and_login("owner@example.com")
        intruder = self.register_and_login("intruder@example.com")
        project_id = self.create_project(owner)

        forbidden = self.client.get(
            f"/projects/{project_id}/tasks", headers=intruder
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(
            forbidden.json()["detail"],
            "You do not have access to this project",
        )

        # Nonexistent projects behave identically to foreign ones.
        missing = self.client.get("/projects/9999/tasks", headers=owner)
        self.assertEqual(missing.status_code, 403)


class TaskApiTests(ApiTestCase):
    def test_task_lifecycle_schedules_and_flags_critical_path(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)

        created = self.client.post(
            f"/projects/{project_id}/tasks",
            json={"name": "Excavate", "duration": 3},
            headers=headers,
        )
        self.assertEqual(created.status_code, 201)
        first = created.json()["tasks"][0]
        self.assertIsNotNone(first["start_date"])
        self.assertIsNotNone(first["end_date"])
        self.assertTrue(first["is_critical"])
        self.assertEqual(first["total_float"], 0)

        chained = self.client.post(
            f"/projects/{project_id}/tasks",
            json={
                "name": "Footings",
                "duration": 2,
                "predecessor": str(first["id"]),
            },
            headers=headers,
        )
        self.assertEqual(chained.status_code, 201)
        tasks = chained.json()["tasks"]
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[1]["predecessor_task_id"], first["id"])
        self.assertGreater(tasks[1]["start_date"], tasks[0]["end_date"])
        self.assertTrue(all(task["is_critical"] for task in tasks))

        updated = self.client.put(
            f"/projects/{project_id}/tasks/{first['id']}",
            json={"duration": 5},
            headers=headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["tasks"][0]["duration"], 5)

        deleted = self.client.delete(
            f"/projects/{project_id}/tasks/{tasks[1]['id']}",
            headers=headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(len(deleted.json()["tasks"]), 1)

    def test_reorder_persists_new_task_order(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)

        for name in ("First", "Second"):
            self.client.post(
                f"/projects/{project_id}/tasks",
                json={"name": name, "duration": 1},
                headers=headers,
            )

        tasks = self.client.get(
            f"/projects/{project_id}/tasks", headers=headers
        ).json()["tasks"]
        reversed_ids = [tasks[1]["id"], tasks[0]["id"]]

        reordered = self.client.put(
            f"/projects/{project_id}/tasks/reorder",
            json={"task_ids": reversed_ids},
            headers=headers,
        )
        self.assertEqual(reordered.status_code, 200)
        self.assertEqual(reordered.json(), {"message": "Tasks reordered"})

        after = self.client.get(
            f"/projects/{project_id}/tasks", headers=headers
        ).json()["tasks"]
        self.assertEqual([task["id"] for task in after], reversed_ids)

    def test_invalid_predecessor_reference_is_rejected(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)

        response = self.client.post(
            f"/projects/{project_id}/tasks",
            json={"name": "Orphan", "duration": 1, "predecessor": "999"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("must reference a task", response.json()["detail"])


class RecordApiTests(ApiTestCase):
    def test_daily_log_create_and_list(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)

        created = self.client.post(
            f"/projects/{project_id}/daily-logs",
            json={
                "date": "2026-06-30",
                "company": "Desert Concrete",
                "manpower": 8,
                "notes": "Poured footings",
            },
            headers=headers,
        )
        self.assertEqual(created.status_code, 201)

        listing = self.client.get(
            f"/projects/{project_id}/daily-logs", headers=headers
        )
        self.assertEqual(listing.status_code, 200)
        logs = listing.json()["daily_logs"]
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["company"], "Desert Concrete")

    def test_inspections_and_notes_delays_round_trip(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)

        inspection = self.client.post(
            f"/projects/{project_id}/inspections",
            json={
                "date": "2026-06-30",
                "inspection_type": "Framing",
                "status": "Pending",
            },
            headers=headers,
        )
        self.assertEqual(inspection.status_code, 201)
        self.assertEqual(
            len(
                self.client.get(
                    f"/projects/{project_id}/inspections", headers=headers
                ).json()["inspections"]
            ),
            1,
        )

        note = self.client.post(
            f"/projects/{project_id}/notes-delays",
            json={
                "date": "2026-06-30",
                "entry_type": "Delay",
                "company": "Desert Concrete",
                "description": "Rain",
                "impact": "1 day",
            },
            headers=headers,
        )
        self.assertEqual(note.status_code, 201)
        self.assertEqual(
            len(
                self.client.get(
                    f"/projects/{project_id}/notes-delays", headers=headers
                ).json()["notes_delays"]
            ),
            1,
        )

    def test_change_order_create_and_delete(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)

        created = self.client.post(
            f"/projects/{project_id}/change-orders",
            json={
                "date": "2026-06-30",
                "co_number": "CO-101",
                "company": "Desert Concrete",
                "status": "Pending",
                "description": "Added curb",
                "amount": "4500",
                "responsible_party": "Owner",
            },
            headers=headers,
        )
        self.assertEqual(created.status_code, 201)
        change_order_id = created.json()["id"]

        deleted = self.client.delete(
            f"/projects/{project_id}/change-orders/{change_order_id}",
            headers=headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json(), {"message": "Change order deleted"})

        missing = self.client.delete(
            f"/projects/{project_id}/change-orders/{change_order_id}",
            headers=headers,
        )
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
