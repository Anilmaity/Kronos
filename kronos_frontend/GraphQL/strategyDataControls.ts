import { gql } from "@apollo/client";

// Backtest | Paper | Live trade list for one deployed strategy (/strategy-data).
export const STRATEGY_TRADES = gql`
  query StrategyTrades($userStrategyId: UUID!, $kind: String!, $year: Int!, $month: Int!) {
    strategyTrades(userStrategyId: $userStrategyId, kind: $kind, year: $year, month: $month) {
      kind
      status
      progressPct
      error
      periodStart
      periodEnd
      trades {
        entryTime
        exitTime
        side
        entryPrice
        exitPrice
        stopLoss
        takeProfit
        pnlUsd
        outcome
        note
      }
    }
  }
`;

// Registered under the CamelCase class name (auto-discovery convention).
export const RUN_STRATEGY_BACKTEST = gql`
  mutation RunStrategyBacktest($userStrategyId: UUID!) {
    runStrategyBacktest: RunStrategyBacktest(userStrategyId: $userStrategyId) {
      ok
      runId
      error
    }
  }
`;
