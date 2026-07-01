/**
 * Loading skeleton primitives. Purely visual — the shimmering blocks are
 * decorative (`aria-hidden`); accessible loading text lives on the wrapping
 * SkeletonPanel so screen readers hear the same messages tests assert on.
 */
export function Skeleton({ className = "", style, ...props }) {
  return (
    <span
      aria-hidden="true"
      className={`skeleton ${className}`.trim()}
      style={style}
      {...props}
    />
  );
}

const LINE_WIDTHS = ["100%", "86%", "94%", "72%"];

/**
 * A block of skeleton lines announced as a single status. `label` is exposed
 * to assistive tech (visually hidden) — pass the same message the previous
 * text-based loading state used (e.g. "Loading inspections…").
 */
export function SkeletonPanel({ label, lines = 3, className = "" }) {
  return (
    <div role="status" className={`skeleton-panel ${className}`.trim()}>
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton
          key={index}
          className="skeleton--line"
          style={{ width: LINE_WIDTHS[index % LINE_WIDTHS.length] }}
        />
      ))}
    </div>
  );
}
