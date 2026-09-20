/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { MANAGER_BACKTEST_RUN } from "@/GraphQL/managerBacktestControls";

import { Button } from "@/components/ui/button";

import EquityChart from "./EquityChart";
import {
  ArmSummary, PerStrategyEntry, PointsStats, RunDetail, UsdStats, isActiveStatus,
} from "./types";
import { panelStyle, soft } from "@/lib/tvStyles";

const DETAIL_POLL_MS = 10_000;

const fmt = (n: number | null | undefined, digits = 2) =>
  n === null || n === undefined ? "—" : n.toFixed(digits);

const pnlColor = (n: number) =>
  n > 0 ? "var(--tv-up)" : n < 0 ? "var(--tv-down)" : "var(--tv-text-soft)";

const SummaryCard = ({ arm, s }: { arm: string; s: ArmSummary }) => (
  <div
    className="flex flex-col gap-2 px-4 py-3 min-w-[240px]"
    style={{ ...panelStyle, background: "transparent" }}
  >
    <span className="text-xs uppercase tracking-wide" style={soft}>{arm}</span>
    <div className="flex items-baseline gap-2">
      <span
        className="text-xl font-semibold tnum"
        style={{ color: pnlColor(s.pnl_pts) }}
      >
        {fmt(s.pnl_pts, 1)} pts
      </span>
      <span className="text-sm tnum" style={{ color: pnlColor(s.pnl_usd) }}>
        (${fmt(s.pnl_usd)})
      </span>
    </div>
    <div className="flex items-center gap-4 text-sm flex-wrap">
      <span style={soft}>trades <b>{s.trades}</b></span>
      <span style={soft}>WR <b>{fmt(s.win_rate, 1)}%</b></span>
      <span style={soft}>maxDD <b>{fmt(s.max_dd_pts, 1)}</b></span>
      <span style={soft}>PF <b>{s.profit_factor === null ? "—" : fmt(s.profit_factor)}</b></span>
    </div>
  </div>
);

const emptyCells = (n: number) => (
  <>
    {Array.from({ length: n }, (_, i) => (
      <td key={i} className="py-2 pr-4 text-right" style={soft}>—</td>
    ))}
  </>
);

// Points cells: pnl_pts, profit_factor, win_rate. Points are sizing-invariant
// and always present on sim/live (unlike the matched-usd sub-block).
const PointsCells = ({ s }: { s: PointsStats }) => (
  <>
    <td className="py-2 pr-4 text-right tnum" style={{ color: pnlColor(s.pnl_pts) }}>
      {fmt(s.pnl_pts, 1)}
    </td>
    <td className="py-2 pr-4 text-right tnum">
      {s.profit_factor === null ? "—" : fmt(s.profit_factor)}
    </td>
    <td className="py-2 pr-4 text-right tnum">{fmt(s.win_rate, 1)}%</td>
  </>
);

// USD cells: pnl_usd, trades, win_rate. Absent when live_risk_usd_inferred
// is null (too few live losers to infer a per-trade risk to match sizing).
const UsdCells = ({ s }: { s: UsdStats | undefined }) =>
  s === undefined ? emptyCells(3) : (
    <>
      <td className="py-2 pr-4 text-right tnum" style={{ color: pnlColor(s.pnl_usd) }}>
        ${fmt(s.pnl_usd)}
      </td>
      <td className="py-2 pr-4 text-right tnum">{s.trades}</td>
      <td className="py-2 pr-4 text-right tnum">{fmt(s.win_rate, 1)}%</td>
    </>
  );

const fmtRejected = (rejected: Record<string, number>) => {
  const entries = Object.entries(rejected).filter(([, n]) => n > 0);
  if (entries.length === 0) return "none";
  return entries.map(([reason, n]) => `${reason}:${n}`).join(", ");
};

const ResultsPanel = ({ runId, onClose }: { runId: string; onClose: () => void }) => {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchDetail = useCallback(async () => {
    try {
      const { data } = await client.query({
        query: MANAGER_BACKTEST_RUN,
        variables: { runId },
        fetchPolicy: "no-cache",
      });
      setRun(data.managerBacktestRun ?? null);
      setNotFound(!data.managerBacktestRun);
    } catch (err) {
      middleware(err);
    }
  }, [runId]);

  useEffect(() => {
    setRun(null);
    setNotFound(false);
    fetchDetail();
  }, [runId]);

  const active = run !== null && isActiveStatus(run.status);

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (active) {
      pollRef.current = setInterval(fetchDetail, DETAIL_POLL_MS);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [active, runId]);

  if (run === null) {
    return (
      <div className="w-full px-4 py-4 flex items-center justify-between"
           style={panelStyle}>
        <span className="text-sm" style={soft}>
          {notFound ? "Run not found (it may have been deleted)." : "Loading run..."}
        </span>
        {notFound && (
          <Button variant="ghost" size="sm" onClick={onClose}>Close</Button>
        )}
      </div>
    );
  }

  const res = run.result;

  return (
    <div className="w-full flex flex-col gap-4 px-4 py-4" style={panelStyle}>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex flex-col">
          <span className="text-sm font-semibold">{run.label}</span>
          <span className="text-xs" style={soft}>
            {run.periodStart} → {run.periodEnd}
            {run.finishedAt
              ? ` · finished ${new Date(run.finishedAt).toLocaleString()}`
              : ""}
          </span>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>Close</Button>
      </div>

      {active && (
        <span className="text-sm" style={soft}>
          {run.phase || "queued"}... {run.progressPct.toFixed(0)}%
        </span>
      )}

      {run.status === "FAILED" && (
        <pre
          className="text-sm whitespace-pre-wrap px-3 py-2"
          style={{ ...panelStyle, color: "var(--tv-down)" }}
        >
          {run.error || "Run failed without an error message."}
        </pre>
      )}

      {run.status === "CANCELLED" && (
        <span className="text-sm" style={soft}>Run was cancelled.</span>
      )}

      {run.status === "DONE" && res && (
        <>
          <div className="flex items-stretch gap-4 flex-wrap">
            <SummaryCard arm="gated" s={res.summary.gated} />
            {res.summary.ungated && (
              <SummaryCard arm="ungated" s={res.summary.ungated} />
            )}
          </div>

          <EquityChart
            gated={res.equity_curve.gated}
            ungated={res.equity_curve.ungated}
          />

          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span
              className="px-2 py-1 rounded"
              style={{ border: "1px solid var(--tv-border)", ...soft }}
            >
              S5: {res.s5_resolution.n_ambiguous} ambiguous,{" "}
              {res.s5_resolution.n_flipped} flipped,{" "}
              {res.s5_resolution.n_unresolved} unresolved,{" "}
              {fmt(res.s5_resolution.pnl_delta_pts, 1)} pts
            </span>
            {res.kill_trips.length > 0 && (
              <span
                className="px-2 py-1 rounded"
                style={{ border: "1px solid var(--tv-border)", color: "var(--tv-down)" }}
              >
                kill-switch: {res.kill_trips.join(", ")}
              </span>
            )}
          </div>

          {Object.keys(res.per_strategy).length > 0 && (
            <>
              {/* Primary verdict: points are sizing-invariant, so this is the
                  table that decides whether live fidelity to sim held up. */}
              <div className="flex flex-col gap-2">
                <span className="text-xs uppercase tracking-wide" style={soft}>
                  Fidelity (points — sizing-invariant)
                </span>
                <div className="w-full overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr style={soft}>
                        <th className="text-left py-2 pr-4 font-normal">Strategy</th>
                        <th className="text-right py-2 pr-4 font-normal">Sim pts</th>
                        <th className="text-right py-2 pr-4 font-normal">Sim PF</th>
                        <th className="text-right py-2 pr-4 font-normal">Sim WR</th>
                        <th className="text-right py-2 pr-4 font-normal">Live pts</th>
                        <th className="text-right py-2 pr-4 font-normal">Live PF</th>
                        <th className="text-right py-2 pr-4 font-normal">Live WR</th>
                        <th className="text-right py-2 pr-4 font-normal">Δ pts</th>
                        <th className="text-right py-2 pr-4 font-normal">Δ WR</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(res.per_strategy).map(
                        ([name, e]: [string, PerStrategyEntry]) => (
                          <tr key={name}
                              style={{ borderTop: "1px solid var(--tv-border)" }}>
                            <td className="py-2 pr-4">{name}</td>
                            <PointsCells s={e.sim.points} />
                            {e.live === null ? emptyCells(3) : <PointsCells s={e.live.points} />}
                            <td className="py-2 pr-4 text-right tnum"
                                style={{
                                  color: e.delta ? pnlColor(e.delta.points.pnl_pts)
                                                 : "var(--tv-text-soft)",
                                }}>
                              {e.delta ? fmt(e.delta.points.pnl_pts, 1) : "—"}
                            </td>
                            <td className="py-2 pr-4 text-right tnum">
                              {e.delta ? `${fmt(e.delta.points.win_rate, 1)}%` : "—"}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Secondary: USD matched to an inferred live per-trade risk.
                  Only meaningful (and only present) once enough live losers
                  exist to infer that risk — otherwise show the reason. */}
              {res.live_risk_usd_inferred !== null ? (
                <div className="flex flex-col gap-2">
                  <span className="text-xs uppercase tracking-wide" style={soft}>
                    Money (matched to inferred live risk ${fmt(res.live_risk_usd_inferred)})
                  </span>
                  <div className="w-full overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr style={soft}>
                          <th className="text-left py-2 pr-4 font-normal">Strategy</th>
                          <th className="text-right py-2 pr-4 font-normal">Sim $</th>
                          <th className="text-right py-2 pr-4 font-normal">Sim n</th>
                          <th className="text-right py-2 pr-4 font-normal">Sim WR</th>
                          <th className="text-right py-2 pr-4 font-normal">Live $</th>
                          <th className="text-right py-2 pr-4 font-normal">Live n</th>
                          <th className="text-right py-2 pr-4 font-normal">Live WR</th>
                          <th className="text-right py-2 pr-4 font-normal">Δ $</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(res.per_strategy).map(
                          ([name, e]: [string, PerStrategyEntry]) => (
                            <tr key={name}
                                style={{ borderTop: "1px solid var(--tv-border)" }}>
                              <td className="py-2 pr-4">{name}</td>
                              <UsdCells s={e.sim.usd} />
                              {e.live === null ? emptyCells(3) : <UsdCells s={e.live.usd} />}
                              <td className="py-2 pr-4 text-right tnum"
                                  style={{
                                    color: e.delta?.usd ? pnlColor(e.delta.usd.pnl_usd)
                                                   : "var(--tv-text-soft)",
                                  }}>
                                {e.delta?.usd ? `$${fmt(e.delta.usd.pnl_usd)}` : "—"}
                              </td>
                            </tr>
                          )
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <span
                  className="px-2 py-1 rounded text-xs w-fit"
                  style={{ border: "1px solid var(--tv-border)", ...soft }}
                >
                  Money view unavailable —{" "}
                  {res.notes.find((n) => /risk/i.test(n))
                    ?? "live risk in USD could not be inferred (too few live losing trades)."}
                </span>
              )}

              {/* Per-strategy reconciliation: how many live signals were
                  generated vs actually placed (with reject reasons), against
                  the sim trade count for the same window. */}
              <div className="flex flex-col gap-2">
                <span className="text-xs uppercase tracking-wide" style={soft}>
                  Reconciliation (live signal generation vs sim)
                </span>
                <div className="w-full overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr style={soft}>
                        <th className="text-left py-2 pr-4 font-normal">Strategy</th>
                        <th className="text-left py-2 pr-4 font-normal">Live generated → placed</th>
                        <th className="text-left py-2 pr-4 font-normal">Rejected</th>
                        <th className="text-right py-2 pr-4 font-normal">Sim trades</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(res.per_strategy).map(
                        ([name, e]: [string, PerStrategyEntry]) => {
                          const r = e.reconciliation;
                          return (
                            <tr key={name}
                                style={{ borderTop: "1px solid var(--tv-border)" }}>
                              <td className="py-2 pr-4">{name}</td>
                              {r === "unavailable" ? (
                                <td className="py-2 pr-4" style={soft} colSpan={3}>
                                  reconciliation unavailable
                                </td>
                              ) : (
                                <>
                                  <td className="py-2 pr-4 tnum">
                                    {r.live_generated} → {r.live_placed}
                                  </td>
                                  <td className="py-2 pr-4 tnum" style={soft}>
                                    {fmtRejected(r.rejected)}
                                  </td>
                                  <td className="py-2 pr-4 text-right tnum">{r.sim_trades}</td>
                                </>
                              )}
                            </tr>
                          );
                        }
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {res.notes.length > 0 && (
            <div className="flex flex-col gap-1">
              {res.notes.map((n) => (
                <span key={n} className="text-xs" style={soft}>• {n}</span>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ResultsPanel;
