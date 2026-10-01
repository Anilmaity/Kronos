// React - Next default
import React from "react";
import { Metadata } from "next";

// Components
import DashboardPage from "../dashboard/_components/main";

export const metadata: Metadata = {
  title: "Neymar VIP — Kronos",
  description: "Neymar VIP Telegram copy-trade positions",
};

const NeymarVip = () => {
  return <DashboardPage label="03 — Neymar VIP" source="neymar-vip" />;
};

export default NeymarVip;
