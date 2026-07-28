import Button from "../ui/Button";


function DashboardErrorState({ onRetry }) {
  return (
    <section className="dashboard-error" role="alert">
      <h2>Project dashboard unavailable</h2>
      <p>
        Project dashboard data could not be loaded. Other project pages remain
        available.
      </p>
      <Button variant="primary" onClick={onRetry}>
        Retry dashboard
      </Button>
    </section>
  );
}

export default DashboardErrorState;
