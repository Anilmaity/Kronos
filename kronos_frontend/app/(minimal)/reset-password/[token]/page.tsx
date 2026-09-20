// React - Next default
import { Metadata } from "next";

// Components
import ResetPasswordForm from "./_components/main";

export const metadata: Metadata = {
  title: "Reset Password - Kronos",
  description: "Reset Password for Kronos",
};

const TokenResetPassword = () => {
  return <ResetPasswordForm />;
};

export default TokenResetPassword;
