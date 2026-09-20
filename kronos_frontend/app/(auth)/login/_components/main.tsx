/* eslint-disable react-hooks/exhaustive-deps */
"use client";
import React, { useEffect } from "react";
import { useRouter } from "next/navigation";

// GraphQL
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";

// Components
import LoginForm from "./loginForm";
import OTPForm from "./otpForm";
import { useAuthStep } from "@/hooks/useAuthStep";
import { ModeToggle } from "@/components/mode-toggle";
import { STORAGE_KEYS } from "@/lib/storage";

const Login = () => {
  const [isLoading, setIsLoading] = React.useState(false);
  const { step } = useAuthStep();
  const router = useRouter();

  useEffect(() => {
    const getUser = () => {
      const token = localStorage.getItem(STORAGE_KEYS.token);
      if (token) {
        const mutation = gql`
          mutation {
            VerifyToken(token: "${token}") { success }
          }
        `;
        client
          .mutate({ mutation, fetchPolicy: "no-cache" })
          .then((res) => {
            setIsLoading(true);
            if (res.data.VerifyToken.success) router.push("/dashboard");
            else localStorage.clear();
          })
          .catch(() => { localStorage.clear(); })
          .finally(() => { setIsLoading(false); });
      }
    };
    getUser();
  }, []);

  return (
    <div
      className="flex min-h-screen items-center justify-center relative"
      style={{ background: "var(--tv-bg)" }}
    >
      {/* Theme toggle — top-right */}
      <div style={{ position: "absolute", top: 16, right: 16 }}>
        <ModeToggle />
      </div>

      {/* Login card */}
      <div
        style={{
          width: 360,
          maxWidth: "calc(100vw - 32px)",
          background: "var(--tv-surface)",
          border: "1px solid var(--tv-border)",
          borderRadius: 8,
          padding: 32,
        }}
      >
        {step === "OTP" ? <OTPForm /> : <LoginForm />}
      </div>
    </div>
  );
};

export default Login;
