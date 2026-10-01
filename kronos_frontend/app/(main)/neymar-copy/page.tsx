// React - Next default
import React from "react";
import { Metadata } from "next";

// Components
import DashboardPage from "../dashboard/_components/main";

export const metadata: Metadata = {
  title: "Neymar — Kronos",
  description: "Neymar Telegram copy-trade positions",
};

const NeymarCopy = () => {
  return <DashboardPage label="02 — Neymar" source="neymar" />;
};

export default NeymarCopy;
