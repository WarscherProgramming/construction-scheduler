import { useEffect } from "react";

import Icon from "./ui/Icon";

const TONES = {
  error: { icon: "alert-triangle", title: "Action needed" },
  warning: { icon: "alert-triangle", title: "Heads up" },
  success: { icon: "check-circle", title: "Success" },
  info: { icon: "info", title: "Notice" },
};

function FeedbackBanner({ notice, onDismiss }) {
  useEffect(() => {
    if (!notice || notice.type === "error") return undefined;

    const timeoutId = window.setTimeout(onDismiss, 5000);
    return () => window.clearTimeout(timeoutId);
  }, [notice, onDismiss]);

  if (!notice) return null;

  const isError = notice.type === "error";
  const tone = TONES[notice.type] || TONES.info;
  const toneClass = TONES[notice.type] ? notice.type : "info";

  return (
    <div
      role={isError ? "alert" : "status"}
      aria-live={isError ? "assertive" : "polite"}
      className={`feedback-banner feedback-banner--${toneClass}`}
    >
      <span className="feedback-banner__icon">
        <Icon name={tone.icon} size={20} />
      </span>

      <div className="feedback-banner__body">
        <strong className="feedback-banner__title">
          {notice.title || tone.title}
        </strong>
        <span className="feedback-banner__message">{notice.message}</span>
      </div>

      <button
        type="button"
        className="feedback-banner__close"
        onClick={onDismiss}
        aria-label="Dismiss notification"
      >
        <Icon name="x" size={16} />
      </button>
    </div>
  );
}

export default FeedbackBanner;
