/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import React, { useCallback, useEffect, useState } from "react";

import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import {
  GET_ARCHIVED_STRATEGIES,
  UNARCHIVE_STRATEGY,
} from "@/GraphQL/strategyControls";

import { formatCapital } from "@/utils/FormatCapital";
import { panelStyle, soft } from "@/lib/tvStyles";

interface ArchivedStrategy {
  id: string;
  name: string;
  brokerName: string | null;
  multiplyer: number;
  isActive: boolean;
  createdAt: string;
  totalProfitLoss: number | null;
  totalPositionCount: number | null;
  strategy: { id: string; name: string } | null;
}

const plColor = (n: number): string =>
  n < 0 ? "var(--tv-down)" : n > 0 ? "var(--tv-up)" : "var(--tv-text-soft)";

const ArchivePage = () => {
  const [rows, setRows] = useState<ArchivedStrategy[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const { data } = await client.query({
        query: GET_ARCHIVED_STRATEGIES,
        fetchPolicy: "no-cache",
      });
      setRows(data.archivedStrategies ?? []);
    } catch (err) {
      middleware(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleUnarchive = (userStrategyId: string) => {
    client
      .mutate({
        mutation: UNARCHIVE_STRATEGY,
        variables: { userStrategyId },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        const message = response.data.UnarchiveStrategy.Response;
        if (message === "Success") {
          toast.success("Strategy Restored");
          fetchData();
        } else {
          toast.error(message);
        }
      })
      .catch((err) => {
        middleware(err);
      });
  };

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Archive</span>
        <span className="text-sm" style={soft}>
          Archived strategies — restore returns them to the dashboard (stopped)
        </span>
      </div>

      {loading && (
        <div
          className="w-full flex items-center justify-center px-4 py-16 text-sm"
          style={{ ...panelStyle, ...soft }}
        >
          Loading…
        </div>
      )}

      {!loading && rows.length === 0 && (
        <div
          className="w-full flex items-center justify-center px-4 py-16 text-sm"
          style={{ ...panelStyle, ...soft }}
        >
          Nothing archived
        </div>
      )}

      {!loading && rows.length > 0 && (
        <div className="w-full overflow-x-auto" style={panelStyle}>
          <div
            className="flex items-center w-full px-4 py-3 min-w-[900px] text-xs font-semibold uppercase tracking-wider"
            style={{ ...soft, borderBottom: "1px solid var(--tv-border)" }}
          >
            <div className="w-[24%]">Strategy</div>
            <div className="w-[16%]">Broker</div>
            <div className="w-[8%] text-end">Mult</div>
            <div className="w-[14%] text-end">Archived</div>
            <div className="w-[12%] text-end">P&amp;L</div>
            <div className="w-[10%] text-end">Positions</div>
            <div className="w-[16%] text-end">Actions</div>
          </div>

          {rows.map((row) => (
            <div
              key={row.id}
              className="flex items-center w-full px-4 py-3 min-w-[900px] text-sm"
              style={{ borderBottom: "1px solid var(--tv-border)" }}
            >
              <div className="w-[24%] truncate" title={row.name}>
                {row.name}
              </div>
              <div className="w-[16%] truncate text-xs" style={soft}>
                {row.brokerName || "—"}
              </div>
              <div className="w-[8%] text-end">{row.multiplyer}x</div>
              <div className="w-[14%] text-end text-xs" style={soft}>
                {row.createdAt ? row.createdAt.split("T")[0] : "—"}
              </div>
              <div
                className="w-[12%] text-end font-semibold"
                style={{ color: plColor(Number(row.totalProfitLoss ?? 0)) }}
              >
                {formatCapital(Number(Number(row.totalProfitLoss ?? 0).toFixed(2)))}
              </div>
              <div className="w-[10%] text-end">{row.totalPositionCount ?? 0}</div>
              <div className="w-[16%] flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => handleUnarchive(row.id)}
                  className="tv-chip tv-chip--up"
                >
                  Restore
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ArchivePage;
