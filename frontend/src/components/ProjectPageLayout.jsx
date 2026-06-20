import { buttonStyle } from "../styles";
import SkipLink from "./SkipLink";

function ProjectPageLayout({ title, onBack, children }) {
  return (
    <>
      <SkipLink />
      <main id="main-content" className="project-page" tabIndex={-1}>
        <button onClick={onBack} style={buttonStyle}>
          Back to Project Dashboard
        </button>

        <h1>{title}</h1>
        {children}
      </main>
    </>
  );
}

export default ProjectPageLayout;
