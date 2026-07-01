import Icon from "./Icon";

/**
 * Reusable sidebar container built on the shared `.app-sidebar` shell.
 *
 * Two modes, composable:
 *  - Navigation: pass `items` (`{ id, label, onClick, icon? }`); the entry
 *    whose id matches `activeId` is marked as the current page. `navHeading`
 *    renders a visible label above the list.
 *  - Control panel: pass arbitrary `children` (e.g. the Scheduler's view
 *    toggle, template forms, export action).
 *
 * `header` and `footer` are free-form slots; `footer` is pinned to the bottom
 * when the sidebar is a flex column (see `.sidebar-footer`).
 */
function Sidebar({
  header,
  navHeading,
  items = [],
  activeId,
  footer,
  children,
  ariaLabel = "Primary",
  className = "",
}) {
  const hasNav = items.length > 0;

  return (
    <aside className={["app-sidebar", className].filter(Boolean).join(" ")}>
      {header && <div className="sidebar-header">{header}</div>}

      {hasNav && navHeading && (
        <h2 className="sidebar-heading">{navHeading}</h2>
      )}

      {hasNav && (
        <nav className="sidebar-nav" aria-label={ariaLabel}>
          {items.map((item) => {
            const isActive = item.id === activeId;

            return (
              <button
                key={item.id}
                type="button"
                className={[
                  "sidebar-nav-item",
                  isActive ? "is-active" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                aria-current={isActive ? "page" : undefined}
                onClick={item.onClick}
              >
                {item.icon && <Icon name={item.icon} size={18} />}
                {item.label}
              </button>
            );
          })}
        </nav>
      )}

      {children}

      {footer && <div className="sidebar-footer">{footer}</div>}
    </aside>
  );
}

export default Sidebar;
