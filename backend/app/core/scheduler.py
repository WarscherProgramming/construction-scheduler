
from datetime import datetime, timedelta

PROJECT_START = datetime(2026, 1, 1)

def calculate_schedule(tasks):
    task_map = {task["id"]: task for task in tasks}

    for task in tasks:
        task.pop("start_date", None)
        task.pop("end_date", None)

    for _ in range(len(tasks)):
        for task in tasks:
            if task.get("predecessor_id") is None:
                start_date = PROJECT_START
            else:
                predecessor = task_map.get(task["predecessor_id"])

                if not predecessor or "end_date" not in predecessor:
                    continue

                start_date = datetime.strptime(
                    predecessor["end_date"], "%Y-%m-%d"
                )

            end_date = start_date + timedelta(days=task["duration"])

            task["start_date"] = start_date.strftime("%Y-%m-%d")
            task["end_date"] = end_date.strftime("%Y-%m-%d")

    return tasks


