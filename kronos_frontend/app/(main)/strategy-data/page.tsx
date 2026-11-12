import React from "react";
import { Metadata } from "next";

import StrategyDataPage from "./_components/main";

export const metadata: Metadata = {
  title: "Strategy data - Kronos",
  description: "Backtest, paper and live trade calendar for one strategy.",
};

const StrategyData = ({
  searchParams,
}: {
  searchParams: { us?: string; name?: string; view?: string };
}) => {
  // "use client" exports are opaque references here, so the tab list is repeated.
  const v = searchParams.view;
  const view = v === "paper" || v === "live" ? v : "backtest";
  return (
    <StrategyDataPage
      userStrategyId={searchParams.us ?? ""}
      name={searchParams.name ?? "Strategy"}
      initialView={view}
    />
  );
};

export default StrategyData;
