function AuthPage({
  authMode,
  email,
  password,
  onEmailChange,
  onPasswordChange,
  onLogin,
  onRegister,
  onToggleMode,
}) {
  return (
    <div style={{ padding: "20px" }}>
      <h1>Construction Scheduler</h1>

      <h2>{authMode === "login" ? "Login" : "Register"}</h2>

      <input
        placeholder="Email"
        value={email}
        onChange={(event) => onEmailChange(event.target.value)}
      />

      <input
        placeholder="Password"
        type="password"
        value={password}
        onChange={(event) => onPasswordChange(event.target.value)}
      />

      {authMode === "login" ? (
        <button onClick={onLogin}>Login</button>
      ) : (
        <button onClick={onRegister}>Register</button>
      )}

      <button onClick={onToggleMode}>
        {authMode === "login"
          ? "Need an account? Register"
          : "Already have an account? Login"}
      </button>
    </div>
  );
}

export default AuthPage;
