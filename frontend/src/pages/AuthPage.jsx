import FormField from "../components/FormField";
import { buttonStyle } from "../styles";

function AuthPage({
  authMode,
  email,
  password,
  onEmailChange,
  onPasswordChange,
  onLogin,
  onRegister,
  onToggleMode,
  isSubmitting = false,
}) {
  const handleSubmit = (event) => {
    event.preventDefault();

    if (authMode === "login") {
      onLogin();
    } else {
      onRegister();
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>FieldFlow</h1>

      <h2>{authMode === "login" ? "Login" : "Register"}</h2>

      <form
        className="form-stack"
        onSubmit={handleSubmit}
        style={{ marginBottom: "12px", maxWidth: "420px" }}
      >
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
              authMode === "login" ? "current-password" : "new-password"
            }
            required
            value={password}
            onChange={(event) => onPasswordChange(event.target.value)}
          />
        </FormField>

        <button
          type="submit"
          className="button-primary"
          disabled={isSubmitting}
          aria-busy={isSubmitting}
          style={buttonStyle}
        >
          {isSubmitting
            ? authMode === "login"
              ? "Logging in…"
              : "Creating account…"
            : authMode === "login"
              ? "Login"
              : "Register"}
        </button>
      </form>

      <button
        type="button"
        onClick={onToggleMode}
        disabled={isSubmitting}
        style={buttonStyle}
      >
        {authMode === "login"
          ? "Need an account? Register"
          : "Already have an account? Login"}
      </button>
    </div>
  );
}

export default AuthPage;
