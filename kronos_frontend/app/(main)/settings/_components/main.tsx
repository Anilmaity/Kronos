// React - Next default
"use client";
import React from "react";

// Components
import ChangePassword from "./ChangePassword";

const SettingsPage = () => {
  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Settings</span>
        <span className="text-sm" style={{ color: "var(--tv-text-soft)" }}>
          Account security
        </span>
      </div>
      <ChangePassword />
    </div>
  );
};

export default SettingsPage;
