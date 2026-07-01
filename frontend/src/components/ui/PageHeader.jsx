/**
 * Consistent page title block: optional eyebrow, the level-1 heading, an
 * optional subtitle, and a right-aligned actions slot.
 */
function PageHeader({ title, subtitle, eyebrow, actions, className = "" }) {
  return (
    <header className={["page-header", className].filter(Boolean).join(" ")}>
      <div className="page-header__text">
        {eyebrow && <p className="page-header__eyebrow">{eyebrow}</p>}
        <h1 className="page-header__title">{title}</h1>
        {subtitle && <p className="page-header__subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
  );
}

export default PageHeader;
