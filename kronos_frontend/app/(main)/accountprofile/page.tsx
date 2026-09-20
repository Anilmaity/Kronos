// React - Next Default
import { Metadata } from "next";

// Components
import ControllerPage from "./_components/main";

export const metadata: Metadata = {
  title: "Account Profile - Kronos",
  description: "Risk profiles and account controls for Kronos",
};

export default function Controller() {
  return <ControllerPage />;
}
