"use client";

import React, { useState } from "react";

import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { CANCEL_MANAGER_BACKTEST } from "@/GraphQL/managerBacktestControls";

import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

import { RunSummary, RunStatus, isActiveStatus } from "./types";

import { panelStyle } from "@/lib/tvStyles";

const STATUS_COLORS: Record<RunStatus, string> = {
  PENDING: "var(--tv-text-soft)",
  RUNNING: "var(--tv-accent)",
  DONE: "var(--tv-up)",
  FAILED: "var(--tv-down)",
  CANCELLED: "var(--tv-text-soft)",
};

interface Props {
  runs: RunSummary[];
  loading: boolean;
  loadFailed: boolean;
  selectedRunId: string | null;
  onSelect: (id: string) => void;
  onChanged: () => void;
}

const RunsTable = ({
  runs, loading, loadFailed, selectedRunId, onSelect, onChanged,
}: Props) => {
  const [cancelTarget, setCancelTarget] = useState<RunSummary | null>(null);

  const confirmCancel = () => {
    if (!cancelTarget) return;
    const run = cancelTarget;
    setCancelTarget(null);
    client
      .mutate({
        mutation: CANCEL_MANAGER_BACKTEST,
        variables: { runId: run.id },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        const { ok, error } = response.data.cancelManagerBacktest;
        if (ok) {
          toast.success(`Cancelled ${run.label}`);
        } else {
          toast.error(error ?? "Cancel failed");
        }
        onChanged();
      })
      .catch((err) => middleware(err));
  };

  return (
    <div className="w-full flex flex-col gap-2 px-4 py-4" style={panelStyle}>
      <span className="text-sm font-semibold">Runs</span>

      {loading && (
        <span className="text-sm" style={{ color: "var(--tv-text-soft)" }}>
          Loading runs...
        </span>
      )}
      {loadFailed && !loading && (
        <span className="text-sm" style={{ color: "var(--tv-down)" }}>
          Failed to load runs.
        </span>
      )}
      {!loading && !loadFailed && runs.length === 0 && (
        <span className="text-sm" style={{ color: "var(--tv-text-soft)" }}>
          No backtests yet - queue one above.
        </span>
      )}

      {runs.length > 0 && (
        <div className="w-full overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ color: "var(--tv-text-soft)" }}>
                <th className="text-left py-2 pr-4 font-normal">Label</th>
                <th className="text-left py-2 pr-4 font-normal">Period</th>
                <th className="text-left py-2 pr-4 font-normal">Status</th>
                <th className="text-left py-2 pr-4 font-normal">Progress</th>
                <th className="text-left py-2 pr-4 font-normal">Created</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.id}
                  onClick={() => onSelect(run.id)}
                  className="cursor-pointer"
                  style={{
                    borderTop: "1px solid var(--tv-border)",
                    background:
                      run.id === selectedRunId
                        ? "var(--tv-surface-2, rgba(255,255,255,0.03))"
                        : undefined,
                  }}
                >
                  <td className="py-2 pr-4">{run.label}</td>
                  <td className="py-2 pr-4 whitespace-nowrap">
                    {run.periodStart} → {run.periodEnd}
                  </td>
                  <td className="py-2 pr-4">
                    <span
                      className="font-semibold"
                      style={{ color: STATUS_COLORS[run.status] }}
                    >
                      {run.status}
                    </span>
                  </td>
                  <td className="py-2 pr-4 min-w-[140px]">
                    {isActiveStatus(run.status) ? (
                      <div className="flex flex-col gap-1">
                        <div
                          className="w-full h-1.5 rounded"
                          style={{ background: "var(--tv-border)" }}
                        >
                          <div
                            className="h-1.5 rounded"
                            style={{
                              width: `${run.progressPct}%`,
                              background: "var(--tv-accent)",
                            }}
                          />
                        </div>
                        <span
                          className="text-xs"
                          style={{ color: "var(--tv-text-soft)" }}
                        >
                          {run.phase || "queued"} ({run.progressPct.toFixed(0)}%)
                        </span>
                      </div>
                    ) : (
                      <span style={{ color: "var(--tv-text-soft)" }}>—</span>
                    )}
                  </td>
                  <td
                    className="py-2 pr-4 whitespace-nowrap"
                    style={{ color: "var(--tv-text-soft)" }}
                  >
                    {new Date(run.createdAt).toLocaleString()}
                  </td>
                  <td className="py-2 text-right">
                    {isActiveStatus(run.status) && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setCancelTarget(run);
                        }}
                      >
                        Cancel
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AlertDialog
        open={cancelTarget !== null}
        onOpenChange={(open) => !open && setCancelTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel backtest?</AlertDialogTitle>
            <AlertDialogDescription>
              {cancelTarget
                ? `"${cancelTarget.label}" will stop at the next progress checkpoint. This cannot be resumed.`
                : ""}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep running</AlertDialogCancel>
            <AlertDialogAction onClick={confirmCancel}>
              Cancel run
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default RunsTable;
