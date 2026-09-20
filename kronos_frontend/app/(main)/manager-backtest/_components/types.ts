export type RunStatus = "PENDING" | "RUNNING" | "DONE" | "FAILED" | "CANCELLED";

export interface RunSummary {
  id: string;
  label: string;
  status: RunStatus;
  progressPct: number;
  phase: string;
  periodStart: string;
  periodEnd: string;
  createdAt: string;
}

export interface ArmSummary {
  pnl_pts: number;
  pnl_usd: number;
  trades: number;
  win_rate: number;
  max_dd_pts: number;
  profit_factor: number | null;
}

// Points are sizing-invariant (the primary fidelity signal); USD is matched
// to an inferred live risk-per-trade and is only present when that inference
// succeeded (see live_risk_usd_inferred on RunResult).
export interface PointsStats {
  pnl_pts: number;
  trades: number;
  win_rate: number;
  profit_factor: number | null;
}

export interface UsdStats {
  pnl_usd: number;
  trades: number;
  win_rate: number;
}

export interface DeltaStats {
  points: { pnl_pts: number; trades: number; win_rate: number };
  usd?: UsdStats;
}

export interface StrategyReconciliation {
  live_generated: number;
  live_placed: number;
  rejected: Record<string, number>;
  sim_trades: number;
}

export interface PerStrategyEntry {
  sim: { points: PointsStats; usd?: UsdStats };
  live: { points: PointsStats; usd?: UsdStats } | null;
  delta: DeltaStats | null;
  reconciliation: StrategyReconciliation | "unavailable";
}

export interface RunResult {
  summary: { gated: ArmSummary; ungated?: ArmSummary };
  per_strategy: Record<string, PerStrategyEntry>;
  equity_curve: { gated: [string, number][]; ungated?: [string, number][] };
  s5_resolution: {
    n_ambiguous: number;
    n_flipped: number;
    n_unresolved: number;
    pnl_delta_pts: number;
  };
  trades_csv: string;
  notes: string[];
  kill_trips: string[];
  paused_pct: Record<string, number>;
  live_risk_usd_inferred: number | null;
}

export interface RunDetail extends RunSummary {
  params: Record<string, unknown>;
  result: RunResult | null;
  error: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export const isActiveStatus = (s: RunStatus) =>
  s === "PENDING" || s === "RUNNING";
