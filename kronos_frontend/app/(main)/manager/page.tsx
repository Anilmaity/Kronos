// React - Next default
import React from "react";
import { Metadata } from "next";

// Components
import ManagerPage from "./_components/main";

export const metadata: Metadata = {
  title: "Strategy Manager - Kronos",
  description: "Regime-aware strategy manager control panel",
};

const Manager = () => {
  return <ManagerPage />;
};

export default Manager;
