import React from "react";
import { Metadata } from "next";

import SignalsPage from "./_components/main";

export const metadata: Metadata = {
  title: "Signals - Kronos",
  description: "Live strategy signals (fired / placed / rejected)",
};

const Signals = () => {
  return <SignalsPage />;
};

export default Signals;
