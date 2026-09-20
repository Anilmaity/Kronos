/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";

// GraphQL
import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { MANAGER_BACKTEST_RUNS } from "@/GraphQL/managerBacktestControls";

// Components
import NewRunCard from "./NewRunCard";
import RunsTable from "./RunsTable";
import ResultsPanel from "./ResultsPanel";

import { RunSummary, isActiveStatus } from "./types";

const ACTIVE_POLL_MS = 10_000;
const IDLE_POLL_MS = 60_000;

const ManagerBacktestPage = () => {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      const { data } = await client.query({
        query: MANAGER_BACKTEST_RUNS,
        fetchPolicy: "no-cache",
      });
      setRuns(data.managerBacktestRuns ?? []);
      setLoadFailed(false);
    } catch (err) {
      setLoadFailed(true);
      middleware(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const hasActive = runs.some((r) => isActiveStatus(r.status));

  useEffect(() => {
    fetchRuns();
  }, []);

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(
      fetchRuns,
      hasActive ? ACTIVE_POLL_MS : IDLE_POLL_MS
    );
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [hasActive]);

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex items-center justify-between w-full gap-4 flex-wrap">
        <div className="flex flex-col">
          <span className="text-base font-semibold">Manager Backtest</span>
          <span className="text-sm" style={{ color: "var(--tv-text-soft)" }}>
            Historical audit: replay the manager&apos;s roster and gates over a
            past window, then compare against live.
          </span>
        </div>
      </div>

      <NewRunCard onQueued={fetchRuns} />

      <RunsTable
        runs={runs}
        loading={loading}
        loadFailed={loadFailed}
        selectedRunId={selectedRunId}
        onSelect={setSelectedRunId}
        onChanged={fetchRuns}
      />

      {selectedRunId && (
        <ResultsPanel
          runId={selectedRunId}
          onClose={() => setSelectedRunId(null)}
        />
      )}
    </div>
  );
};

export default ManagerBacktestPage;
