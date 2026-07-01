import SkipLink from "../SkipLink";

/**
 * App shell: skip link, a sidebar slot, and the scrollable main region with the
 * accessibility landmark every page relies on (`#main-content`, focusable).
 */
function AppLayout({ sidebar, children, mainClassName = "", shellClassName = "" }) {
  return (
    <div className={["app-shell", shellClassName].filter(Boolean).join(" ")}>
      <SkipLink />
      {sidebar}
      <main
        id="main-content"
        className={["app-main", mainClassName].filter(Boolean).join(" ")}
        tabIndex={-1}
      >
        {children}
      </main>
    </div>
  );
}

export default AppLayout;
