const VARIANT_CLASS = {
  primary: "button-primary",
  secondary: "",
  danger: "button-danger",
  ghost: "button-ghost",
};

/**
 * Shared button. Replaces the inline `buttonStyle` object so every button
 * shares the same sizing, spacing, and variant treatment from CSS.
 */
function Button({
  variant = "secondary",
  size,
  block = false,
  type = "button",
  className = "",
  children,
  ...props
}) {
  const classes = [
    "button",
    VARIANT_CLASS[variant] ?? "",
    size === "sm" ? "button-sm" : "",
    block ? "button-block" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button type={type} className={classes} {...props}>
      {children}
    </button>
  );
}

export default Button;
