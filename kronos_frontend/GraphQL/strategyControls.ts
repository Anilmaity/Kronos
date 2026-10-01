import { gql } from "@apollo/client";

// Pause / resume a user strategy. Sets UserStrategy.is_active.
export const CHANGE_STRATEGY_STATUS = gql`
  mutation ChangeStrategyStatus($userStrategyId: String!, $status: Boolean!) {
    ChangeStrategyStatus(userStrategyId: $userStrategyId, status: $status) {
      Response
    }
  }
`;

// Position-size multiplier for future entries. Sets UserStrategy.multiplyer.
export const SET_USER_STRATEGY_MULTIPLIER = gql`
  mutation SetUserStrategyMultiplier($userStrategyId: String!, $multiplier: Int!) {
    SetUserStrategyMultiplier(userStrategyId: $userStrategyId, multiplier: $multiplier) {
      Response
    }
  }
`;

// Stop / flatten: close all open positions for the strategy.
export const EXIT_STRATEGY = gql`
  mutation ExitStrategy($strategyId: String!, $brokerCredId: String!) {
    ExitStrategy(strategyId: $strategyId, brokerCredId: $brokerCredId) {
      Response
      Ok
    }
  }
`;

// Delete a user strategy.
export const DELETE_USER_STRATEGY = gql`
  mutation DeleteUserStrategy($id: String!) {
    DeleteUserStrategy(id: $id) {
      Response
    }
  }
`;

// Archive a user strategy: auto-stops it and hides it from the dashboard.
// Blocked by the backend when an open position exists.
export const ARCHIVE_STRATEGY = gql`
  mutation ArchiveStrategy($userStrategyId: String!) {
    ArchiveStrategy(userStrategyId: $userStrategyId) {
      Response
    }
  }
`;

// Restore an archived strategy back to the dashboard (does not redeploy).
export const UNARCHIVE_STRATEGY = gql`
  mutation UnarchiveStrategy($userStrategyId: String!) {
    UnarchiveStrategy(userStrategyId: $userStrategyId) {
      Response
    }
  }
`;

// List the current user's archived strategies (for the Archive tab).
export const GET_ARCHIVED_STRATEGIES = gql`
  query ArchivedStrategies {
    archivedStrategies {
      id
      name
      brokerName
      multiplyer
      isActive
      createdAt
      totalProfitLoss
      totalPositionCount
      strategy {
        id
        name
      }
    }
  }
`;

// ── Telegram copy-trade tabs (Neymar / Neymar VIP) ─────────────────────────────
// Add a broker account to a copy-trade tab at a fixed total lot per signal.
export const ADD_COPY_TRADE_ACCOUNT = gql`
  mutation AddCopyTradeAccount(
    $source: String!
    $userBrokerId: String!
    $lotSize: Float!
    $tradeSlUsd: Float
    $maxSlPerTradeUsd: Float
    $dailyDdFloor: Float
    $maxDdFloor: Float
    $dailyDdOffset: Float
    $maxDdOffset: Float
  ) {
    AddCopyTradeAccount(
      source: $source
      userBrokerId: $userBrokerId
      lotSize: $lotSize
      tradeSlUsd: $tradeSlUsd
      maxSlPerTradeUsd: $maxSlPerTradeUsd
      dailyDdFloor: $dailyDdFloor
      maxDdFloor: $maxDdFloor
      dailyDdOffset: $dailyDdOffset
      maxDdOffset: $maxDdOffset
    ) {
      Ok
      Response
    }
  }
`;

// Change a copy-trade account's fixed total lot ("Price").
export const SET_COPY_TRADE_LOT = gql`
  mutation SetCopyTradeLot($userStrategyId: String!, $lotSize: Float!) {
    SetCopyTradeLot(userStrategyId: $userStrategyId, lotSize: $lotSize) {
      Ok
      Response
    }
  }
`;

// Accounts for the "Add Data" picker, with what each is already deployed to.
export const GET_COPY_TRADE_ACCOUNT_OPTIONS = gql`
  query GetCopyTradeAccountOptions {
    getuserdata {
      userbrokers {
        id
        label
        name
        accountHolderName
        metaAccountId
        hasToken
        isActive
        ddEquity
        userstrategys {
          id
          strategy {
            id
          }
        }
      }
    }
  }
`;

// Trade SL + the account's Daily / Max drawdown. Every field is sent; null clears it.
export const UPDATE_COPY_TRADE_RISK = gql`
  mutation UpdateCopyTradeRisk(
    $userStrategyId: String!
    $tradeSlUsd: Float
    $maxSlPerTradeUsd: Float
    $dailyDdFloor: Float
    $maxDdFloor: Float
    $dailyDdOffset: Float
    $maxDdOffset: Float
  ) {
    UpdateCopyTradeRisk(
      userStrategyId: $userStrategyId
      tradeSlUsd: $tradeSlUsd
      maxSlPerTradeUsd: $maxSlPerTradeUsd
      dailyDdFloor: $dailyDdFloor
      maxDdFloor: $maxDdFloor
      dailyDdOffset: $dailyDdOffset
      maxDdOffset: $maxDdOffset
    ) {
      Ok
      Response
    }
  }
`;

// Live equity + drawdown state per account (polled every few seconds on the Neymar tabs).
export const GET_COPY_TRADE_EQUITY = gql`
  query GetCopyTradeEquity {
    getuserdata {
      userbrokers {
        id
        ddEquity
        ddEquityAt
        ddStatus
        ddBlockedDay
        dailyDdFloor
        maxDdFloor
      }
    }
  }
`;
