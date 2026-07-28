import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import event

from app.models.attachment import Attachment
from app.models.change_order import ChangeOrder
from app.models.daily_log import DailyLog
from app.models.punch_item import PunchItem
from app.models.rfi import RFI
from app.models.submittal import Submittal
from app.models.task import Task
from app.models.user import User
from tests.test_api import ApiTestCase


AS_OF = "2026-07-27"


class DashboardApiTests(ApiTestCase):
    def dashboard_url(self, project_id, as_of=AS_OF):
        return f"/projects/{project_id}/dashboard?as_of={as_of}"

    def user_id(self, email="super@example.com"):
        with self.TestingSession() as db:
            return db.query(User.id).filter(User.email == email).scalar()

    def add_attachment(
        self,
        db,
        *,
        project_id,
        uploaded_by,
        suffix,
        created_at,
        parent_type="project",
        parent_id=None,
    ):
        db.add(
            Attachment(
                project_id=project_id,
                parent_type=parent_type,
                parent_id=parent_id or project_id,
                original_filename=f"document-{suffix}.pdf",
                storage_key=f"storage-{project_id}-{suffix}",
                storage_provider="local",
                mime_type="application/pdf",
                size_bytes=100 + suffix,
                uploaded_by=uploaded_by,
                sha256=f"{suffix:064x}",
                created_at=created_at,
            )
        )

    def test_authentication_ownership_and_query_validation(self):
        owner = self.register_and_login("dashboard-owner@example.com")
        intruder = self.register_and_login("dashboard-intruder@example.com")
        project_id = self.create_project(owner, "Apex Clubhouse")

        self.assertEqual(
            self.client.get(self.dashboard_url(project_id)).status_code,
            401,
        )
        self.assertEqual(
            self.client.get(
                self.dashboard_url(project_id),
                headers=owner,
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                self.dashboard_url(project_id),
                headers=intruder,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                self.dashboard_url(9999),
                headers=owner,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                f"/projects/{project_id}/dashboard",
                headers=owner,
            ).status_code,
            422,
        )

        for invalid_date in (
            "2026-02-30",
            "07-27-2026",
            "2026-07-27T00:00:00",
        ):
            with self.subTest(as_of=invalid_date):
                response = self.client.get(
                    self.dashboard_url(project_id, invalid_date),
                    headers=owner,
                )
                self.assertEqual(response.status_code, 422)

        leap_day = self.client.get(
            self.dashboard_url(project_id, "2028-02-29"),
            headers=owner,
        )
        self.assertEqual(leap_day.status_code, 200)
        self.assertEqual(leap_day.json()["as_of"], "2028-02-29")

    def test_empty_project_returns_complete_typed_response(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers, "Empty Project")

        response = self.client.get(
            self.dashboard_url(project_id),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            set(payload),
            {
                "as_of",
                "generated_at",
                "project",
                "schedule",
                "rfis",
                "submittals",
                "punch_items",
                "change_orders",
                "daily_logs",
                "documents",
                "attention_items",
                "upcoming_tasks",
                "recent_updates",
            },
        )
        self.assertEqual(
            payload["project"],
            {"id": project_id, "name": "Empty Project"},
        )
        self.assertEqual(
            payload["schedule"],
            {
                "task_count": 0,
                "planned_start": None,
                "planned_finish": None,
                "past_planned_finish_count": 0,
                "upcoming_start_count": 0,
            },
        )
        self.assertEqual(
            payload["change_orders"]["active_value"],
            "0.00",
        )
        self.assertEqual(
            payload["change_orders"]["approved_value"],
            "0.00",
        )
        self.assertEqual(payload["attention_items"], [])
        self.assertEqual(payload["upcoming_tasks"], [])
        self.assertEqual(payload["recent_updates"], [])
        self.assertEqual(payload["documents"]["recent"], [])

    def test_workflow_groups_boundaries_and_decimal_precision(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)
        now = datetime(2026, 7, 27, 12, tzinfo=timezone.utc)

        with self.TestingSession() as db:
            db.add_all(
                [
                    RFI(
                        project_id=project_id,
                        number=f"RFI-{index:03d}",
                        subject=f"RFI {index}",
                        question="Question",
                        submitted_date="2026-07-01",
                        due_date=due_date,
                        status=status,
                        created_at=now,
                        updated_at=now,
                    )
                    for index, (status, due_date) in enumerate(
                        (
                            ("Open", "2026-07-26"),
                            ("Pending", "2026-07-27"),
                            ("Open", "2026-08-03"),
                            ("Open", "2026-08-04"),
                            ("Closed", "2026-07-20"),
                            ("Legacy", "2026-07-20"),
                        ),
                        start=1,
                    )
                ]
            )
            db.add_all(
                [
                    Submittal(
                        project_id=project_id,
                        number=f"SUB-{index:03d}",
                        specification_section="08 41 13",
                        title=f"Submittal {index}",
                        required_by_date=due_date,
                        status=status,
                        created_at=now,
                        updated_at=now,
                    )
                    for index, (status, due_date) in enumerate(
                        (
                            ("Draft", "2026-07-26"),
                            ("Submitted", "2026-07-27"),
                            ("Under Review", "2026-08-03"),
                            ("Draft", "2026-08-04"),
                            ("Approved", "2026-07-20"),
                            ("Legacy", "2026-07-20"),
                        ),
                        start=1,
                    )
                ]
            )
            db.add_all(
                [
                    PunchItem(
                        project_id=project_id,
                        number=f"PUNCH-{index:03d}",
                        location="Level 1",
                        description=f"Punch {index}",
                        priority="Medium",
                        status=status,
                        due_date=due_date,
                        completed_date=completed_date,
                        created_at=now,
                        updated_at=now,
                    )
                    for index, (
                        status,
                        due_date,
                        completed_date,
                    ) in enumerate(
                        (
                            ("Open", "2026-07-26", None),
                            ("In Progress", "2026-07-27", None),
                            ("Completed", None, "2026-07-21"),
                            ("Verified", None, "2026-07-27"),
                            ("Completed", None, "2026-07-20"),
                            ("Verified", None, None),
                            ("Legacy", None, "2026-07-27"),
                        ),
                        start=1,
                    )
                ]
            )
            change_order_values = (
                ("Draft", Decimal("0.10"), None, None),
                ("Under Review", Decimal("0.20"), None, None),
                ("Approved", None, Decimal("100.10"), None),
                ("Executed", None, Decimal("0.20"), None),
                ("Rejected", Decimal("50.00"), Decimal("50.00"), None),
                ("Void", Decimal("60.00"), Decimal("60.00"), None),
                ("Legacy", Decimal("70.00"), Decimal("70.00"), "$999"),
            )
            db.add_all(
                [
                    ChangeOrder(
                        project_id=project_id,
                        date="2026-07-01",
                        co_number=f"CO-{index:03d}",
                        status=status,
                        description=f"Change {index}",
                        proposed_amount=proposed,
                        approved_amount=approved,
                        amount=legacy_amount,
                        created_at=now,
                        updated_at=now,
                    )
                    for index, (
                        status,
                        proposed,
                        approved,
                        legacy_amount,
                    ) in enumerate(change_order_values, start=1)
                ]
            )
            db.commit()

        payload = self.client.get(
            self.dashboard_url(project_id),
            headers=headers,
        ).json()

        self.assertEqual(
            payload["rfis"],
            {"total": 6, "open": 4, "overdue": 1, "due_soon": 2},
        )
        self.assertEqual(
            payload["submittals"],
            {"total": 6, "pending": 4, "overdue": 1, "due_soon": 2},
        )
        self.assertEqual(
            payload["punch_items"],
            {
                "total": 7,
                "open": 2,
                "overdue": 1,
                "completed_last_7_days": 2,
            },
        )
        self.assertEqual(
            payload["change_orders"],
            {
                "total": 7,
                "active": 2,
                "approved": 2,
                "rejected": 2,
                "unknown_status": 1,
                "active_value": "0.30",
                "approved_value": "100.30",
            },
        )

    def test_schedule_and_daily_log_date_definitions(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)

        with self.TestingSession() as db:
            db.add_all(
                [
                    Task(
                        project_id=project_id,
                        name=f"Task {index}",
                        duration=1,
                        start_date=start,
                        end_date=end,
                        order_index=index,
                    )
                    for index, (start, end) in enumerate(
                        (
                            ("2026-07-01", "2026-07-26"),
                            ("2026-07-27", "2026-07-27"),
                            ("2026-08-03", "2026-08-05"),
                            ("2026-08-04", "2026-08-06"),
                            (None, None),
                        ),
                        start=1,
                    )
                ]
            )
            db.add_all(
                [
                    DailyLog(
                        project_id=project_id,
                        date=log_date,
                        company="Build Co",
                        manpower=manpower,
                    )
                    for log_date, manpower in (
                        ("2026-07-20", 20),
                        ("2026-07-21", 3),
                        ("2026-07-27", 4),
                        ("2026-07-27", 5),
                    )
                ]
            )
            db.commit()

        payload = self.client.get(
            self.dashboard_url(project_id),
            headers=headers,
        ).json()
        self.assertEqual(
            payload["schedule"],
            {
                "task_count": 5,
                "planned_start": "2026-07-01",
                "planned_finish": "2026-08-06",
                "past_planned_finish_count": 1,
                "upcoming_start_count": 2,
            },
        )
        self.assertEqual(
            payload["daily_logs"],
            {
                "total": 4,
                "latest_log_date": "2026-07-27",
                "today_count": 2,
                "today_manpower": 9,
                "last_7_days_count": 3,
            },
        )

    def test_documents_are_bounded_ordered_scoped_and_safe(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)
        other_project_id = self.create_project(headers, "Other")
        uploaded_by = self.user_id()
        boundary = datetime(2026, 7, 21, tzinfo=timezone.utc)

        with self.TestingSession() as db:
            self.add_attachment(
                db,
                project_id=project_id,
                uploaded_by=uploaded_by,
                suffix=90,
                created_at=boundary - timedelta(microseconds=1),
            )
            for suffix in range(1, 11):
                self.add_attachment(
                    db,
                    project_id=project_id,
                    uploaded_by=uploaded_by,
                    suffix=suffix,
                    created_at=boundary + timedelta(days=suffix % 7),
                )
            self.add_attachment(
                db,
                project_id=other_project_id,
                uploaded_by=uploaded_by,
                suffix=99,
                created_at=boundary + timedelta(days=6),
            )
            self.add_attachment(
                db,
                project_id=project_id,
                uploaded_by=uploaded_by,
                suffix=91,
                created_at=boundary + timedelta(days=7),
            )
            db.commit()

        response = self.client.get(
            self.dashboard_url(project_id),
            headers=headers,
        )
        documents = response.json()["documents"]

        self.assertEqual(documents["total"], 12)
        self.assertEqual(documents["uploaded_last_7_days"], 10)
        self.assertEqual(len(documents["recent"]), 8)
        ordered = [
            (item["created_at"], item["id"])
            for item in documents["recent"]
        ]
        self.assertEqual(ordered, sorted(ordered, reverse=True))
        self.assertNotIn("storage_key", response.text)
        self.assertNotIn("storage_provider", response.text)
        self.assertNotIn("sha256", response.text)
        self.assertNotIn("cleanup", response.text)

    def test_attention_items_are_actionable_bounded_and_deterministic(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)
        now = datetime(2026, 7, 27, tzinfo=timezone.utc)

        with self.TestingSession() as db:
            db.add(
                RFI(
                    project_id=project_id,
                    number="RFI-001",
                    subject="Clarify flashing",
                    question="Question",
                    submitted_date="2026-07-01",
                    due_date="2026-07-24",
                    status="Open",
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                Submittal(
                    project_id=project_id,
                    number="SUB-001",
                    specification_section="08 41 13",
                    title="Storefront data",
                    required_by_date="2026-07-23",
                    status="Submitted",
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                PunchItem(
                    project_id=project_id,
                    number="PUNCH-001",
                    location="Lobby",
                    description="Repair finish",
                    priority="High",
                    status="In Progress",
                    due_date="2026-07-22",
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                Task(
                    project_id=project_id,
                    name="Install storefront",
                    duration=5,
                    start_date="2026-07-10",
                    end_date="2026-07-20",
                    order_index=1,
                )
            )
            db.commit()

        items = self.client.get(
            self.dashboard_url(project_id),
            headers=headers,
        ).json()["attention_items"]

        self.assertEqual(
            [item["resource_type"] for item in items],
            ["punch_item", "submittal", "rfi", "task"],
        )
        self.assertEqual(
            [item["target_page"] for item in items],
            ["punch-items", "submittals", "rfis", "schedule"],
        )
        self.assertEqual(items[-1]["reason"], "Past planned finish")
        self.assertNotIn("overdue", items[-1]["reason"].lower())

        with self.TestingSession() as db:
            db.add_all(
                [
                    RFI(
                        project_id=project_id,
                        number=f"RFI-{index:03d}",
                        subject=f"Extra {index}",
                        question="Question",
                        submitted_date="2026-07-01",
                        due_date="2026-07-01",
                        status="Open",
                        created_at=now,
                        updated_at=now,
                    )
                    for index in range(2, 14)
                ]
            )
            db.commit()

        limited = self.client.get(
            self.dashboard_url(project_id),
            headers=headers,
        ).json()["attention_items"]
        self.assertEqual(len(limited), 10)

    def test_upcoming_tasks_are_bounded_ordered_and_field_limited(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)

        with self.TestingSession() as db:
            db.add_all(
                [
                    Task(
                        project_id=project_id,
                        name=f"Upcoming {index}",
                        duration=index,
                        start_date=(
                            "2026-07-27"
                            if index <= 3
                            else "2026-08-03"
                        ),
                        end_date="2026-08-05",
                        order_index=10 - index,
                    )
                    for index in range(1, 11)
                ]
            )
            db.add(
                Task(
                    project_id=project_id,
                    name="Too late",
                    duration=1,
                    start_date="2026-08-04",
                    end_date="2026-08-04",
                    order_index=0,
                )
            )
            db.commit()

        tasks = self.client.get(
            self.dashboard_url(project_id),
            headers=headers,
        ).json()["upcoming_tasks"]

        self.assertEqual(len(tasks), 8)
        self.assertEqual(
            [task["name"] for task in tasks[:3]],
            ["Upcoming 3", "Upcoming 2", "Upcoming 1"],
        )
        self.assertEqual(
            set(tasks[0]),
            {"id", "name", "start_date", "end_date", "duration"},
        )
        self.assertTrue(
            all(task["start_date"] <= "2026-08-03" for task in tasks)
        )

    def test_recent_updates_are_derived_bounded_and_project_scoped(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)
        other_project_id = self.create_project(headers, "Other")
        uploaded_by = self.user_id()
        timestamp = datetime(2026, 7, 27, 15, tzinfo=timezone.utc)

        with self.TestingSession() as db:
            for index in range(1, 4):
                db.add(
                    RFI(
                        project_id=project_id,
                        number=f"RFI-{index:03d}",
                        subject=f"RFI update {index}",
                        question="Question",
                        submitted_date="2026-07-01",
                        status="Open",
                        created_at=timestamp,
                        updated_at=timestamp + timedelta(minutes=index),
                    )
                )
            db.add(
                Submittal(
                    project_id=project_id,
                    number="SUB-001",
                    specification_section="08 41 13",
                    title="Submittal update",
                    status="Draft",
                    created_at=timestamp,
                    updated_at=timestamp + timedelta(minutes=4),
                )
            )
            db.add(
                PunchItem(
                    project_id=project_id,
                    number="PUNCH-001",
                    location="Lobby",
                    description="Punch update",
                    priority="High",
                    status="Open",
                    created_at=timestamp,
                    updated_at=timestamp + timedelta(minutes=5),
                )
            )
            db.add(
                ChangeOrder(
                    project_id=project_id,
                    date=AS_OF,
                    co_number="CO-001",
                    status="Draft",
                    title="Change update",
                    created_at=timestamp,
                    updated_at=timestamp + timedelta(minutes=6),
                )
            )
            for suffix in range(1, 5):
                self.add_attachment(
                    db,
                    project_id=project_id,
                    uploaded_by=uploaded_by,
                    suffix=suffix,
                    created_at=timestamp + timedelta(minutes=6 + suffix),
                )
            db.add(
                RFI(
                    project_id=other_project_id,
                    number="RFI-999",
                    subject="Foreign update",
                    question="Question",
                    submitted_date="2026-07-01",
                    status="Open",
                    created_at=timestamp,
                    updated_at=timestamp + timedelta(days=1),
                )
            )
            db.commit()

        response = self.client.get(
            self.dashboard_url(project_id),
            headers=headers,
        )
        updates = response.json()["recent_updates"]

        self.assertEqual(len(updates), 8)
        self.assertNotIn("Foreign update", response.text)
        self.assertTrue(
            all("actor" not in update for update in updates)
        )
        ordering = [
            (
                update["updated_at"],
                update["resource_type"],
                update["record_id"],
            )
            for update in updates
        ]
        expected = sorted(
            ordering,
            key=lambda item: (item[0],),
            reverse=True,
        )
        self.assertEqual(
            [item[0] for item in ordering],
            [item[0] for item in expected],
        )

    def test_query_count_is_constant_and_response_is_bounded(self):
        headers = self.register_and_login()
        empty_project_id = self.create_project(headers, "Empty")
        mixed_project_id = self.create_project(headers, "Mixed")
        large_project_id = self.create_project(headers, "Large")
        uploaded_by = self.user_id()
        now = datetime(2026, 7, 27, 12, tzinfo=timezone.utc)

        with self.TestingSession() as db:
            db.add(
                RFI(
                    project_id=mixed_project_id,
                    number="RFI-001",
                    subject="Mixed RFI",
                    question="Question",
                    submitted_date="2026-07-01",
                    due_date="2026-07-20",
                    status="Open",
                    created_at=now,
                    updated_at=now,
                )
            )
            for index in range(1, 101):
                db.add(
                    RFI(
                        project_id=large_project_id,
                        number=f"RFI-{index:03d}",
                        subject=f"Large RFI {index}",
                        question="Question",
                        submitted_date="2026-07-01",
                        due_date="2026-07-20",
                        status="Open",
                        created_at=now + timedelta(seconds=index),
                        updated_at=now + timedelta(seconds=index),
                    )
                )
                db.add(
                    Task(
                        project_id=large_project_id,
                        name=f"Large task {index}",
                        duration=1,
                        start_date="2026-07-27",
                        end_date="2026-07-28",
                        order_index=index,
                    )
                )
                self.add_attachment(
                    db,
                    project_id=large_project_id,
                    uploaded_by=uploaded_by,
                    suffix=index,
                    created_at=now + timedelta(seconds=index),
                )
            db.commit()

        def request_with_query_count(project_id):
            statements = []

            def count_statement(
                connection,
                cursor,
                statement,
                parameters,
                context,
                executemany,
            ):
                statements.append(statement)

            event.listen(
                self.engine,
                "before_cursor_execute",
                count_statement,
            )
            try:
                with patch(
                    "app.storage.factory.build_attachment_storage"
                ) as build_storage:
                    response = self.client.get(
                        self.dashboard_url(project_id),
                        headers=headers,
                    )
                    build_storage.assert_not_called()
            finally:
                event.remove(
                    self.engine,
                    "before_cursor_execute",
                    count_statement,
                )
            self.assertEqual(response.status_code, 200)
            return response, len(statements)

        empty_response, empty_count = request_with_query_count(
            empty_project_id
        )
        mixed_response, mixed_count = request_with_query_count(
            mixed_project_id
        )
        large_response, large_count = request_with_query_count(
            large_project_id
        )

        self.assertEqual(
            (empty_count, mixed_count, large_count),
            (12, 12, 12),
        )
        self.assertEqual(
            len(large_response.json()["attention_items"]),
            10,
        )
        self.assertEqual(
            len(large_response.json()["upcoming_tasks"]),
            8,
        )
        self.assertEqual(
            len(large_response.json()["documents"]["recent"]),
            8,
        )
        self.assertEqual(
            len(large_response.json()["recent_updates"]),
            8,
        )
        self.assertLess(len(large_response.content), 75 * 1024)
        self.assertLess(len(mixed_response.content), 75 * 1024)
        self.assertLess(len(empty_response.content), 75 * 1024)

        serialized = json.loads(large_response.content)
        self.assertNotIn("question", serialized["recent_updates"][0])
