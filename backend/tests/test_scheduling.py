from datetime import date
import unittest

from app.domain.scheduling import (
    ScheduleTask,
    add_workdays,
    calculate_schedule,
    federal_holidays,
    is_workday,
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
        # 2026-06-19 is Juneteenth, so day one becomes Monday 06-22.
        self.assertEqual(
            add_workdays(date(2026, 6, 19), 2),
            date(2026, 6, 23),
        )

    def test_add_workdays_rejects_non_positive_duration(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            add_workdays(date(2026, 6, 19), 0)


class FederalHolidayTests(unittest.TestCase):
    def test_fixed_holidays_are_not_workdays(self):
        self.assertFalse(is_workday(date(2026, 6, 19)))  # Juneteenth (Friday)
        self.assertFalse(is_workday(date(2025, 12, 25)))  # Christmas (Thursday)

    def test_saturday_holiday_is_observed_on_friday(self):
        # 2026-07-04 falls on Saturday; observed Friday 07-03.
        self.assertIn(date(2026, 7, 3), federal_holidays(2026))
        self.assertFalse(is_workday(date(2026, 7, 3)))

    def test_sunday_holiday_is_observed_on_monday(self):
        # 2027-07-04 falls on Sunday; observed Monday 07-05.
        self.assertFalse(is_workday(date(2027, 7, 5)))

    def test_floating_holidays_are_not_workdays(self):
        # Thanksgiving 2026: fourth Thursday of November = 11-26.
        self.assertFalse(is_workday(date(2026, 11, 26)))
        # Labor Day 2026: first Monday of September = 09-07.
        self.assertFalse(is_workday(date(2026, 9, 7)))

    def test_scheduling_skips_observed_holidays(self):
        # Thursday 07-02 counts as day one; Friday 07-03 (observed July 4th),
        # Saturday, and Sunday are skipped, so day two lands Monday 07-06.
        self.assertEqual(
            add_workdays(date(2026, 7, 2), 2),
            date(2026, 7, 6),
        )


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
    # 2026-06-19 is Juneteenth: project work begins Monday 06-22.
    project_start = date(2026, 6, 19)

    def test_independent_task_uses_project_start_and_skips_weekends(self):
        result = calculate_schedule(
            [ScheduleTask(id=1, name="Excavate", duration=3)],
            project_start=self.project_start,
        )

        self.assertEqual(result[0].start_date, "2026-06-22")
        self.assertEqual(result[0].end_date, "2026-06-24")

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

        self.assertEqual(result[1].start_date, "2026-06-25")
        self.assertEqual(result[1].end_date, "2026-06-25")

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

        self.assertEqual(result[1].start_date, "2026-06-25")

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

        self.assertEqual(result[0].start_date, "2026-06-23")
        self.assertEqual(result[1].start_date, "2026-06-22")

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

        self.assertEqual(result[0].start_date, "2026-06-22")
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

        self.assertEqual(result[1].start_date, "2026-06-22")
        self.assertEqual(result[1].end_date, "2026-06-23")
        self.assertEqual(result[0].start_date, "2026-06-22")
        self.assertEqual(result[0].end_date, "2026-06-23")


class CriticalPathTests(unittest.TestCase):
    # Monday 2026-03-02; March 2026 has no federal holidays.
    project_start = date(2026, 3, 2)

    def by_id(self, result):
        return {task.id: task for task in result}

    def test_single_chain_is_fully_critical(self):
        result = self.by_id(
            calculate_schedule(
                [
                    ScheduleTask(id=1, name="Excavate", duration=2),
                    ScheduleTask(
                        id=2,
                        name="Footings",
                        duration=3,
                        predecessor_task_id=1,
                    ),
                ],
                project_start=self.project_start,
            )
        )

        self.assertTrue(result[1].is_critical)
        self.assertTrue(result[2].is_critical)
        self.assertEqual(result[1].total_float, 0)
        self.assertEqual(result[2].total_float, 0)

    def test_parallel_short_branch_has_float(self):
        result = self.by_id(
            calculate_schedule(
                [
                    ScheduleTask(id=1, name="Long chain", duration=5),
                    ScheduleTask(id=2, name="Short branch", duration=2),
                    ScheduleTask(
                        id=3,
                        name="Closeout",
                        duration=1,
                        predecessor_task_id=1,
                    ),
                ],
                project_start=self.project_start,
            )
        )

        self.assertTrue(result[1].is_critical)
        self.assertTrue(result[3].is_critical)
        self.assertFalse(result[2].is_critical)
        self.assertEqual(result[2].total_float, 4)

    def test_lag_keeps_finish_to_start_chain_critical(self):
        result = self.by_id(
            calculate_schedule(
                [
                    ScheduleTask(id=1, name="Pour", duration=1),
                    ScheduleTask(
                        id=2,
                        name="Strip forms",
                        duration=1,
                        predecessor_task_id=1,
                        lag_days=2,
                    ),
                ],
                project_start=self.project_start,
            )
        )

        self.assertTrue(result[1].is_critical)
        self.assertTrue(result[2].is_critical)
        self.assertEqual(result[1].total_float, 0)

    def test_start_to_start_successor_carries_float(self):
        result = self.by_id(
            calculate_schedule(
                [
                    ScheduleTask(id=1, name="Excavate", duration=5),
                    ScheduleTask(
                        id=2,
                        name="Dewatering",
                        duration=2,
                        predecessor_task_id=1,
                        dependency_type="SS",
                        lag_days=1,
                    ),
                ],
                project_start=self.project_start,
            )
        )

        self.assertTrue(result[1].is_critical)
        self.assertEqual(result[1].total_float, 0)
        self.assertFalse(result[2].is_critical)
        self.assertEqual(result[2].total_float, 2)

    def test_summary_tasks_aggregate_children(self):
        result = self.by_id(
            calculate_schedule(
                [
                    ScheduleTask(id=1, name="Foundation", duration=1),
                    ScheduleTask(
                        id=2,
                        name="Excavate",
                        duration=2,
                        parent_task_id=1,
                    ),
                    ScheduleTask(
                        id=3,
                        name="Survey",
                        duration=1,
                        parent_task_id=1,
                        manual_start_date="2026-03-02",
                    ),
                ],
                project_start=self.project_start,
            )
        )

        self.assertTrue(result[2].is_critical)
        self.assertEqual(result[3].total_float, 1)
        self.assertFalse(result[3].is_critical)
        # Summary rows report their most constrained child.
        self.assertTrue(result[1].is_critical)
        self.assertEqual(result[1].total_float, 0)

    def test_unscheduled_cycle_tasks_are_not_critical(self):
        result = self.by_id(
            calculate_schedule(
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
        )

        self.assertFalse(result[1].is_critical)
        self.assertIsNone(result[1].total_float)


if __name__ == "__main__":
    unittest.main()
