import { gql } from "@apollo/client";

// Reports tab (2026-08-01 plan): per-account realized PnL calendar for a
// given month. Query fields are camelCase attributes on the ObjectType, so
// no CamelCase alias is needed here (that trick is only for mutations).

export const PNL_CALENDAR = gql`
  query PnlCalendar($year: Int!, $month: Int!, $userBrokerId: UUID) {
    pnlCalendar(year: $year, month: $month, userBrokerId: $userBrokerId) {
      days {
        date
        pnlUsd
        trades
      }
      monthPnlUsd
      monthTrades
      winDays
      lossDays
      accounts {
        id
        label
        isActive
      }
    }
  }
`;
