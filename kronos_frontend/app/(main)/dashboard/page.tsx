// React - Next default
import React from "react";
import { Metadata } from "next";

// Components
import DashboardPage from "./_components/main";

export const metadata: Metadata = {
  title: "Dashboard — Kronos",
  description: "Dashboard for Kronos",
};

const Dashboard = () => {
  return <DashboardPage />;
};

export default Dashboard;
