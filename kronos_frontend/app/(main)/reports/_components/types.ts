export interface PnlDay {
  date: string; // "YYYY-MM-DD"
  pnlUsd: number;
  trades: number;
}

export interface PnlAccount {
  id: string;
  label: string;
  isActive: boolean;
}

export interface CalendarPayload {
  days: PnlDay[];
  monthPnlUsd: number;
  monthTrades: number;
  winDays: number;
  lossDays: number;
  accounts: PnlAccount[];
}
