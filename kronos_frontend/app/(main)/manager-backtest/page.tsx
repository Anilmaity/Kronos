// React - Next default
import React from "react";
import { Metadata } from "next";

// Components
import ManagerBacktestPage from "./_components/main";

export const metadata: Metadata = {
  title: "Manager Backtest - Kronos",
  description: "Historical audit backtests of the Strategy Manager",
};

const ManagerBacktest = () => {
  return <ManagerBacktestPage />;
};

export default ManagerBacktest;
