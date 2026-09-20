import React from "react";
import { Metadata } from "next";

import BacktestReportsPage from "./_components/main";

export const metadata: Metadata = {
  title: "Backtests - Kronos",
  description: "Backtest reports for live trading strategies",
};

const Backtests = () => {
  return <BacktestReportsPage />;
};

export default Backtests;
