from datetime import date
import unittest

from app.domain.scheduling import ScheduleTask, calculate_schedule


class StatusAwareSchedulingTests(unittest.TestCase):
    def calculate(self, tasks, *, data_date="2026-03-09"):
        return calculate_schedule(
            tasks,
            project_start=date(2026, 3, 2),
            data_date=date.fromisoformat(data_date),
        )

    def test_not_started_work_is_held_at_the_data_date(self):
        task = self.calculate(
            [ScheduleTask(id=1, name="Future work", duration=2)]
        )[0]

        self.assertEqual(task.start_date, "2026-03-09")
        self.assertEqual(task.end_date, "2026-03-10")
        self.assertEqual(task.remaining_duration, 2)

    def test_weekend_data_date_moves_incomplete_work_to_monday(self):
        task = self.calculate(
            [ScheduleTask(id=1, name="Future work", duration=1)],
            data_date="2026-03-08",
        )[0]

        self.assertEqual(task.start_date, "2026-03-09")
        self.assertEqual(task.end_date, "2026-03-09")

    def test_completed_task_uses_actuals_and_constrains_successor(self):
        completed, successor = self.calculate(
            [
                ScheduleTask(
                    id=1,
                    name="Completed",
                    duration=5,
                    progress_status="completed",
                    percent_complete=100,
                    actual_start_date="2026-03-02",
                    actual_finish_date="2026-03-04",
                    remaining_duration=0,
                ),
                ScheduleTask(
                    id=2,
                    name="Successor",
                    duration=2,
                    predecessor_task_id=1,
                ),
            ],
            data_date="2026-03-05",
        )

        self.assertEqual(completed.start_date, "2026-03-02")
        self.assertEqual(completed.end_date, "2026-03-04")
        self.assertEqual(completed.total_float, 0)
        self.assertFalse(completed.is_critical)
        self.assertEqual(successor.start_date, "2026-03-05")
        self.assertEqual(successor.end_date, "2026-03-06")

    def test_in_progress_finish_uses_remaining_work_and_data_date(self):
        task = self.calculate(
            [
                ScheduleTask(
                    id=1,
                    name="Active",
                    duration=10,
                    progress_status="in_progress",
                    percent_complete=40,
                    actual_start_date="2026-03-02",
                    remaining_duration=3,
                )
            ]
        )[0]

        self.assertEqual(task.start_date, "2026-03-02")
        self.assertEqual(task.calculation_start_date, "2026-03-09")
        self.assertEqual(task.end_date, "2026-03-11")

    def test_in_progress_remaining_work_retains_finish_to_start_logic(self):
        predecessor, active = self.calculate(
            [
                ScheduleTask(id=1, name="Predecessor", duration=3),
                ScheduleTask(
                    id=2,
                    name="Started early",
                    duration=4,
                    predecessor_task_id=1,
                    progress_status="in_progress",
                    percent_complete=50,
                    actual_start_date="2026-03-05",
                    remaining_duration=2,
                ),
            ]
        )

        self.assertEqual(predecessor.end_date, "2026-03-11")
        self.assertEqual(active.end_date, "2026-03-13")
        self.assertTrue(active.out_of_sequence)
        self.assertIn(
            "FS predecessor boundary 2026-03-12",
            active.out_of_sequence_reason,
        )

    def test_in_progress_predecessor_forecast_constrains_successor(self):
        active, successor = self.calculate(
            [
                ScheduleTask(
                    id=1,
                    name="Active predecessor",
                    duration=5,
                    progress_status="in_progress",
                    percent_complete=60,
                    actual_start_date="2026-03-02",
                    remaining_duration=2,
                ),
                ScheduleTask(
                    id=2,
                    name="Successor",
                    duration=1,
                    predecessor_task_id=1,
                ),
            ]
        )

        self.assertEqual(active.end_date, "2026-03-10")
        self.assertEqual(successor.start_date, "2026-03-11")
        self.assertTrue(active.is_critical)
        self.assertTrue(successor.is_critical)

    def test_summary_predecessor_retains_logic_for_started_successor(self):
        summary, _, active = self.calculate(
            [
                ScheduleTask(id=1, name="Summary", duration=1),
                ScheduleTask(
                    id=2,
                    name="Summary child",
                    duration=2,
                    parent_task_id=1,
                ),
                ScheduleTask(
                    id=3,
                    name="Started successor",
                    duration=3,
                    predecessor_task_id=1,
                    lag_days=1,
                    progress_status="in_progress",
                    percent_complete=50,
                    actual_start_date="2026-03-05",
                    remaining_duration=1,
                ),
            ]
        )

        self.assertEqual(summary.end_date, "2026-03-10")
        self.assertEqual(active.end_date, "2026-03-12")
        self.assertTrue(active.out_of_sequence)
        self.assertIn(
            "FS predecessor boundary 2026-03-12",
            active.out_of_sequence_reason,
        )

    def test_start_to_start_out_of_sequence_uses_start_plus_lag(self):
        _, active = self.calculate(
            [
                ScheduleTask(id=1, name="Predecessor", duration=3),
                ScheduleTask(
                    id=2,
                    name="Started early",
                    duration=4,
                    predecessor_task_id=1,
                    dependency_type="SS",
                    lag_days=2,
                    progress_status="in_progress",
                    percent_complete=25,
                    actual_start_date="2026-03-09",
                    remaining_duration=2,
                ),
            ]
        )

        self.assertTrue(active.out_of_sequence)
        self.assertIn(
            "SS predecessor boundary 2026-03-11",
            active.out_of_sequence_reason,
        )

    def test_summary_progress_is_duration_weighted_and_nested(self):
        parent, child_a, nested, child_b = self.calculate(
            [
                ScheduleTask(id=1, name="Summary", duration=1),
                ScheduleTask(
                    id=2,
                    name="Complete child",
                    duration=4,
                    parent_task_id=1,
                    progress_status="completed",
                    percent_complete=100,
                    actual_start_date="2026-03-02",
                    actual_finish_date="2026-03-05",
                    remaining_duration=0,
                ),
                ScheduleTask(
                    id=3,
                    name="Nested summary",
                    duration=1,
                    parent_task_id=1,
                ),
                ScheduleTask(
                    id=4,
                    name="Active child",
                    duration=2,
                    parent_task_id=3,
                    progress_status="in_progress",
                    percent_complete=50,
                    actual_start_date="2026-03-06",
                    remaining_duration=1,
                ),
            ]
        )

        self.assertEqual(child_a.progress_status, "completed")
        self.assertEqual(child_b.progress_status, "in_progress")
        self.assertEqual(nested.progress_status, "in_progress")
        self.assertEqual(nested.percent_complete, 50)
        self.assertEqual(parent.progress_status, "in_progress")
        self.assertEqual(parent.percent_complete, 83)
        self.assertEqual(parent.actual_start_date, "2026-03-02")
        self.assertIsNone(parent.actual_finish_date)
        self.assertIsNone(parent.remaining_duration)

    def test_recalculation_is_stable_with_progress(self):
        tasks = [
            ScheduleTask(
                id=1,
                name="Active",
                duration=5,
                progress_status="in_progress",
                percent_complete=60,
                actual_start_date="2026-03-03",
                remaining_duration=2,
            ),
            ScheduleTask(
                id=2,
                name="Next",
                duration=1,
                predecessor_task_id=1,
            ),
        ]

        first = self.calculate(tasks)
        second = self.calculate(tasks)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
