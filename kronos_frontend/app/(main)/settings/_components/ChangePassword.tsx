// React - Next default
import React from "react";

// Libs
import { FieldValues, SubmitHandler, useForm } from "react-hook-form";
import { toast } from "sonner";

// GraphQL
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";

// Components
import { Button } from "@/components/ui/button";
import PasswordInput from "@/components/inputs/PasswordInput";
import { middleware } from "@/GraphQL/middleware";
import { STORAGE_KEYS } from "@/lib/storage";

const ChangePassword = () => {
  const [isLoading, setIsLoading] = React.useState(false);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FieldValues>({
    defaultValues: {
      currentPassword: "",
      newPassword1: "",
      newPassword2: "",
    },
  }); // useForm is a hook that returns a set of methods to handle form state and validation

  const user = localStorage.getItem(STORAGE_KEYS.userEmail);

  const onSubmit: SubmitHandler<FieldValues> = (data, e) => {
    e?.preventDefault();

    if (data.password === "") {
      toast.error("Please enter a password");
      return;
    }

    if (data.newPassword === "") {
      toast.error("Please enter a new password");
      return;
    }

    if (data.confirmNewPassword === "") {
      toast.error("Please confirm your new password");
      return;
    }

    if (data.newPassword1 !== data.newPassword2) {
      toast.error("New Passwords do not match");
      return;
    }

    setIsLoading(true);

    const mutation = gql`
      mutation {
        ChangePassword(
          password: "${data.currentPassword}"
          newPassword: "${data.newPassword1}"
          email: "${user}"
        ) {
          Response
        }
      }
    `;

    client
      .mutate({
        mutation,
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        if (response.data.ChangePassword.Response === "Success") {
          toast.success("Password Changed Successfully");
        } else {
          toast.error("Something went wrong in changing password");
        }
      })
      .catch((err) => {
        middleware(err);
      })
      .finally(() => {
        setIsLoading(false);
      });
    reset();
  };

  return (
    <div className="w-full h-full p-2 md:px-4 py-2 flex flex-col items-start justify-start gap-4 ">
      <div className="text-base font-semibold">Change Password</div>
      <div
        className="w-full px-2 py-4 md:p-6"
        style={{
          background: "var(--tv-surface)",
          border: "1px solid var(--tv-border)",
          borderRadius: "8px",
        }}
      >
        <form
          className="flex max-w-[460px] mx-auto flex-col items-center justify-center gap-6 w-full"
          onSubmit={handleSubmit(onSubmit)}
        >
          <PasswordInput
            errors={errors}
            id="currentPassword"
            label="Current Password"
            register={register}
            disabled={isLoading}
            required
          />
          <PasswordInput
            errors={errors}
            id="newPassword1"
            label="New Password"
            register={register}
            disabled={isLoading}
            required
          />
          <PasswordInput
            errors={errors}
            id="newPassword2"
            label="Re-Enter New Password"
            register={register}
            disabled={isLoading}
            required
          />
          <Button disabled={isLoading} className="w-full">
            Save
          </Button>
        </form>
      </div>
    </div>
  );
};

export default ChangePassword;
