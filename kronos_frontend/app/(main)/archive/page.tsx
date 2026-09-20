// React - Next default
import React from "react";
import { Metadata } from "next";

// Components
import ArchivePage from "./_components/main";

export const metadata: Metadata = {
  title: "Archive - Kronos",
  description: "Archived strategies",
};

const Archive = () => {
  return <ArchivePage />;
};

export default Archive;
