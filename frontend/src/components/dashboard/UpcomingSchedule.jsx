import EmptyState from "../EmptyState";
import UpcomingTaskItem from "./UpcomingTaskItem";


function UpcomingSchedule({
  tasks,
  hasScheduleTasks,
  projectId,
  onNavigate,
}) {
  const emptyMessage = hasScheduleTasks
    ? "No tasks are scheduled to start in the next seven days."
    : "No schedule tasks have been added to this project.";

  return (
    <section
      className="dashboard-action-section"
      aria-labelledby="dashboard-upcoming-title"
    >
      <div className="dashboard-action-section__header">
        <h2 id="dashboard-upcoming-title">Upcoming Schedule</h2>
        <p>Tasks starting within the next seven days.</p>
      </div>

      {tasks.length === 0 ? (
        <EmptyState title={emptyMessage} />
      ) : (
        <ul className="dashboard-action-list">
          {tasks.map((task, index) => (
            <UpcomingTaskItem
              key={task?.id || index}
              task={task}
              projectId={projectId}
              onNavigate={onNavigate}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

export default UpcomingSchedule;
