import { gql } from "@apollo/client";

// Manager Backtest tab (2026-07-31 plan): queue historical-audit runs of the
// Strategy Manager and poll their progress/results.

export const MANAGER_BACKTEST_RUNS = gql`
  query ManagerBacktestRuns {
    managerBacktestRuns {
      id
      label
      status
      progressPct
      phase
      periodStart
      periodEnd
      createdAt
    }
  }
`;

export const MANAGER_BACKTEST_RUN = gql`
  query ManagerBacktestRun($runId: UUID!) {
    managerBacktestRun(runId: $runId) {
      id
      label
      status
      progressPct
      phase
      periodStart
      periodEnd
      createdAt
      params
      result
      error
      startedAt
      finishedAt
    }
  }
`;

export const RUN_MANAGER_BACKTEST = gql`
  mutation RunManagerBacktest(
    $periodStart: Date!
    $periodEnd: Date!
    $label: String
    $spreadPts: Float
    $slippagePts: Float
    $lots: Float
    $killSwitchUsd: Float
    $maxConcurrent: Int
    $regimeCadenceMin: Int
    $includeUngated: Boolean
  ) {
    # Field is registered under the CamelCase class name (auto-discovery
    # convention — see DeleteUserBroker in accountControls); aliased back to
    # camelCase so response.data.runManagerBacktest stays natural.
    runManagerBacktest: RunManagerBacktest(
      periodStart: $periodStart
      periodEnd: $periodEnd
      label: $label
      spreadPts: $spreadPts
      slippagePts: $slippagePts
      lots: $lots
      killSwitchUsd: $killSwitchUsd
      maxConcurrent: $maxConcurrent
      regimeCadenceMin: $regimeCadenceMin
      includeUngated: $includeUngated
    ) {
      ok
      runId
      error
    }
  }
`;

export const CANCEL_MANAGER_BACKTEST = gql`
  mutation CancelManagerBacktest($runId: UUID!) {
    cancelManagerBacktest: CancelManagerBacktest(runId: $runId) {
      ok
      error
    }
  }
`;
