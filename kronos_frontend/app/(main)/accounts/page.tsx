import { Metadata } from "next";
import AccountsManager from "./_components/AccountsManager";

export const metadata: Metadata = {
  title: "Accounts - Kronos",
};

export default function AccountsPage() {
  return <AccountsManager />;
}
