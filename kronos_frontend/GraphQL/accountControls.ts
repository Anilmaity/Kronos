import { gql } from "@apollo/client";

// Create a trading account (stores encrypted MetaAPI token).
export const ADD_ACCOUNT = gql`
  mutation AddAccount(
    $label: String!
    $metaAccountId: String!
    $metaApiToken: String!
  ) {
    AddAccount(
      label: $label
      metaAccountId: $metaAccountId
      metaApiToken: $metaApiToken
    ) {
      Response
      UserBroker {
        id
        label
        metaAccountId
        metaApiTokenLast4
        hasToken
      }
    }
  }
`;

// Update an account. Omit metaApiToken to keep the current token.
export const UPDATE_ACCOUNT = gql`
  mutation UpdateAccount(
    $id: String!
    $label: String
    $metaAccountId: String
    $metaApiToken: String
  ) {
    UpdateAccount(
      id: $id
      label: $label
      metaAccountId: $metaAccountId
      metaApiToken: $metaApiToken
    ) {
      Response
      UserBroker {
        id
        label
        metaAccountId
        metaApiTokenLast4
        hasToken
      }
    }
  }
`;

// Delete an account (user-scoped on the backend).
export const DELETE_USER_BROKER = gql`
  mutation DeleteUserBroker($brokerId: String!) {
    DeleteUserBroker(brokerId: $brokerId) {
      Response
    }
  }
`;

// Fetch the current user's accounts (reuses the existing getuserdata resolver).
export const GET_ACCOUNTS = gql`
  query GetAccounts {
    getuserdata {
      userbrokers {
        id
        label
        metaAccountId
        metaApiTokenLast4
        hasToken
        isActive
        status
      }
    }
  }
`;

// Per-account KPI + equity-curve analytics for the /accounts/[id] dashboard.
// fromDate/toDate are optional ISO "YYYY-MM-DD" strings; omit both for all-time.
export const GET_ACCOUNT_ANALYTICS = gql`
  query AccountAnalytics($userBrokerId: UUID!, $fromDate: Date, $toDate: Date) {
    accountAnalytics(userBrokerId: $userBrokerId, fromDate: $fromDate, toDate: $toDate) {
      id label metaAccountId isActive fromDate toDate
      kpis {
        netPnlUsd trades winRate profitFactor avgWinUsd avgLossUsd
        expectancyUsd maxDrawdownUsd bestDayUsd worstDayUsd avgTradesPerDay currentBalanceUsd
      }
      equityCurve { t equityUsd }
    }
  }
`;

export interface EquityPoint { t: string; equityUsd: number }
export interface AccountKpis {
  netPnlUsd: number; trades: number; winRate: number; profitFactor: number | null;
  avgWinUsd: number; avgLossUsd: number; expectancyUsd: number; maxDrawdownUsd: number;
  bestDayUsd: number; worstDayUsd: number; avgTradesPerDay: number; currentBalanceUsd: number;
}
export interface AccountAnalytics {
  id: string; label: string; metaAccountId: string; isActive: boolean;
  fromDate: string; toDate: string; kpis: AccountKpis; equityCurve: EquityPoint[];
}
