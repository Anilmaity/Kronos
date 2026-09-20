import Logo from "@/components/logo";
import React from "react";
import { FieldValues, SubmitHandler, useForm } from "react-hook-form";
import { toast } from "sonner";
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";
import Input from "@/components/inputs/Input";
import PassWordInput from "@/components/inputs/PasswordInput";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { STORAGE_KEYS } from "@/lib/storage";

const LoginForm = () => {
  const [isLoading, setIsLoading] = React.useState(false);
  const router = useRouter();

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FieldValues>({
    defaultValues: { email: "", password: "" },
  });

  const onSubmit: SubmitHandler<FieldValues> = (data, e) => {
    setIsLoading(true);
    e?.preventDefault();

    const mutation = gql`
      mutation {
        Login(email: "${data.email}", password: "${data.password}") {
          Response token
        }
      }
    `;

    client
      .mutate({ mutation, fetchPolicy: "no-cache" })
      .then((res) => {
        if (res.data.Login.Response.includes("Success")) {
          localStorage.setItem(STORAGE_KEYS.userEmail, data.email);
          localStorage.setItem(STORAGE_KEYS.token, res.data.Login.token);
          toast.success("Login successful.");
          router.push("/dashboard");
        } else if (res.data.Login.Response === "Invalid Password") {
          toast.error("Invalid credentials");
        } else {
          toast.error(res.data.Login.Response);
        }
      })
      .catch((err) => toast.error(err.message))
      .finally(() => setIsLoading(false));
    reset();
  };

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Logo */}
      <div className="flex justify-center">
        <Logo />
      </div>

      {/* Heading */}
      <div className="flex flex-col items-center gap-2 text-center">
        <h2
          style={{
            fontSize: "22px",
            fontWeight: 600,
            color: "var(--tv-text-1)",
            letterSpacing: "-0.01em",
          }}
        >
          Welcome back
        </h2>
        <p
          style={{
            fontSize: "13px",
            color: "var(--tv-text-3)",
          }}
        >
          Enter your credentials to access Kronos
        </p>
      </div>

      {/* Form */}
      <div className="w-full">
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col w-full gap-4">
          <Input errors={errors} id="email" label="Email" register={register} required disabled={isLoading} />
          <PassWordInput errors={errors} id="password" label="Password" register={register} required disabled={isLoading} />

          <Button
            disabled={isLoading}
            className="w-full mt-2 h-[44px] text-[13px]"
            type="submit"
          >
            {isLoading ? "Authenticating…" : "Sign In"}
          </Button>
        </form>
      </div>

      <Link
        href="/forget-password"
        style={{
          fontSize: "11px",
          fontWeight: 500,
          textTransform: "uppercase" as const,
          letterSpacing: "0.4px",
          color: "var(--tv-text-3)",
          textDecoration: "underline",
          textUnderlineOffset: "4px",
        }}
      >
        Forgot password?
      </Link>
    </div>
  );
};

export default LoginForm;
