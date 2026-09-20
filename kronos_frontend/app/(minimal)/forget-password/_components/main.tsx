// React - Next Default
"use client";
import React from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";

const Image = dynamic(() => import("next/image"), {
  ssr: false,
});

// Libs
import { toast } from "sonner";
import { FieldValues, SubmitHandler, useForm } from "react-hook-form";

// GraphQL
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";

// Components
import Input from "@/components/inputs/Input";
import { Button } from "@/components/ui/button";

const ForgetPasswordForm = () => {
  const theme = useTheme(); // for getting the current theme

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FieldValues>({
    defaultValues: {
      email: "",
    },
  }); // react-hook-form

  const [isLoading, setIsLoading] = React.useState(false); // local state to handle loading state

  const router = useRouter(); // for navigation

  const onSubmit: SubmitHandler<FieldValues> = (data, e) => {
    e?.preventDefault(); // prevent the default form submission behavior of the browser

    if (data.email === "") {
      return;
    } // if the email is empty, return

    setIsLoading(true); // set loading state to true

    client
      .mutate({
        mutation: gql`
          mutation forgetPassword($email: String!) {
            ForgetPassword(email: $email) {
              Response
            }
          }
        `,
        variables: {
          email: data.email,
        },
      })
      .then((res) => {
        toast.success("Email sent successfully");
        router.push("/login");
      }) // if the email is sent successfully, push the user to the login page
      .catch((err) => {
        toast.error(err.message);
      }) // if there is an error, show the error message
      .finally(() => {
        setIsLoading(false);
        reset();
      }); // send the email to the server
  };

  const imgSrc =
      theme.theme === "dark"
      ? "/illustrations/forgot-password-dark.png"
      : "/illustrations/forgot-password.png"; // get the image source based on the current theme

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
      <div className="flex-1 w-full max-w-[550px] h-full px-3 py-6 flex flex-col items-center justify-center gap-4">
        <div className="text-xl xs:text-2xl md:text-4xl w-full flex justify-center">
          Forget Password
        </div>
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col items-center justify-center w-full gap-3 max-w-[327px] md:max-w-[460px]"
        >
          <Input
            errors={errors}
            id="email"
            label="Email"
            register={register}
            required
            disabled={isLoading}
            // value={userData?.email}
          />
          <Button type="submit" className="w-full text-white ">
            {isLoading ? "Loading..." : "Reset Password"}
          </Button>
        </form>
        <Link
          href={"/login"}
          className="underline underline-offset-2 capitalize text-myBlue2"
        >
          Back To sign In
        </Link>
      </div>
    </div>
  );
};

export default ForgetPasswordForm;
