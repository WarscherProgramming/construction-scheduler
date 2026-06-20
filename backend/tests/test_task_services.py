from datetime import date
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes_task import (
    validate_dependency_assignment,
    validate_parent_assignment,
)
from app.db.database import Base
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.services.task_scheduling import recalculate_schedule


class TaskSchedulingServiceTests(unittest.TestCase):
    def test_recalculation_updates_orm_tasks_in_place(self):
        predecessor = Task(
            id=10,
            project_id=1,
            name="Excavate",
            duration=1,
            dependency_type="FS",
            lag_days=0,
        )
        successor = Task(
            id=20,
            project_id=1,
            name="Footings",
            duration=2,
            predecessor_task_id=10,
            dependency_type="FS",
            lag_days=0,
        )

        recalculate_schedule(
            [predecessor, successor],
            project_start=date(2026, 6, 19),
        )

        self.assertEqual(predecessor.start_date, "2026-06-19")
        self.assertEqual(predecessor.end_date, "2026-06-19")
        self.assertEqual(successor.start_date, "2026-06-22")
        self.assertEqual(successor.end_date, "2026-06-23")

    def test_recalculation_rolls_parent_dates_into_orm_task(self):
        parent = Task(
            id=1,
            project_id=1,
            name="Foundation",
            duration=1,
            dependency_type="FS",
            lag_days=0,
        )
        child = Task(
            id=2,
            project_id=1,
            name="Excavate",
            duration=2,
            parent_task_id=1,
            dependency_type="FS",
            lag_days=0,
        )

        recalculate_schedule(
            [parent, child],
            project_start=date(2026, 6, 19),
        )

        self.assertEqual(parent.start_date, child.start_date)
        self.assertEqual(parent.end_date, child.end_date)
        self.assertEqual(parent.duration, 1)


class TaskRelationshipValidationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

        self.session.add(
            User(id=1, email="owner@example.com", hashed_password="hash")
        )
        self.session.add(Project(id=1, name="Project", user_id=1))
        self.session.add_all(
            [
                Task(
                    id=1,
                    project_id=1,
                    name="Parent",
                    duration=1,
                    dependency_type="FS",
                    lag_days=0,
                ),
                Task(
                    id=2,
                    project_id=1,
                    name="Child",
                    duration=1,
                    parent_task_id=1,
                    predecessor_task_id=1,
                    dependency_type="FS",
                    lag_days=0,
                ),
                Task(
                    id=3,
                    project_id=1,
                    name="Grandchild",
                    duration=1,
                    parent_task_id=2,
                    predecessor_task_id=2,
                    dependency_type="FS",
                    lag_days=0,
                ),
            ]
        )
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_parent_cycle_is_rejected(self):
        parent = self.session.get(Task, 1)

        with self.assertRaises(HTTPException) as raised:
            validate_parent_assignment(
                parent,
                3,
                project_id=1,
                db=self.session,
            )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertIn("cycle", raised.exception.detail)

    def test_dependency_cycle_is_rejected(self):
        first = self.session.get(Task, 1)

        with self.assertRaises(HTTPException) as raised:
            validate_dependency_assignment(
                first,
                3,
                project_id=1,
                db=self.session,
            )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertIn("cycle", raised.exception.detail)

    def test_cross_project_reference_is_rejected(self):
        self.session.add(Project(id=2, name="Other", user_id=1))
        self.session.add(
            Task(
                id=4,
                project_id=2,
                name="Other task",
                duration=1,
                dependency_type="FS",
                lag_days=0,
            )
        )
        self.session.commit()
        first = self.session.get(Task, 1)

        with self.assertRaises(HTTPException) as raised:
            validate_dependency_assignment(
                first,
                4,
                project_id=1,
                db=self.session,
            )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertIn("this project", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
