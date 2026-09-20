// React - Next default
import { Metadata } from "next";

// Libs
import ForgetPasswordForm from "./_components/main";

export const metadata: Metadata = {
  title: "Forget Password - Kronos",
  description: "Forget Password for Kronos",
};

const ForgetPassword = () => {
  return <ForgetPasswordForm />;
};

export default ForgetPassword;
