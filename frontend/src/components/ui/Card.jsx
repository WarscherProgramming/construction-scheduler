/**
 * Surface container with optional header (title + actions). Wraps the existing
 * card visual treatment so pages stop hand-rolling padded/bordered divs.
 */
function Card({
  title,
  actions,
  as: Tag = "section",
  className = "",
  bodyClassName = "",
  children,
  ...props
}) {
  const hasHeader = Boolean(title || actions);

  return (
    <Tag className={["card", className].filter(Boolean).join(" ")} {...props}>
      {hasHeader && (
        <div className="card__header">
          {title && <h2 className="card__title">{title}</h2>}
          {actions && <div className="card__actions">{actions}</div>}
        </div>
      )}
      <div className={["card__body", bodyClassName].filter(Boolean).join(" ")}>
        {children}
      </div>
    </Tag>
  );
}

export default Card;
