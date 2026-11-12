/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { RUN_STRATEGY_BACKTEST, STRATEGY_TRADES } from "@/GraphQL/strategyDataControls";
import { Button } from "@/components/ui/button";
import { panelStyle, soft } from "@/lib/tvStyles";

import MonthGrid from "../../reports/_components/MonthGrid";
import { CalendarPayload } from "../../reports/_components/types";
import DayChart, { Trade } from "./DayChart";

export const VIEWS = ["backtest", "paper", "live"] as const;
export type View = (typeof VIEWS)[number];

const VIEW_LABEL: Record<View, string> = { backtest: "Backtest", paper: "Paper", live: "Live" };
const VIEW_NOTE: Record<View, string> = {
  backtest: "Server replay of the strategy's own code over the last two months, 0.01 lot.",
  paper: "Every signal the strategy fired (placed or rejected), played forward on 1-minute candles to its stop or target, 0.01 lot.",
  live: "Closed positions on the broker account.",
};
const ACCOUNT_USD = 10000; // percentages are of the $10k demo account
const POLL_MS = 5000;

interface Result {
  status: string;
  progressPct: number | null;
  error: string | null;
  periodStart: string | null;
  periodEnd: string | null;
  trades: Trade[];
}

const utcDay = (epoch: number) => new Date(epoch * 1000).toISOString().slice(0, 10);
const utcTime = (epoch: number) => new Date(epoch * 1000).toISOString().slice(11, 16);

const toPayload = (trades: Trade[]): CalendarPayload => {
  const byDay = new Map<string, { pnlUsd: number; trades: number }>();
  trades.forEach((t) => {
    const d = byDay.get(utcDay(t.entryTime)) ?? { pnlUsd: 0, trades: 0 };
    d.pnlUsd += t.pnlUsd;
    d.trades += 1;
    byDay.set(utcDay(t.entryTime), d);
  });
  const days = Array.from(byDay, ([date, v]) => ({ date, ...v }));
  return {
    days,
    monthPnlUsd: days.reduce((s, d) => s + d.pnlUsd, 0),
    monthTrades: trades.length,
    winDays: days.filter((d) => d.pnlUsd > 0).length,
    lossDays: days.filter((d) => d.pnlUsd < 0).length,
    accounts: [],
  };
};

const StrategyDataPage = ({
  userStrategyId,
  name,
  initialView,
}: {
  userStrategyId: string;
  name: string;
  initialView: View;
}) => {
  const [view, setView] = useState<View>(initialView);
  const [ym, setYm] = useState(() => {
    const now = new Date();
    return now.getUTCFullYear() * 12 + now.getUTCMonth();
  });
  const year = Math.floor(ym / 12);
  const month = (ym % 12) + 1;
  const [result, setResult] = useState<Result | null>(null);
  const [failed, setFailed] = useState(false);
  const [day, setDay] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const requestRef = useRef(0);

  useEffect(() => {
    setResult(null);
    setDay(null);
  }, [view, ym]);

  useEffect(() => {
    if (!userStrategyId) return undefined;
    const id = (requestRef.current += 1);
    let timer: ReturnType<typeof setTimeout> | undefined;
    client
      .query({
        query: STRATEGY_TRADES,
        variables: { userStrategyId, kind: view, year, month },
        fetchPolicy: "no-cache",
      })
      .then(({ data }) => {
        if (requestRef.current !== id) return; // superseded by a newer tab/month
        const r: Result = data.strategyTrades;
        setResult(r);
        setFailed(false);
        // A queued or running replay: poll until it lands.
        if (r.status === "PENDING" || r.status === "RUNNING") {
          timer = setTimeout(() => setTick((n) => n + 1), POLL_MS);
        }
      })
      .catch((err) => {
        if (requestRef.current !== id) return;
        setFailed(true);
        middleware(err);
      });
    return () => clearTimeout(timer);
  }, [view, ym, tick, userStrategyId]);

  const runBacktest = () => {
    client
      .mutate({ mutation: RUN_STRATEGY_BACKTEST, variables: { userStrategyId } })
      .then(({ data }) => {
        const r = data.runStrategyBacktest;
        if (r.ok) {
          toast.success("Backtest queued");
          setTick((n) => n + 1);
        } else {
          toast.error(r.error ?? "Could not queue the backtest");
        }
      })
      .catch((err) => middleware(err));
  };

  const trades = result?.trades ?? [];
  const payload = useMemo(() => (result ? toPayload(result.trades) : null), [result]);
  const dayTrades = useMemo(
    () => trades.filter((t) => utcDay(t.entryTime) === day),
    [result, day]
  );
  const busy = result?.status === "PENDING" || result?.status === "RUNNING";

  if (!userStrategyId) {
    return (
      <span className="text-sm" style={soft}>
        Open this page from a strategy&apos;s menu on the dashboard.
      </span>
    );
  }

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">{name}</span>
        <span className="text-sm" style={soft}>
          {VIEW_NOTE[view]} Days in UTC, by entry time.
        </span>
      </div>

      <div className="flex flex-col gap-4 w-full px-4 py-4" style={panelStyle}>
        <div className="flex items-center gap-2 flex-wrap" role="tablist">
          {VIEWS.map((v) => (
            <button
              type="button"
              role="tab"
              aria-selected={view === v}
              key={v}
              onClick={() => setView(v)}
              className={`tv-chip ${view === v ? "tv-chip--up" : ""}`}
            >
              {VIEW_LABEL[v]}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <Button variant="ghost" size="icon" onClick={() => setYm(ym - 1)} aria-label="Previous month">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-semibold min-w-[140px] text-center">
            {new Date(Date.UTC(year, month - 1, 1)).toLocaleString("en-US", {
              month: "long",
              year: "numeric",
              timeZone: "UTC",
            })}
          </span>
          <Button variant="ghost" size="icon" onClick={() => setYm(ym + 1)} aria-label="Next month">
            <ChevronRight className="h-4 w-4" />
          </Button>

          {view === "backtest" && result && (
            <>
              <button type="button" className="tv-chip" onClick={runBacktest} disabled={busy}>
                {result.status === "NONE" ? "Run backtest" : "Re-run backtest"}
              </button>
              <span className="text-sm" style={soft}>
                {result.status === "NONE" && "No backtest yet for this strategy."}
                {busy && `Backtest ${result.status.toLowerCase()} - ${Math.round(result.progressPct ?? 0)}%`}
                {result.status === "DONE" && `Covers ${result.periodStart} to ${result.periodEnd}`}
                {(result.status === "FAILED" || result.status === "CANCELLED") &&
                  `Backtest ${result.status.toLowerCase()}${result.error ? `: ${result.error.slice(0, 160)}` : ""}`}
              </span>
            </>
          )}
        </div>

        {failed ? (
          <span className="text-sm" style={{ color: "var(--tv-down)" }}>
            Failed to load trades.
          </span>
        ) : (
          <MonthGrid
            payload={payload}
            year={year}
            month={month}
            pctBase={ACCOUNT_USD}
            selectedDay={day}
            onDayClick={setDay}
          />
        )}
      </div>

      {day && (
        <div className="flex flex-col gap-3 w-full px-4 py-4" style={panelStyle}>
          <span className="text-sm font-semibold">
            {day} - {dayTrades.length} trades
          </span>
          <DayChart day={day} trades={dayTrades} />
          <table className="w-full text-sm tnum">
            <thead>
              <tr style={soft}>
                {["#", "Side", "In (UTC)", "Entry", "Out (UTC)", "Exit", "Result", "PnL", "Note"].map((h) => (
                  <th key={h} className="text-left font-medium py-1">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dayTrades.map((t, i) => (
                <tr key={`${t.entryTime}-${i}`} style={{ borderTop: "1px solid var(--tv-border)" }}>
                  <td className="py-1">{i + 1}</td>
                  <td>{t.side}</td>
                  <td>{utcTime(t.entryTime)}</td>
                  <td>{t.entryPrice.toFixed(2)}</td>
                  <td>{utcTime(t.exitTime)}</td>
                  <td>{t.exitPrice.toFixed(2)}</td>
                  <td>{t.outcome}</td>
                  <td style={{ color: t.pnlUsd >= 0 ? "var(--tv-up)" : "var(--tv-down)" }}>
                    {t.pnlUsd >= 0 ? "+" : "-"}${Math.abs(t.pnlUsd).toFixed(2)}
                  </td>
                  <td style={soft}>{t.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default StrategyDataPage;
