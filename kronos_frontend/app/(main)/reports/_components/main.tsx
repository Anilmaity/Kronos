/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";

import { ChevronLeft, ChevronRight } from "lucide-react";

// GraphQL
import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { PNL_CALENDAR } from "@/GraphQL/reportsControls";

// Components
import { Button } from "@/components/ui/button";

import MonthGrid from "./MonthGrid";
import { CalendarPayload } from "./types";
import { panelStyle, soft } from "@/lib/tvStyles";

// Month navigation is clamped to 2020-01 .. (current year + 1)-12.
const MIN_YEAR = 2020;
const MIN_MONTH = 1;
const MAX_YEAR = new Date().getFullYear() + 1;
const MAX_MONTH = 12;

const toIndex = (year: number, month: number) => year * 12 + (month - 1);
const fromIndex = (idx: number) => ({
  year: Math.floor(idx / 12),
  month: (idx % 12) + 1,
});

const MIN_IDX = toIndex(MIN_YEAR, MIN_MONTH);
const MAX_IDX = toIndex(MAX_YEAR, MAX_MONTH);

const monthLabel = (year: number, month: number) =>
  new Date(year, month - 1, 1).toLocaleString("en-US", {
    month: "long",
    year: "numeric",
  });

// Stamps a fetched payload with the request args it actually answers.
// Rendering must gate on this stamp (see stampMatchesCurrent below) so a
// late/failed navigation can never show a new month's header over an old
// month's data - misattributed money totals must be impossible.
interface CalendarResult {
  payload: CalendarPayload | null;
  forYear: number;
  forMonth: number;
  forBrokerId: string | null;
}

const chipStyle = (
  selected: boolean,
  active: boolean
): React.CSSProperties => ({
  fontSize: "12px",
  fontWeight: 600,
  borderRadius: "4px",
  padding: "5px 12px",
  border: `1px solid ${selected ? "var(--tv-up)" : "var(--tv-border)"}`,
  color: selected ? "var(--tv-up)" : "var(--tv-text-soft)",
  opacity: active ? 1 : 0.5,
  cursor: "pointer",
  background: "transparent",
});

const ReportsPage = () => {
  // Init to the current IST month (server dates are naive wall-clock IST;
  // the browser's local Date() is a reasonable proxy for the initial view).
  const [year, setYear] = useState<number>(() => new Date().getFullYear());
  const [month, setMonth] = useState<number>(() => new Date().getMonth() + 1);
  const [selectedBrokerId, setSelectedBrokerId] = useState<string | null>(
    null
  );

  const [result, setResult] = useState<CalendarResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  // Request-sequence guard: month/chip switches can fire a new fetch before
  // an older one resolves. Each fetch stamps the ref with its own id before
  // awaiting; a response only commits state if its id is still the latest -
  // otherwise it's a stale race loser and is silently dropped.
  const requestIdRef = useRef(0);

  const fetchCalendar = useCallback(async () => {
    const requestId = (requestIdRef.current += 1);
    // Capture this request's own args (not current state) so the commit
    // below stamps the payload with exactly what it answers, even if state
    // has moved on (further navigation) by the time this resolves.
    const reqYear = year;
    const reqMonth = month;
    const reqBrokerId = selectedBrokerId;
    setLoading(true);
    try {
      const { data } = await client.query({
        query: PNL_CALENDAR,
        variables: { year: reqYear, month: reqMonth, userBrokerId: reqBrokerId },
        fetchPolicy: "no-cache",
      });
      if (requestIdRef.current !== requestId) return; // superseded - drop it
      setResult({
        payload: data.pnlCalendar ?? null,
        forYear: reqYear,
        forMonth: reqMonth,
        forBrokerId: reqBrokerId,
      });
      setLoadFailed(false);
      setLoading(false);
    } catch (err) {
      if (requestIdRef.current !== requestId) return; // superseded - drop it
      setLoadFailed(true);
      setLoading(false);
      middleware(err);
    }
  }, [year, month, selectedBrokerId]);

  // Fetch on mount and whenever year, month, or the selected account changes.
  // No polling - this is historical data.
  useEffect(() => {
    fetchCalendar();
  }, [year, month, selectedBrokerId]);

  const navigate = (delta: number) => {
    const idx = Math.min(
      MAX_IDX,
      Math.max(MIN_IDX, toIndex(year, month) + delta)
    );
    const next = fromIndex(idx);
    setYear(next.year);
    setMonth(next.month);
  };

  const atMin = toIndex(year, month) <= MIN_IDX;
  const atMax = toIndex(year, month) >= MAX_IDX;

  // The gate: only trust `result` when it's stamped for exactly what's
  // currently on screen. A mismatch (a late-resolving or failed fetch left
  // an older stamp behind while year/month/selectedBrokerId moved on) falls
  // back to null - the same "Loading..."/failed state a fresh, unanswered
  // request already renders - instead of showing the new header over the
  // old payload's data.
  const stampMatchesCurrent =
    result !== null &&
    result.forYear === year &&
    result.forMonth === month &&
    result.forBrokerId === selectedBrokerId;

  const payload = stampMatchesCurrent ? result.payload : null;

  // Chips deliberately bypass the stamp gate: the accounts list is
  // month-independent ("chip list, unfiltered by month"), and gating it made
  // the chip row collapse under the cursor during every navigation.
  const accounts = result?.payload?.accounts ?? [];

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex items-center justify-between w-full gap-4 flex-wrap">
        <div className="flex flex-col">
          <span className="text-base font-semibold">Reports</span>
          <span className="text-sm" style={soft}>
            Realized PnL per account - days in IST
          </span>
        </div>
      </div>

      <div
        className="flex flex-col gap-4 w-full px-4 py-4"
        style={panelStyle}
      >
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setSelectedBrokerId(null)}
            style={chipStyle(selectedBrokerId === null, true)}
          >
            All accounts
          </button>
          {accounts.map((a) => (
            <button
              type="button"
              key={a.id}
              onClick={() => setSelectedBrokerId(a.id)}
              style={chipStyle(selectedBrokerId === a.id, a.isActive)}
            >
              {a.label}
              {!a.isActive ? " (archived)" : ""}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(-1)}
            disabled={atMin}
            aria-label="Previous month"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-semibold min-w-[140px] text-center">
            {monthLabel(year, month)}
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(1)}
            disabled={atMax}
            aria-label="Next month"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {loadFailed && !loading && (
          <span className="text-sm" style={{ color: "var(--tv-down)" }}>
            Failed to load the PnL calendar.
          </span>
        )}

        {/*
          MonthGrid renders its own "Loading..." state while payload is
          null (first load / a load that failed before ever succeeding).
          Once a payload exists, the wrapper below just dims it during a
          refetch so month/chip switches have a visible loading cue.
        */}
        {!(loadFailed && payload === null) && (
          <div
            style={{
              opacity: loading ? 0.6 : 1,
              transition: "opacity 150ms ease",
            }}
          >
            <MonthGrid payload={payload} year={year} month={month} />
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportsPage;
