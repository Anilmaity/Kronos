/**
 * Shared display formatters.
 *
 * These were previously re-declared per page (signals, backtests, manager,
 * dashboard PositionRows). Where two pages' versions differed, both variants
 * are exported under distinct names — behavior is identical to the originals.
 */

/** Fixed-digit number, "—" for empty/invalid. (signals + backtests) */
export const fmtNum = (
  v: string | number | null | undefined,
  digits = 2
): string => {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return n.toFixed(digits);
};

/** Like fmtNum but with an explicit "+" for non-negative values. (backtests) */
export const fmtSigned = (
  v: string | number | null | undefined,
  digits = 2
): string => {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return (n >= 0 ? "+" : "") + n.toFixed(digits);
};

/** P&L colour: tv-down below zero, tv-up otherwise, soft for empty/invalid. (backtests) */
export const pnlColor = (v: string | number | null | undefined): string => {
  if (v === null || v === undefined || v === "") return "var(--tv-text-soft)";
  const n = Number(v);
  if (Number.isNaN(n)) return "var(--tv-text-soft)";
  return n < 0 ? "var(--tv-down)" : "var(--tv-up)";
};

/** Full date-time in IST (en-IN, 24h), returns the input on parse failure. (signals) */
export const fmtTime = (v: string | null | undefined): string => {
  if (!v) return "—";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
};

/** Short "Mon DD HH:MM" in the browser locale, "—" for empty/invalid. (manager) */
export const fmtDateTime = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return `${d.toLocaleDateString(undefined, {
    month: "short",
    day: "2-digit",
  })} ${d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  })}`;
};

/** Adaptive-precision number for regime metrics. (manager) */
export const fmtNumber = (value: any): string => {
  if (typeof value === "number") {
    return Math.abs(value) >= 100 ? value.toFixed(1) : value.toFixed(3);
  }
  return String(value);
};

/** 12-hour local wall-clock time, en-US. (dashboard PositionRows) */
export const formatTime12h = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleString("en-US", {
    hour: "numeric",
    minute: "numeric",
    second: "numeric",
    hour12: true,
  });
};
