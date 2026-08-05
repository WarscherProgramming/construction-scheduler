from datetime import date
import unittest

from app.domain.scheduling import (
    ScheduleDependency,
    ScheduleTask,
    calculate_schedule,
)


class AdvancedSchedulingDomainTests(unittest.TestCase):
    def calculate(self, tasks):
        return calculate_schedule(
            tasks,
            project_start=date(2026, 3, 2),
            data_date=date(2026, 3, 2),
        )

    def test_multiple_predecessors_use_most_restrictive_boundary(self):
        _, _, successor = self.calculate(
            [
                ScheduleTask(id=1, name="First", duration=3),
                ScheduleTask(id=2, name="Second", duration=5),
                ScheduleTask(
                    id=3,
                    name="Successor",
                    duration=2,
                    dependencies=(
                        ScheduleDependency(1, "FS", 0),
                        ScheduleDependency(2, "SS", 2),
                    ),
                ),
            ]
        )

        self.assertEqual(successor.start_date, "2026-03-05")
        self.assertEqual(successor.end_date, "2026-03-06")

    def test_finish_and_start_finish_dependencies(self):
        _, finish_finish, start_finish = self.calculate(
            [
                ScheduleTask(id=1, name="Predecessor", duration=3),
                ScheduleTask(
                    id=2,
                    name="Finish to finish",
                    duration=2,
                    dependencies=(ScheduleDependency(1, "FF", 0),),
                ),
                ScheduleTask(
                    id=3,
                    name="Start to finish",
                    duration=2,
                    dependencies=(ScheduleDependency(1, "SF", 4),),
                ),
            ]
        )

        self.assertEqual(finish_finish.start_date, "2026-03-03")
        self.assertEqual(finish_finish.end_date, "2026-03-04")
        self.assertEqual(start_finish.start_date, "2026-03-05")
        self.assertEqual(start_finish.end_date, "2026-03-06")

    def test_negative_lag_creates_deterministic_lead(self):
        _, successor = self.calculate(
            [
                ScheduleTask(id=1, name="Predecessor", duration=3),
                ScheduleTask(
                    id=2,
                    name="Successor",
                    duration=2,
                    dependencies=(ScheduleDependency(1, "FS", -2),),
                ),
            ]
        )

        self.assertEqual(successor.start_date, "2026-03-03")
        self.assertEqual(successor.end_date, "2026-03-04")

    def test_milestone_is_zero_duration_and_part_of_critical_path(self):
        milestone, successor = self.calculate(
            [
                ScheduleTask(
                    id=1,
                    name="Notice to proceed",
                    duration=0,
                    remaining_duration=0,
                    is_milestone=True,
                ),
                ScheduleTask(
                    id=2,
                    name="Mobilize",
                    duration=2,
                    dependencies=(ScheduleDependency(1),),
                ),
            ]
        )

        self.assertEqual(milestone.start_date, "2026-03-02")
        self.assertEqual(milestone.end_date, "2026-03-02")
        self.assertEqual(successor.start_date, "2026-03-03")
        self.assertTrue(milestone.is_critical)

    def test_lower_bound_constraints_delay_work(self):
        start_bound, finish_bound = self.calculate(
            [
                ScheduleTask(
                    id=1,
                    name="Start bound",
                    duration=2,
                    constraint_type="SNET",
                    constraint_date="2026-03-05",
                ),
                ScheduleTask(
                    id=2,
                    name="Finish bound",
                    duration=2,
                    constraint_type="FNET",
                    constraint_date="2026-03-06",
                ),
            ]
        )

        self.assertEqual(start_bound.start_date, "2026-03-05")
        self.assertEqual(finish_bound.start_date, "2026-03-05")

    def test_upper_bound_constraint_creates_negative_float(self):
        _, successor = self.calculate(
            [
                ScheduleTask(id=1, name="Predecessor", duration=3),
                ScheduleTask(
                    id=2,
                    name="Deadline task",
                    duration=1,
                    dependencies=(ScheduleDependency(1),),
                    constraint_type="SNLT",
                    constraint_date="2026-03-03",
                ),
            ]
        )

        self.assertEqual(successor.start_date, "2026-03-05")
        self.assertTrue(successor.constraint_violated)
        self.assertLess(successor.total_float, 0)
        self.assertTrue(successor.is_critical)

    def test_mandatory_constraint_is_exact_and_reports_conflict(self):
        _, successor = self.calculate(
            [
                ScheduleTask(id=1, name="Predecessor", duration=3),
                ScheduleTask(
                    id=2,
                    name="Mandatory task",
                    duration=1,
                    dependencies=(ScheduleDependency(1),),
                    constraint_type="MS",
                    constraint_date="2026-03-03",
                ),
            ]
        )

        self.assertEqual(successor.start_date, "2026-03-03")
        self.assertTrue(successor.constraint_violated)

    def test_alap_task_moves_to_project_finish(self):
        alap, _, _ = self.calculate(
            [
                ScheduleTask(
                    id=1,
                    name="Late task",
                    duration=1,
                    constraint_type="ALAP",
                ),
                ScheduleTask(id=2, name="Long work", duration=4),
                ScheduleTask(
                    id=3,
                    name="Finish",
                    duration=1,
                    dependencies=(ScheduleDependency(2),),
                ),
            ]
        )

        self.assertEqual(alap.start_date, "2026-03-06")
        self.assertEqual(alap.end_date, "2026-03-06")

    def test_finish_dependency_flags_completed_out_of_sequence_work(self):
        _, completed = self.calculate(
            [
                ScheduleTask(id=1, name="Predecessor", duration=3),
                ScheduleTask(
                    id=2,
                    name="Completed early",
                    duration=2,
                    dependencies=(ScheduleDependency(1, "FF", 0),),
                    progress_status="completed",
                    percent_complete=100,
                    actual_start_date="2026-03-02",
                    actual_finish_date="2026-03-03",
                    remaining_duration=0,
                ),
            ]
        )

        self.assertTrue(completed.out_of_sequence)
        self.assertIn("FF predecessor boundary", completed.out_of_sequence_reason)


if __name__ == "__main__":
    unittest.main()
