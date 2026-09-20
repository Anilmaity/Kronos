"use client";

import React, { useEffect, useState } from "react";
import { gql } from "@apollo/client";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { fmtNum, fmtSigned, pnlColor } from "@/utils/format";
import { panelStyle, soft } from "@/lib/tvStyles";

interface BacktestReport {
  id: string;
  strategyId: string;
  strategyName: string;
  runLabel: string;
  periodStart: string | null;
  periodEnd: string | null;
  trades: number;
  wins: number;
  losses: number;
  winRatePct: string | null;
  pnlPts: string | null;
  maxDdPts: string | null;
  avgWinPts: string | null;
  avgLossPts: string | null;
  profitFactor: string | null;
  expectancyPts: string | null;
  sourceCsv: string | null;
  notes: string | null;
}

const QUERY = gql`
  query AllBacktestReport {
    allBacktestReport {
      id
      strategyId
      strategyName
      runLabel
      periodStart
      periodEnd
      trades
      wins
      losses
      winRatePct
      pnlPts
      maxDdPts
      avgWinPts
      avgLossPts
      profitFactor
      expectancyPts
      sourceCsv
      notes
    }
  }
`;


const BacktestReportsPage: React.FC = () => {
  const [reports, setReports] = useState<BacktestReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const { data } = await client.query({
        query: QUERY,
        fetchPolicy: "no-cache",
      });
      setReports(data?.allBacktestReport ?? []);
      setError(null);
    } catch (err: any) {
      middleware(err);
      setError(err?.message ?? "Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Backtest Reports</span>
        <span className="text-sm" style={soft}>
          {reports.length} offline runs — points, not USD
        </span>
      </div>

      {loading && (
        <div
          className="w-full flex items-center justify-center px-4 py-16 text-sm"
          style={{ ...panelStyle, ...soft }}
        >
          Loading reports…
        </div>
      )}

      {error && !loading && (
        <div
          className="w-full px-4 py-6 text-sm"
          style={{ ...panelStyle, color: "var(--tv-down)" }}
        >
          {error}
        </div>
      )}

      {!loading && !error && reports.length === 0 && (
        <div
          className="w-full flex items-center justify-center px-4 py-16 text-sm"
          style={{ ...panelStyle, ...soft }}
        >
          No backtest reports
        </div>
      )}

      {!loading && !error && reports.length > 0 && (
        <div className="w-full overflow-x-auto" style={panelStyle}>
          <div
            className="flex items-center w-full px-4 py-3 min-w-[1200px] text-xs font-semibold uppercase tracking-wider"
            style={{ ...soft, borderBottom: "1px solid var(--tv-border)" }}
          >
            <div className="w-[16%]">Strategy</div>
            <div className="w-[14%]">Run</div>
            <div className="w-[12%]">Period</div>
            <div className="w-[6%] text-end">Trades</div>
            <div className="w-[7%] text-end">W / L</div>
            <div className="w-[6%] text-end">Win %</div>
            <div className="w-[8%] text-end">PnL pts</div>
            <div className="w-[7%] text-end">Max DD</div>
            <div className="w-[5%] text-end">PF</div>
            <div className="w-[8%] text-end">E[R] pts</div>
            <div className="w-[11%] pl-3">Notes</div>
          </div>

          {reports.map((r) => (
            <div
              key={r.id}
              className="flex items-center w-full px-4 py-3 min-w-[1200px] text-sm"
              style={{ borderBottom: "1px solid var(--tv-border)" }}
            >
              <div className="w-[16%] truncate" title={r.strategyName}>
                {r.strategyName}
              </div>
              <div className="w-[14%] truncate text-xs" style={soft} title={r.runLabel}>
                {r.runLabel}
              </div>
              <div className="w-[12%] text-xs" style={soft}>
                {r.periodStart && r.periodEnd
                  ? `${r.periodStart} → ${r.periodEnd}`
                  : "—"}
              </div>
              <div className="w-[6%] text-end">{r.trades}</div>
              <div className="w-[7%] text-end text-xs" style={soft}>
                {r.wins}/{r.losses}
              </div>
              <div className="w-[6%] text-end">{fmtNum(r.winRatePct, 1)}</div>
              <div
                className="w-[8%] text-end font-semibold"
                style={{ color: pnlColor(r.pnlPts) }}
              >
                {fmtSigned(r.pnlPts, 2)}
              </div>
              <div className="w-[7%] text-end">{fmtNum(r.maxDdPts, 2)}</div>
              <div className="w-[5%] text-end">{fmtNum(r.profitFactor, 2)}</div>
              <div className="w-[8%] text-end">{fmtNum(r.expectancyPts, 4)}</div>
              <div className="w-[11%] pl-3 truncate text-xs" style={soft} title={r.notes ?? ""}>
                {r.notes ?? "—"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BacktestReportsPage;
