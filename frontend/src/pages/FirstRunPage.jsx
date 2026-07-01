import SkipLink from "../components/SkipLink";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import Logo from "../components/ui/Logo";
import { DEMO_PROJECT_NAME } from "../data/demoProject";

function SeedingProgress({ seedProgress }) {
  const total = seedProgress?.total || 0;
  const step = seedProgress?.step || 0;
  const percent = total > 0 ? Math.round((step / total) * 100) : 0;

  return (
    <div className="seed-progress" role="status" aria-live="polite">
      <h1 className="first-run__title">Building your demo project…</h1>
      <p className="first-run__lead">
        {seedProgress?.label || "Setting things up…"}
      </p>

      <div
        className="seed-progress__bar"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label="Demo project setup progress"
      >
        <span style={{ width: `${percent}%` }} />
      </div>

      <p className="seed-progress__count">
        {total > 0
          ? `${step} of ${total} records created`
          : "Preparing sample data…"}
      </p>
    </div>
  );
}

function FirstRunPage({
  onLoadSample,
  onStartEmpty,
  isSeeding = false,
  seedProgress = null,
  onLogout,
}) {
  return (
    <>
      <SkipLink />
      <main id="main-content" className="first-run" tabIndex={-1}>
        <div className="first-run__card">
          <div className="first-run__brand">
            <Logo size={30} showWordmark />
          </div>

          {isSeeding ? (
            <SeedingProgress seedProgress={seedProgress} />
          ) : (
            <>
              <div className="first-run__intro">
                <h1 className="first-run__title">Welcome to FieldFlow</h1>
                <p className="first-run__lead">
                  Get a feel for the platform with a fully built sample project,
                  or start fresh with your own.
                </p>
              </div>

              <div className="first-run__choices">
                <section className="choice-card choice-card--primary">
                  <span className="choice-card__icon choice-card__icon--brand">
                    <Icon name="calendar" size={22} />
                  </span>
                  <h2 className="choice-card__title">Load a sample project</h2>
                  <p className="choice-card__text">
                    Explore {DEMO_PROJECT_NAME} — a full schedule, daily logs,
                    inspections, and change orders, ready to browse.
                  </p>
                  <Button variant="primary" block onClick={onLoadSample}>
                    Load Sample Project
                  </Button>
                </section>

                <section className="choice-card">
                  <span className="choice-card__icon">
                    <Icon name="plus" size={22} />
                  </span>
                  <h2 className="choice-card__title">
                    Start with an empty workspace
                  </h2>
                  <p className="choice-card__text">
                    Begin from a clean slate and create your first project when
                    you&rsquo;re ready.
                  </p>
                  <Button block onClick={onStartEmpty}>
                    Start With Empty Workspace
                  </Button>
                </section>
              </div>
            </>
          )}
        </div>

        {onLogout && !isSeeding && (
          <button
            type="button"
            className="auth-link first-run__signout"
            onClick={onLogout}
          >
            Sign out
          </button>
        )}
      </main>
    </>
  );
}

export default FirstRunPage;
