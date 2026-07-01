/**
 * FieldFlow brand mark (Concept A): three ascending bars = schedule + progress.
 *
 * Renders the mark alone, or the mark plus the "FieldFlow" wordmark. The mark
 * uses the brand color by default; pass `tone="mono"` (currentColor) for use on
 * colored/inverted surfaces.
 *
 * @param {number} size        Mark height in px (width scales to match).
 * @param {boolean} showWordmark  Render the "FieldFlow" text beside the mark.
 * @param {"brand"|"mono"} tone   Fill: brand blue (default) or currentColor.
 */
function Logo({
  size = 24,
  showWordmark = false,
  tone = "brand",
  className = "",
  ...props
}) {
  const fill = tone === "mono" ? "currentColor" : "var(--brand)";

  const mark = (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      role="img"
      aria-label="FieldFlow"
      focusable="false"
    >
      <rect x="3" y="13" width="4.2" height="8" rx="1.4" fill={fill} opacity="0.55" />
      <rect x="9.9" y="8" width="4.2" height="13" rx="1.4" fill={fill} opacity="0.8" />
      <rect x="16.8" y="3" width="4.2" height="18" rx="1.4" fill={fill} />
    </svg>
  );

  if (!showWordmark) {
    return (
      <span className={`brand-logo ${className}`.trim()} {...props}>
        {mark}
      </span>
    );
  }

  return (
    <span className={`brand-logo brand-logo--wordmark ${className}`.trim()} {...props}>
      {mark}
      <span className="brand-logo__wordmark">FieldFlow</span>
    </span>
  );
}

export default Logo;
