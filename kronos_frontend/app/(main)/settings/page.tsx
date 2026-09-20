// React - Next default
import React from "react";
import { Metadata } from "next";

// Components
import SettingsPage from "./_components/main";

export const metadata: Metadata = {
  title: "Settings - Kronos",
  description: "Settings for Kronos",
};

export default function Settings() {
  return <SettingsPage />;
}
