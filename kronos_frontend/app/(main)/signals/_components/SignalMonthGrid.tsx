"use client";

import React from "react";

import {
  buildWeeks,
  DayCounts,
  FIRED_COLOR,
} from "./signalCalendar";

import { panelStyle } from "@/lib/tvStyles";

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const countChip = (color: string): React.CSSProperties => ({
  fontSize: "11px",
  fontWeight: 700,
  color,
  lineHeight: 1.2,
});

interface SignalMonthGridProps {
  days: Record<string, DayCounts>; // already chip-filtered by the parent
  year: number;
  month: number;
  selectedDay: string | null;
  onSelectDay: (key: string | null) => void;
}

const SignalMonthGrid: React.FC<SignalMonthGridProps> = ({
  days,
  year,
  month,
  selectedDay,
  onSelectDay,
}) => {
  const weeks = buildWeeks(year, month);

  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-[640px]">
        <div className="grid grid-cols-7 gap-1 mb-1">
          {WEEKDAY_LABELS.map((label) => (
            <div
              key={label}
              className="text-center text-xs font-semibold py-1"
              style={{ color: "var(--tv-text-soft)" }}
            >
              {label}
            </div>
          ))}
        </div>

        {weeks.map((week, wi) => (
          <div key={wi} className="grid grid-cols-7 gap-1 mb-1">
            {week.map((cell) => {
              const counts = days[cell.key];
              const selected = selectedDay === cell.key;
              const clickable = cell.inMonth && !!counts;
              return (
                <button
                  type="button"
                  key={cell.key}
                  disabled={!clickable}
                  onClick={() => onSelectDay(selected ? null : cell.key)}
                  className="flex flex-col items-start gap-0.5 p-2 min-h-[64px] text-left"
                  style={{
                    ...panelStyle,
                    opacity: cell.inMonth ? 1 : 0.35,
                    cursor: clickable ? "pointer" : "default",
                    outline: selected
                      ? "2px solid var(--tv-accent)"
                      : "none",
                    outlineOffset: "-2px",
                  }}
                >
                  <span
                    className="text-xs"
                    style={{ color: "var(--tv-text-soft)" }}
                  >
                    {cell.dayNumber}
                  </span>
                  {counts && counts.placed > 0 && (
                    <span style={countChip("var(--tv-up)")}>
                      {counts.placed} P
                    </span>
                  )}
                  {counts && counts.rejected > 0 && (
                    <span style={countChip("var(--tv-down)")}>
                      {counts.rejected} R
                    </span>
                  )}
                  {counts && counts.fired > 0 && (
                    <span style={countChip(FIRED_COLOR)}>
                      {counts.fired} F
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

export default SignalMonthGrid;
