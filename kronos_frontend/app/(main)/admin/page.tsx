// React - Next default
import React from "react";
import { Metadata } from "next";

// Components
import SuperAdminPage from "./_components/main";

export const metadata: Metadata = {
  title: "Admin - Kronos",
  description: "Superadmin positions for Kronos",
};

const SuperAdmin = () => {
  return <SuperAdminPage />;
};

export default SuperAdmin;
