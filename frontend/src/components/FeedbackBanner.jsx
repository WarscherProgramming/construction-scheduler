import { useEffect } from "react";


const bannerStyles = {
  position: "fixed",
  top: "16px",
  right: "16px",
  zIndex: 1000,
  display: "flex",
  alignItems: "flex-start",
  gap: "12px",
  width: "min(420px, calc(100vw - 32px))",
  padding: "12px 14px",
  border: "1px solid",
  borderRadius: "8px",
  boxShadow: "0 8px 24px rgba(0, 0, 0, 0.16)",
  fontFamily: "Arial, sans-serif",
};

const toneStyles = {
  error: {
    color: "#7f1d1d",
    background: "#fef2f2",
    borderColor: "#fecaca",
  },
  success: {
    color: "#14532d",
    background: "#f0fdf4",
    borderColor: "#bbf7d0",
  },
  info: {
    color: "#1e3a8a",
    background: "#eff6ff",
    borderColor: "#bfdbfe",
  },
};

function FeedbackBanner({ notice, onDismiss }) {
  useEffect(() => {
    if (!notice || notice.type === "error") return undefined;

    const timeoutId = window.setTimeout(onDismiss, 5000);
    return () => window.clearTimeout(timeoutId);
  }, [notice, onDismiss]);

  if (!notice) return null;

  const isError = notice.type === "error";

  return (
    <div
      role={isError ? "alert" : "status"}
      aria-live={isError ? "assertive" : "polite"}
      style={{
        ...bannerStyles,
        ...(toneStyles[notice.type] || toneStyles.info),
      }}
    >
      <div style={{ flex: 1 }}>
        <strong style={{ display: "block", marginBottom: "2px" }}>
          {isError ? "Action needed" : "Success"}
        </strong>
        <span>{notice.message}</span>
      </div>

      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss notification"
        style={{
          minWidth: "32px",
          minHeight: "32px",
          border: 0,
          borderRadius: "4px",
          color: "inherit",
          background: "transparent",
          cursor: "pointer",
          fontSize: "20px",
          lineHeight: 1,
        }}
      >
        <span aria-hidden="true">Close</span>
      </button>
    </div>
  );
}

export default FeedbackBanner;
