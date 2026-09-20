"use client";

import React from "react";

import { CalendarPayload, PnlDay } from "./types";
import { panelStyle, soft } from "@/lib/tvStyles";

const UP = "var(--tv-up)";
const DOWN = "var(--tv-down)";

const pnlColor = (n: number): string =>
  n > 0 ? UP : n < 0 ? DOWN : "var(--tv-text-soft)";

// Rounds to whole dollars and prefixes a sign, e.g. 212.4 -> "+$212",
// -42 -> "-$42", 0 -> "$0".
const fmtSignedUsd = (n: number): string => {
  const rounded = Math.round(n);
  const sign = rounded > 0 ? "+" : rounded < 0 ? "-" : "";
  return `${sign}$${Math.abs(rounded)}`;
};

const pad2 = (n: number): string => String(n).padStart(2, "0");

// All date math below is done with UTC accessors (Date.UTC / getUTC*) on
// purpose - the payload's day keys are plain "YYYY-MM-DD" strings with no
// timezone attached, and mixing in local-time Date methods would drift the
// grid by a day around DST/timezone boundaries. Cells are matched to
// payload days by string key, never by Date equality.
const dateKey = (y: number, m0: number, d: number): string => {
  const dt = new Date(Date.UTC(y, m0, d));
  return `${dt.getUTCFullYear()}-${pad2(dt.getUTCMonth() + 1)}-${pad2(dt.getUTCDate())}`;
};

interface DayCell {
  key: string; // "YYYY-MM-DD"
  dayNumber: number;
  inMonth: boolean;
}

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Week"];

// Builds full Monday-start week rows covering the given month, including
// dimmed leading/trailing cells that belong to the adjacent months.
const buildWeeks = (year: number, month: number): DayCell[][] => {
  const monthIndex = month - 1; // Date.UTC takes a 0-indexed month
  const firstOfMonth = new Date(Date.UTC(year, monthIndex, 1));
  const leading = (firstOfMonth.getUTCDay() + 6) % 7; // Mon=0 .. Sun=6
  const daysInMonth = new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate();
  const totalCells = Math.ceil((leading + daysInMonth) / 7) * 7;

  const cells: DayCell[] = [];
  for (let i = 0; i < totalCells; i += 1) {
    const dayOffset = i - leading + 1; // 1..daysInMonth is in-month
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

interface MonthGridProps {
  payload: CalendarPayload | null;
  year: number;
  month: number;
}

const MonthGrid = ({ payload, year, month }: MonthGridProps) => {
  const weeks = React.useMemo(() => buildWeeks(year, month), [year, month]);

  if (payload === null) {
    return (
      <div
        className="w-full px-4 py-6 flex items-center justify-center"
        style={panelStyle}
      >
        <span className="text-sm" style={soft}>
          Loading...
        </span>
      </div>
    );
  }

  const dayMap = new Map<string, PnlDay>();
  payload.days.forEach((d) => dayMap.set(d.date, d));

  const netLabel = `net ${fmtSignedUsd(payload.monthPnlUsd)} - ${payload.monthTrades} trades - ${payload.winDays}W / ${payload.lossDays}L`;

  return (
    <div className="w-full flex flex-col gap-3">
      <span
        className="text-sm font-semibold tnum"
        style={{ color: pnlColor(payload.monthPnlUsd) }}
      >
        {netLabel}
      </span>

      {payload.days.length === 0 && (
        <span className="text-sm" style={soft}>
          No closed trades this month.
        </span>
      )}

      <div
        className="grid"
        style={{ gridTemplateColumns: "repeat(7, 1fr) 88px" }}
      >
        {WEEKDAY_LABELS.map((label) => (
          <div key={label} className="text-xs px-2 py-1" style={soft}>
            {label}
          </div>
        ))}

        {weeks.map((week, weekIdx) => {
          let weekPnlUsd = 0;
          let weekTrades = 0;
          week.forEach((cell) => {
            if (!cell.inMonth) return;
            const day = dayMap.get(cell.key);
            if (day) {
              weekPnlUsd += day.pnlUsd;
              weekTrades += day.trades;
            }
          });

          return (
            // eslint-disable-next-line react/no-array-index-key
            <React.Fragment key={`week-${weekIdx}`}>
              {week.map((cell) => {
                const day = cell.inMonth ? dayMap.get(cell.key) : undefined;
                const showPnl = day !== undefined && day.pnlUsd !== 0;
                return (
                  <div
                    key={cell.key}
                    className="flex flex-col justify-between px-2 py-1"
                    style={{
                      border: "1px solid var(--tv-border)",
                      minHeight: "72px",
                      opacity: cell.inMonth ? 1 : 0.4,
                    }}
                  >
                    <span className="text-xs" style={soft}>
                      {cell.dayNumber}
                    </span>
                    {showPnl && (
                      <div className="flex flex-col items-end">
                        <span
                          className="text-sm font-semibold tnum"
                          style={{ color: pnlColor(day.pnlUsd) }}
                        >
                          {fmtSignedUsd(day.pnlUsd)}
                        </span>
                        <span className="text-xs tnum" style={soft}>
                          {day.trades}t
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}

              <div
                className="flex flex-col justify-between px-2 py-1"
                style={{ border: "1px solid var(--tv-border)", minHeight: "72px" }}
              >
                <span className="text-xs" style={soft}>
                  Week
                </span>
                <span
                  className="text-sm font-semibold tnum self-end"
                  style={{
                    color:
                      weekTrades > 0
                        ? pnlColor(weekPnlUsd)
                        : "var(--tv-text-soft)",
                  }}
                >
                  {weekTrades > 0 ? fmtSignedUsd(weekPnlUsd) : "-"}
                </span>
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default MonthGrid;
