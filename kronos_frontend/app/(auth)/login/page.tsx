"use client";
import dynamic from "next/dynamic";
import React from "react";

const Login = dynamic(() => import("./_components/main"), {
  ssr: false,
});

const LoginPage = () => {
  return <Login />;
};

export default LoginPage;
