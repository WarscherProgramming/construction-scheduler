from datetime import date
import unittest

from app.domain.scheduling import (
    ScheduleTask,
    add_workdays,
    calculate_schedule,
    next_workday,
)
from app.schemas.task import parse_predecessor_reference


class WorkdayTests(unittest.TestCase):
    def test_next_workday_moves_weekend_to_monday(self):
        self.assertEqual(
            next_workday(date(2026, 6, 20)),
            date(2026, 6, 22),
        )

    def test_add_workdays_counts_start_date_as_day_one(self):
        self.assertEqual(
            add_workdays(date(2026, 6, 19), 2),
            date(2026, 6, 22),
        )

    def test_add_workdays_rejects_non_positive_duration(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            add_workdays(date(2026, 6, 19), 0)


class DependencyReferenceTests(unittest.TestCase):
    def test_reference_uses_immutable_task_id(self):
        self.assertEqual(
            parse_predecessor_reference("205SS+3"),
            (205, "SS", 3),
        )

    def test_empty_reference_clears_dependency(self):
        self.assertEqual(
            parse_predecessor_reference(None),
            (None, "FS", 0),
        )


class ScheduleCalculationTests(unittest.TestCase):
    project_start = date(2026, 6, 19)

    def test_independent_task_uses_project_start_and_skips_weekends(self):
        result = calculate_schedule(
            [ScheduleTask(id=1, name="Excavate", duration=3)],
            project_start=self.project_start,
        )

        self.assertEqual(result[0].start_date, "2026-06-19")
        self.assertEqual(result[0].end_date, "2026-06-23")

    def test_manual_start_is_normalized_to_next_workday(self):
        result = calculate_schedule(
            [
                ScheduleTask(
                    id=1,
                    name="Excavate",
                    duration=1,
                    manual_start_date="2026-06-20",
                )
            ],
            project_start=self.project_start,
        )

        self.assertEqual(result[0].start_date, "2026-06-22")
        self.assertEqual(result[0].end_date, "2026-06-22")

    def test_finish_to_start_dependency_and_lag(self):
        result = calculate_schedule(
            [
                ScheduleTask(id=1, name="Excavate", duration=1),
                ScheduleTask(
                    id=2,
                    name="Footings",
                    duration=1,
                    predecessor_task_id=1,
                    lag_days=2,
                ),
            ],
            project_start=self.project_start,
        )

        self.assertEqual(result[1].start_date, "2026-06-22")
        self.assertEqual(result[1].end_date, "2026-06-22")

    def test_start_to_start_dependency_and_lag(self):
        result = calculate_schedule(
            [
                ScheduleTask(id=1, name="Excavate", duration=5),
                ScheduleTask(
                    id=2,
                    name="Dewatering",
                    duration=1,
                    predecessor_task_id=1,
                    dependency_type="SS",
                    lag_days=3,
                ),
            ],
            project_start=self.project_start,
        )

        self.assertEqual(result[1].start_date, "2026-06-22")

    def test_dependencies_use_stable_ids_instead_of_list_positions(self):
        result = calculate_schedule(
            [
                ScheduleTask(
                    id=20,
                    name="Successor",
                    duration=1,
                    predecessor_task_id=10,
                ),
                ScheduleTask(id=10, name="Predecessor", duration=1),
            ],
            project_start=self.project_start,
        )

        self.assertEqual(result[0].start_date, "2026-06-22")
        self.assertEqual(result[1].start_date, "2026-06-19")

    def test_dependency_cycle_remains_unscheduled(self):
        result = calculate_schedule(
            [
                ScheduleTask(
                    id=1,
                    name="One",
                    duration=1,
                    predecessor_task_id=2,
                ),
                ScheduleTask(
                    id=2,
                    name="Two",
                    duration=1,
                    predecessor_task_id=1,
                ),
            ],
            project_start=self.project_start,
        )

        self.assertIsNone(result[0].start_date)
        self.assertIsNone(result[1].start_date)

    def test_parent_dates_and_duration_roll_up_from_direct_children(self):
        result = calculate_schedule(
            [
                ScheduleTask(id=1, name="Foundation", duration=1),
                ScheduleTask(
                    id=2,
                    name="Excavate",
                    duration=1,
                    parent_task_id=1,
                ),
                ScheduleTask(
                    id=3,
                    name="Footings",
                    duration=2,
                    parent_task_id=1,
                    manual_start_date="2026-06-22",
                ),
            ],
            project_start=self.project_start,
        )

        self.assertEqual(result[0].start_date, "2026-06-19")
        self.assertEqual(result[0].end_date, "2026-06-23")
        self.assertEqual(result[0].duration, 2)

    def test_input_tasks_are_not_mutated(self):
        tasks = [ScheduleTask(id=1, name="Excavate", duration=1)]

        calculate_schedule(tasks, project_start=self.project_start)

        self.assertEqual(tasks[0].duration, 1)
        self.assertFalse(hasattr(tasks[0], "start_date"))

    def test_nested_parent_rollups_use_parent_ids(self):
        result = calculate_schedule(
            [
                ScheduleTask(id=1, name="Project", duration=1),
                ScheduleTask(
                    id=2,
                    name="Foundation",
                    duration=1,
                    parent_task_id=1,
                ),
                ScheduleTask(
                    id=3,
                    name="Excavate",
                    duration=2,
                    parent_task_id=2,
                ),
            ],
            project_start=self.project_start,
        )

        self.assertEqual(result[1].start_date, "2026-06-19")
        self.assertEqual(result[1].end_date, "2026-06-22")
        self.assertEqual(result[0].start_date, "2026-06-19")
        self.assertEqual(result[0].end_date, "2026-06-22")


if __name__ == "__main__":
    unittest.main()
