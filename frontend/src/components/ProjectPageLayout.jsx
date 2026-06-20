import { buttonStyle } from "../styles";

function ProjectPageLayout({ title, onBack, children }) {
  return (
    <div style={{ padding: "24px", fontFamily: "Arial, sans-serif" }}>
      <button onClick={onBack} style={buttonStyle}>
        Back to Project Dashboard
      </button>

      <h1>{title}</h1>
      {children}
    </div>
  );
}

export default ProjectPageLayout;
