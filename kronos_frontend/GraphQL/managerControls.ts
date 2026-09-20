import { gql } from "@apollo/client";

// Full Strategy Manager tab state in one round trip:
// config + managed strategies + latest regime snapshot + recent actions.
export const STRATEGY_MANAGER_STATE = gql`
  query StrategyManagerState {
    managerConfig {
      id
      masterMode
      killSwitchLossUsd
      maxConcurrentPositions
      state
      modifiedAt
    }
    managedStrategies {
      id
      slot
      policyKey
      policyParams
      armMode
      liveEligible
      desiredActive
      lastReason
      lastEvaluatedAt
      strategyName
      todayPnl
      openPositions
      userStrategy {
        id
        name
        brokerName
        isActive
        deployed
      }
    }
    latestRegime(symbol: "XAU_USD") {
      id
      createdAt
      symbol
      d1Bias
      h4Bias
      volRegime
      trendRegime
      session
      marketClosed
      details
    }
    managerActions(limit: 50) {
      id
      createdAt
      action
      reason
      managedStrategy {
        id
        slot
        strategyName
      }
    }
  }
`;

// Regime snapshots over the last N hours (ascending), for the history strip.
export const REGIME_HISTORY = gql`
  query RegimeHistory($symbol: String, $hours: Int) {
    regimeHistory(symbol: $symbol, hours: $hours) {
      id
      createdAt
      d1Bias
      h4Bias
      volRegime
      trendRegime
      session
      marketClosed
    }
  }
`;

// Master switch: "ON" | "OFF".
export const SET_MANAGER_MODE = gql`
  mutation SetManagerMode($masterMode: String!) {
    SetManagerMode(masterMode: $masterMode) {
      Response
      ManagerConfig {
        id
        masterMode
        killSwitchLossUsd
        maxConcurrentPositions
        state
      }
    }
  }
`;

// Arm a managed strategy: "OFF" | "PAPER" | "LIVE".
// LIVE is rejected by the backend when the strategy is not live-eligible.
export const ARM_STRATEGY = gql`
  mutation ArmStrategy($managedStrategyId: String!, $armMode: String!) {
    ArmStrategy(managedStrategyId: $managedStrategyId, armMode: $armMode) {
      Response
      ManagedStrategy {
        id
        armMode
        liveEligible
      }
    }
  }
`;

// Kill-switch dollar amount and max concurrent open positions.
export const UPDATE_MANAGER_CONFIG = gql`
  mutation UpdateManagerConfig(
    $killSwitchLossUsd: Float
    $maxConcurrentPositions: Int
  ) {
    UpdateManagerConfig(
      killSwitchLossUsd: $killSwitchLossUsd
      maxConcurrentPositions: $maxConcurrentPositions
    ) {
      Response
      ManagerConfig {
        id
        masterMode
        killSwitchLossUsd
        maxConcurrentPositions
        state
      }
    }
  }
`;
