// React - Next default
import React from "react";
import { Metadata } from "next";

// Components
import ReportsPage from "./_components/main";

export const metadata: Metadata = {
  title: "Reports - Kronos",
  description: "Realized PnL calendar per account.",
};

const Reports = () => {
  return <ReportsPage />;
};

export default Reports;
