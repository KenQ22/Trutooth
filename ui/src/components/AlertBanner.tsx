import React from "react";
import { AlertState } from "../types";

interface AlertBannerProps {
  alert?: AlertState | null;
  onClose?: () => void;
}

const toneStyles: Record<AlertState["tone"], { bg: string; border: string; accent: string }> = {
  positive: {
    bg: "linear-gradient(135deg, rgba(60,229,163,0.18), rgba(60,229,163,0.08))",
    border: "rgba(60,229,163,0.4)",
    accent: "var(--accent)"
  },
  neutral: {
    bg: "rgba(255,255,255,0.06)",
    border: "rgba(255,255,255,0.14)",
    accent: "var(--text-muted)"
  },
  warning: {
    bg: "linear-gradient(135deg, rgba(255,209,102,0.28), rgba(255,209,102,0.1))",
    border: "rgba(255,209,102,0.4)",
    accent: "var(--warning)"
  },
  danger: {
    bg: "linear-gradient(135deg, rgba(249,134,134,0.28), rgba(249,134,134,0.1))",
    border: "rgba(249,134,134,0.4)",
    accent: "var(--danger)"
  }
};

export function AlertBanner({ alert, onClose }: AlertBannerProps) {
  if (!alert) {
    return null;
  }

  const style = toneStyles[alert.tone];

  return (
    <div
      className="alert-banner"
      style={{
        background: style.bg,
        borderColor: style.border,
        color: style.accent
      }}
    >
      <span>{alert.message}</span>
      {onClose && (
        <button type="button" className="ghost" onClick={onClose}>
          Dismiss
        </button>
      )}
    </div>
  );
}
