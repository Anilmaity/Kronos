//React-Next Default
import React from "react";
import { Metadata } from "next";

// Components
import VerifyAccountPage from "./_components/main";

export const metadata: Metadata = {
  title: "Verify Account",
  description: "Verify Account for Kronos",
};

const ForgetPassword = () => {
  return (
    <div className="min-h-screen w-full">
      <VerifyAccountPage />
    </div>
  );
};

export default ForgetPassword;
