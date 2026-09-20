/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { gql } from "@apollo/client";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { fmtNum, fmtTime } from "@/utils/format";
import { Button } from "@/components/ui/button";
import { panelStyle, soft } from "@/lib/tvStyles";

import SignalMonthGrid from "./SignalMonthGrid";
import {
  bucketByDay,
  dayLabel,
  FIRED_COLOR,
  istDayKey,
  monthSummary,
  monthWindowUtc,
  StatusFilter,
} from "./signalCalendar";

interface StrategySignal {
  id: string;
  symbol: string;
  side: string;
  entryPrice: string | null;
  stopLoss: string | null;
  takeProfit: string | null;
  reason: string | null;
  status: string;
  rejectionReason: string | null;
  signalAt: string | null;
  strategyName: string | null;
  strategyId: string | null;
  positionId: string | null;
}

const QUERY = gql`
  query AllStrategySignal($since: DateTime, $until: DateTime, $limit: Int) {
    allStrategySignal(since: $since, until: $until, limit: $limit) {
      id
      symbol
      side
      entryPrice
      stopLoss
      takeProfit
      reason
      status
      rejectionReason
      signalAt
      strategyName
      strategyId
      positionId
    }
  }
`;

const STATUS_FILTERS: StatusFilter[] = ["ALL", "FIRED", "PLACED", "REJECTED"];

// Known bound (spec): a month with >5000 signals would undercount; current
// volume is ~2 orders of magnitude below this.
const MONTH_LIMIT = 5000;

// Month navigation clamp, same policy as the Reports calendar.
const MIN_YEAR = 2026;
const MIN_MONTH = 1;
const MAX_YEAR = new Date().getFullYear() + 1;
const toIndex = (year: number, month: number) => year * 12 + (month - 1);
const fromIndex = (idx: number) => ({
  year: Math.floor(idx / 12),
  month: (idx % 12) + 1,
});
const MIN_IDX = toIndex(MIN_YEAR, MIN_MONTH);
const MAX_IDX = toIndex(MAX_YEAR, 12);

const monthLabelText = (year: number, month: number) =>
  new Date(year, month - 1, 1).toLocaleString("en-US", {
    month: "long",
    year: "numeric",
  });

const chipStyle = (selected: boolean): React.CSSProperties => ({
  fontSize: "12px",
  fontWeight: 600,
  borderRadius: "4px",
  padding: "5px 12px",
  border: `1px solid ${selected ? "var(--tv-up)" : "var(--tv-border)"}`,
  color: selected ? "var(--tv-up)" : "var(--tv-text-soft)",
  cursor: "pointer",
  background: "transparent",
});

const sideColor = (side: string): string =>
  side === "BUY" ? "var(--tv-up)" : side === "SELL" ? "var(--tv-down)" : "var(--tv-text-soft)";

const statusColor = (status: string): string =>
  status === "PLACED"
    ? "var(--tv-up)"
    : status === "REJECTED"
    ? "var(--tv-down)"
    : status === "FIRED"
    ? FIRED_COLOR
    : "var(--tv-text-soft)";

// Stamped result: rendering only trusts a payload fetched for the month
// currently on screen (same race-guard pattern as the Reports calendar).
interface MonthResult {
  signals: StrategySignal[];
  forYear: number;
  forMonth: number;
}

const SignalsPage: React.FC = () => {
  const [year, setYear] = useState<number>(() => new Date().getFullYear());
  const [month, setMonth] = useState<number>(() => new Date().getMonth() + 1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const [result, setResult] = useState<MonthResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const requestIdRef = useRef(0);

  const fetchMonth = useCallback(async () => {
    const requestId = (requestIdRef.current += 1);
    const reqYear = year;
    const reqMonth = month;
    const { since, until } = monthWindowUtc(reqYear, reqMonth);
    setLoading(true);
    setError(null);
    try {
      const { data } = await client.query({
        query: QUERY,
        variables: { since, until, limit: MONTH_LIMIT },
        fetchPolicy: "no-cache",
      });
      if (requestIdRef.current !== requestId) return; // superseded
      setResult({
        signals: data?.allStrategySignal ?? [],
        forYear: reqYear,
        forMonth: reqMonth,
      });
      setError(null);
      setLoading(false);
    } catch (err: any) {
      if (requestIdRef.current !== requestId) return; // superseded
      middleware(err);
      setError(err?.message ?? "Failed to load signals");
      setLoading(false);
    }
  }, [year, month]);

  useEffect(() => {
    fetchMonth();
  }, [year, month]);

  // Day selection never survives a month change.
  const navigate = (delta: number) => {
    const idx = Math.min(MAX_IDX, Math.max(MIN_IDX, toIndex(year, month) + delta));
    const next = fromIndex(idx);
    setSelectedDay(null);
    setYear(next.year);
    setMonth(next.month);
  };
  const atMin = toIndex(year, month) <= MIN_IDX;
  const atMax = toIndex(year, month) >= MAX_IDX;

  const stampMatches =
    result !== null && result.forYear === year && result.forMonth === month;
  const monthSignals = stampMatches ? result.signals : [];

  const summary = useMemo(() => monthSummary(monthSignals), [monthSignals]);
  const days = useMemo(
    () => bucketByDay(monthSignals, statusFilter),
    [monthSignals, statusFilter]
  );

  // Table rows: chip filter, then optional day drill-down. Null-signalAt
  // rows are excluded from day drill-down (they have no day) but listed
  // last in the month view.
  const tableRows = useMemo(() => {
    const filtered = monthSignals.filter(
      (s) => statusFilter === "ALL" || s.status === statusFilter
    );
    if (selectedDay) {
      return filtered.filter((s) => istDayKey(s.signalAt) === selectedDay);
    }
    const dated = filtered.filter((s) => s.signalAt !== null);
    const undated = filtered.filter((s) => s.signalAt === null);
    return [...dated, ...undated];
  }, [monthSignals, statusFilter, selectedDay]);

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex items-center justify-between w-full gap-4 flex-wrap">
        <div className="flex flex-col">
          <span className="text-base font-semibold">Strategy Signals</span>
          <span className="text-sm" style={soft}>
            {stampMatches
              ? `${summary.total} signals — ${summary.placed} placed / ${summary.rejected} rejected / ${summary.fired} fired`
              : "—"}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {STATUS_FILTERS.map((f) => (
            <button
              type="button"
              key={f}
              onClick={() => setStatusFilter(f)}
              style={chipStyle(f === statusFilter)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-4 w-full px-4 py-4" style={panelStyle}>
        <div className="flex items-center gap-3 flex-wrap">
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
            {monthLabelText(year, month)}
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
          {selectedDay && (
            <button
              type="button"
              onClick={() => setSelectedDay(null)}
              style={chipStyle(true)}
              className="inline-flex items-center gap-1"
            >
              <X className="h-3 w-3" />
              {dayLabel(selectedDay)}
            </button>
          )}
        </div>

        {error && !loading && (
          <span className="text-sm" style={{ color: "var(--tv-down)" }}>
            {error}
          </span>
        )}

        {!error && (
          <div style={{ opacity: loading ? 0.6 : 1, transition: "opacity 150ms ease" }}>
            <SignalMonthGrid
              days={days}
              year={year}
              month={month}
              selectedDay={selectedDay}
              onSelectDay={setSelectedDay}
            />
          </div>
        )}
      </div>

      {!loading && !error && tableRows.length === 0 && (
        <div
          className="w-full flex items-center justify-center px-4 py-16 text-sm"
          style={{ ...panelStyle, ...soft }}
        >
          {selectedDay
            ? `No ${statusFilter === "ALL" ? "" : statusFilter.toLowerCase() + " "}signals on ${dayLabel(selectedDay)}`
            : `No signals in ${monthLabelText(year, month)}`}
        </div>
      )}

      {!error && tableRows.length > 0 && (
        <div className="w-full overflow-x-auto" style={panelStyle}>
          <div
            className="flex items-center w-full px-4 py-3 min-w-[1200px] text-xs font-semibold uppercase tracking-wider"
            style={{ ...soft, borderBottom: "1px solid var(--tv-border)" }}
          >
            <div className="w-[13%]">Time (IST)</div>
            <div className="w-[18%]">Strategy</div>
            <div className="w-[8%]">Symbol</div>
            <div className="w-[6%]">Side</div>
            <div className="w-[8%] text-end">Entry</div>
            <div className="w-[8%] text-end">SL</div>
            <div className="w-[8%] text-end">TP</div>
            <div className="w-[8%]">Status</div>
            <div className="w-[23%]">Reason</div>
          </div>

          {tableRows.map((s) => (
            <div
              key={s.id}
              className="flex items-center w-full px-4 py-3 min-w-[1200px] text-sm"
              style={{ borderBottom: "1px solid var(--tv-border)" }}
            >
              <div className="w-[13%] text-xs" style={soft}>
                {fmtTime(s.signalAt)}
              </div>
              <div className="w-[18%] truncate" title={s.strategyName ?? ""}>
                {s.strategyName ?? "—"}
              </div>
              <div className="w-[8%]">{s.symbol}</div>
              <div
                className="w-[6%] font-semibold"
                style={{ color: sideColor(s.side) }}
              >
                {s.side}
              </div>
              <div className="w-[8%] text-end">{fmtNum(s.entryPrice, 2)}</div>
              <div className="w-[8%] text-end">{fmtNum(s.stopLoss, 2)}</div>
              <div className="w-[8%] text-end">{fmtNum(s.takeProfit, 2)}</div>
              <div
                className="w-[8%] text-xs font-semibold"
                style={{ color: statusColor(s.status) }}
              >
                {s.status}
              </div>
              <div
                className="w-[23%] truncate text-xs"
                title={s.status === "REJECTED" ? s.rejectionReason ?? "" : s.reason ?? ""}
                style={soft}
              >
                {s.status === "REJECTED" ? s.rejectionReason ?? "—" : s.reason ?? "—"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SignalsPage;
