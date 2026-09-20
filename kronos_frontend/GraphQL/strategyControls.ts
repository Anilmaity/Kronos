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
