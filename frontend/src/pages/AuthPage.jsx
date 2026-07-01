import { useState } from "react";

import FormField from "../components/FormField";
import SkipLink from "../components/SkipLink";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import Logo from "../components/ui/Logo";

const HIGHLIGHTS = [
  {
    icon: "calendar",
    title: "Live schedule",
    text: "Drag-and-drop planning with dependencies and critical path.",
  },
  {
    icon: "check",
    title: "Field records",
    text: "Daily logs, inspections, and RFIs captured from the field.",
  },
  {
    icon: "alert-triangle",
    title: "Cost & risk",
    text: "Change orders and delay tracking that holds up under scrutiny.",
  },
  {
    icon: "refresh",
    title: "Always in sync",
    text: "Dashboards update as the job moves, for every stakeholder.",
  },
];

/** Decorative faux-app preview shown on the marketing panel (desktop only). */
function AppPreview() {
  return (
    <div className="auth-preview" aria-hidden="true">
      <div className="auth-preview__bar">
        <span />
        <span />
        <span />
      </div>
      <div className="auth-preview__body">
        <div className="auth-preview__rail">
          <span className="auth-preview__brand" />
          <span className="auth-preview__nav is-active" />
          <span className="auth-preview__nav" />
          <span className="auth-preview__nav" />
          <span className="auth-preview__nav" />
        </div>
        <div className="auth-preview__content">
          <div className="auth-preview__kpis">
            <span />
            <span />
            <span />
          </div>
          <div className="auth-preview__chart">
            <span style={{ height: "42%" }} />
            <span style={{ height: "68%" }} />
            <span style={{ height: "54%" }} />
            <span style={{ height: "83%" }} />
            <span style={{ height: "61%" }} />
            <span className="is-amber" style={{ height: "94%" }} />
          </div>
        </div>
      </div>
    </div>
  );
}

function AuthPage({
  authMode,
  email,
  password,
  onEmailChange,
  onPasswordChange,
  onLogin,
  onRegister,
  onToggleMode,
  onDemo,
  isSubmitting = false,
}) {
  const [showReset, setShowReset] = useState(false);
  const isLogin = authMode === "login";

  const handleSubmit = (event) => {
    event.preventDefault();

    if (isLogin) {
      onLogin();
    } else {
      onRegister();
    }
  };

  return (
    <>
      <SkipLink />
      <main id="main-content" className="auth-page" tabIndex={-1}>
        <div className="auth-layout">
          <section className="auth-marketing" aria-labelledby="auth-headline">
            <div className="auth-marketing__top">
              <Logo size={28} showWordmark />
              <p className="auth-eyebrow">Built for the field</p>
              <h2 id="auth-headline" className="auth-marketing__headline">
                Construction planning and field management, in one place.
              </h2>
              <p className="auth-marketing__sub">
                FieldFlow gives superintendents, project managers, and engineers
                a single source of truth for the schedule, the field, and the
                paper trail.
              </p>

              <ul className="auth-highlights">
                {HIGHLIGHTS.map((item) => (
                  <li key={item.icon} className="auth-highlight">
                    <span className="auth-highlight__icon">
                      <Icon name={item.icon} size={18} />
                    </span>
                    <span>
                      <strong>{item.title}</strong>
                      {` — ${item.text}`}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <AppPreview />
          </section>

          <section className="auth-panel">
            <div className="auth-card">
              <div className="auth-card__brand">
                <Logo size={26} showWordmark />
              </div>

              <div className="auth-card__intro">
                <h1 className="auth-card__title">
                  {isLogin ? "Welcome back" : "Create your account"}
                </h1>
                <p className="auth-card__hint">
                  {isLogin
                    ? "Sign in to your projects."
                    : "Start planning in minutes — no setup required."}
                </p>
              </div>

              <form className="auth-form form-stack" onSubmit={handleSubmit}>
                <FormField label="Email" htmlFor="auth-email" required>
                  <input
                    id="auth-email"
                    className="field-control"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(event) => onEmailChange(event.target.value)}
                  />
                </FormField>

                <FormField label="Password" htmlFor="auth-password" required>
                  <input
                    id="auth-password"
                    className="field-control"
                    type="password"
                    autoComplete={
                      isLogin ? "current-password" : "new-password"
                    }
                    required
                    value={password}
                    onChange={(event) => onPasswordChange(event.target.value)}
                  />
                </FormField>

                {isLogin && (
                  <div className="auth-forgot">
                    <button
                      type="button"
                      className="auth-link"
                      onClick={() => setShowReset((value) => !value)}
                    >
                      Forgot password?
                    </button>
                    {showReset && (
                      <p className="auth-forgot__note" role="status">
                        Password reset is coming soon — contact your project
                        admin to regain access.
                      </p>
                    )}
                  </div>
                )}

                <Button
                  type="submit"
                  variant="primary"
                  block
                  disabled={isSubmitting}
                  aria-busy={isSubmitting}
                >
                  {isSubmitting
                    ? isLogin
                      ? "Signing in…"
                      : "Creating account…"
                    : isLogin
                      ? "Sign in"
                      : "Create account"}
                </Button>
              </form>

              {onDemo && (
                <>
                  <div className="auth-divider">
                    <span>or</span>
                  </div>
                  <Button
                    block
                    onClick={onDemo}
                    disabled={isSubmitting}
                    className="auth-demo"
                  >
                    <Icon name="arrow-right" size={18} />
                    Explore the demo
                  </Button>
                </>
              )}

              <p className="auth-switch">
                <button
                  type="button"
                  className="auth-link"
                  onClick={onToggleMode}
                  disabled={isSubmitting}
                >
                  {isLogin
                    ? "Need an account? Register"
                    : "Already have an account? Login"}
                </button>
              </p>
            </div>
          </section>
        </div>
      </main>
    </>
  );
}

export default AuthPage;
