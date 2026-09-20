// React - Next default
import React from "react";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Login — Kronos",
  description: "Sign in to Kronos ICT/SMC trading platform",
};

const LoginLayout = ({ children }: { children: React.ReactNode }) => {
  return children;
};

export default LoginLayout;
