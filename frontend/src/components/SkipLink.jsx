function SkipLink({ targetId = "main-content" }) {
  return (
    <a className="skip-link" href={`#${targetId}`}>
      Skip to main content
    </a>
  );
}

export default SkipLink;
