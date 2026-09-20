// Pure calendar logic for the signals page - no React, no GraphQL, unit-tested.
// Day bucketing is IST (UTC+5:30), matching the Reports PnL calendar.

export interface CalendarSignal {
  signalAt: string | null;
  status: string;
}

export interface DayCounts {
  placed: number;
  rejected: number;
  fired: number;
}

export interface MonthSummary {
  total: number;
  placed: number;
  rejected: number;
  fired: number;
}

export interface DayCell {
  key: string; // "YYYY-MM-DD"
  dayNumber: number;
  inMonth: boolean;
}

export type StatusFilter = "ALL" | "FIRED" | "PLACED" | "REJECTED";

// The tv token set has no amber; FIRED keeps the page's historical amber.
export const FIRED_COLOR = "#d4a648";

const IST_OFFSET_MS = (5 * 60 + 30) * 60 * 1000;

const pad2 = (n: number): string => String(n).padStart(2, "0");

// "YYYY-MM-DD" IST calendar day for a UTC timestamp string; null when the
// timestamp is missing or unparseable (such rows never reach the calendar).
export const istDayKey = (signalAt: string | null): string | null => {
  if (!signalAt) return null;
  const t = Date.parse(signalAt);
  if (Number.isNaN(t)) return null;
  const d = new Date(t + IST_OFFSET_MS);
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(
    d.getUTCDate()
  )}`;
};

// UTC fetch window covering the IST month: [1st 00:00 IST, next month 00:00 IST).
// graphene.DateTime on the backend parses these ISO-8601 strings directly.
export const monthWindowUtc = (
  year: number,
  month: number
): { since: string; until: string } => {
  const startMs = Date.UTC(year, month - 1, 1) - IST_OFFSET_MS;
  const endMs = Date.UTC(year, month, 1) - IST_OFFSET_MS - 1;
  return {
    since: new Date(startMs).toISOString(),
    until: new Date(endMs).toISOString(),
  };
};

const matchesFilter = (s: CalendarSignal, f: StatusFilter): boolean =>
  f === "ALL" || s.status === f;

export const bucketByDay = (
  signals: CalendarSignal[],
  filter: StatusFilter
): Record<string, DayCounts> => {
  const out: Record<string, DayCounts> = {};
  for (const s of signals) {
    if (!matchesFilter(s, filter)) continue;
    const key = istDayKey(s.signalAt);
    if (!key) continue;
    if (!out[key]) out[key] = { placed: 0, rejected: 0, fired: 0 };
    if (s.status === "PLACED") out[key].placed += 1;
    else if (s.status === "REJECTED") out[key].rejected += 1;
    else if (s.status === "FIRED") out[key].fired += 1;
  }
  return out;
};

// Always the full unfiltered month - the header's stable reference line.
export const monthSummary = (signals: CalendarSignal[]): MonthSummary => {
  const out: MonthSummary = { total: 0, placed: 0, rejected: 0, fired: 0 };
  for (const s of signals) {
    out.total += 1;
    if (s.status === "PLACED") out.placed += 1;
    else if (s.status === "REJECTED") out.rejected += 1;
    else if (s.status === "FIRED") out.fired += 1;
  }
  return out;
};

// All date math below uses UTC accessors (Date.UTC / getUTC*) on purpose -
// day keys are plain "YYYY-MM-DD" strings with no timezone attached, and
// mixing in local-time Date methods would drift the grid by a day around
// DST/timezone boundaries. (Same approach as reports/MonthGrid.tsx.)
const dateKey = (y: number, m0: number, d: number): string => {
  const dt = new Date(Date.UTC(y, m0, d));
  return `${dt.getUTCFullYear()}-${pad2(dt.getUTCMonth() + 1)}-${pad2(
    dt.getUTCDate()
  )}`;
};

// Full Monday-start week rows covering the month, including dimmed
// leading/trailing cells belonging to adjacent months.
export const buildWeeks = (year: number, month: number): DayCell[][] => {
  const monthIndex = month - 1;
  const firstOfMonth = new Date(Date.UTC(year, monthIndex, 1));
  const leading = (firstOfMonth.getUTCDay() + 6) % 7; // Mon=0 .. Sun=6
  const daysInMonth = new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate();
  const totalCells = Math.ceil((leading + daysInMonth) / 7) * 7;

  const cells: DayCell[] = [];
  for (let i = 0; i < totalCells; i += 1) {
    const dayOffset = i - leading + 1;
    const dt = new Date(Date.UTC(year, monthIndex, dayOffset));
    cells.push({
      key: dateKey(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate()),
      dayNumber: dt.getUTCDate(),
      inMonth: dayOffset >= 1 && dayOffset <= daysInMonth,
    });
  }

  const weeks: DayCell[][] = [];
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7));
  }
  return weeks;
};

// "2026-08-01" -> "Sat 01 Aug" (for the selected-day clear chip).
export const dayLabel = (key: string): string => {
  const [y, m, d] = key.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  const weekday = dt.toLocaleString("en-US", {
    weekday: "short",
    timeZone: "UTC",
  });
  const monthName = dt.toLocaleString("en-US", {
    month: "short",
    timeZone: "UTC",
  });
  return `${weekday} ${pad2(d)} ${monthName}`;
};
