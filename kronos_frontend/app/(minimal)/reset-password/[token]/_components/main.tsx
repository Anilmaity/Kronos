// react - next default
"use client";
import React from "react";
import { useTheme } from "next-themes";
import { usePathname, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
const Image = dynamic(() => import("next/image"), {
  ssr: false,
});

// libs
import { toast } from "sonner";
import { FieldValues, SubmitHandler, useForm } from "react-hook-form";

// GraphQL
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";

// Components
import { Button } from "@/components/ui/button";
import PasswordInput from "@/components/inputs/PasswordInput";

const ResetPasswordForm = () => {
  const router = useRouter();
  const [isLoading, setIsLoading] = React.useState(false);
  const path = usePathname();
  const token = path.replace("/reset-password/", "");
  const { theme } = useTheme();
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<FieldValues>({
    defaultValues: {
      password: "",
      confirmPassword: "",
    },
  }); // react-hook-form
  const onSubmit: SubmitHandler<FieldValues> = (data, e) => {
    e?.preventDefault();
    if (data.password === "") {
      toast.error("Please enter a password");
      return;
    } // if the password is empty, return

    if (data.confirmPassword === "") {
      toast.error("Please confirm your password");
      return;
    } // if the confirm password is empty, return

    if (data.password !== data.confirmPassword) {
      toast.error("Passwords do not match");
      return;
    } // if the password and confirm password do not match, return
    setIsLoading(true); // set loading state to true

    client
      .mutate({
        mutation: gql`
          mutation resetPassword($password: String!, $token: String!) {
            ResetPassword(password: $password, token: $token) {
              Response
            }
          }
        `,
        variables: {
          password: data.password,
          token: token,
        },
      })
      .then((res) => {
        if (res.data.ResetPassword.Response === "Invalid token.") {
          toast.error("Invalid Token");
          return;
        } // if the token is invalid, return

        if (res.data.ResetPassword.Response === "Token has expired") {
          toast.error("Token Expired");
          return;
        } // if the token has expired, return

        if (res.data.ResetPassword.Response === "Success") {
          toast.success("Password reset successfully");
          localStorage.clear();
          router.push("/login");
          reset();
        } else {
          toast.error("Something went wrong");
        } // if the password reset is successful, redirect to login page
      })
      .catch((err) => {
        console.log(err.message);
      }) // if there is an error, log the error
      .finally(() => {
        reset();
        setIsLoading(false);
      });
  }; // send the password to the server

  const imgSrc =
    theme === "dark"
      ? "/illustrations/reset-password-dark.gif"
      : "/illustrations/reset-password.gif"; // get the image source based on the current theme

  return (
    <div className="p-4 lg:p-6 xl:p-8 w-full min-h-[calc(100vh-200px)] h-full flex items-center justify-center lg:justify-between">
      <div className="h-full hidden lg:flex flex-col items-center w-full lg:max-w-[472px] xl:max-w-[676px]">
        <Image
          src={imgSrc}
          alt="forgetPasswordImage"
          className="rounded-2xl flex-1 aspect-square"
          width={676}
          height={10}
          style={{ width: "auto", height: "auto" }}
          priority={false}
        />
      </div>
      <div className="flex-1 w-full max-w-[550px] px-3 py-[100px] flex flex-col items-center justify-center gap-4">
        <div className="text-xl xs:text-2xl md:text-4xl w-full flex justify-center">
          Reset Password
        </div>
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col items-center justify-center w-full gap-3 max-w-[327px] md:max-w-[460px]"
        >
          <PasswordInput
            id="password"
            label="password"
            disabled={isLoading}
            register={register}
            errors={errors}
            required
          />
          <PasswordInput
            id="confirmPassword"
            label="confirm password"
            disabled={isLoading}
            register={register}
            errors={errors}
            required
          />

          <Button type="submit" className="w-full text-white ">
            {isLoading ? "Loading..." : "Change Password"}
          </Button>
        </form>
      </div>
    </div>
  );
};

export default ResetPasswordForm;
