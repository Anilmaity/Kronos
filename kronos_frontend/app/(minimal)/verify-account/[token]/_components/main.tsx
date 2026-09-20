/* eslint-disable react-hooks/exhaustive-deps */
"use client";
//React - Next default
import React from "react";
import { usePathname, useRouter } from "next/navigation";

//GraphQL
import { client } from "@/GraphQL/client";
import { gql } from "@apollo/client";

//Libs
import { toast } from "sonner";

const VerifyAccountPage = () => {
  const router = useRouter();

  const [isLoading, setIsLoading] = React.useState(false);

  const path = usePathname();

  const token = path.replace("/verify-account/", "");

  // this should only run once when the component is mounted
  React.useEffect(() => {
    setIsLoading(true);

    client
      .mutate({
        mutation: gql`
          mutation verifyAccount($token: String!) {
            VerifyAccount(token: $token) {
              Response
            }
          }
        `,
        variables: {
          token: token,
        },
      })
      .then((res) => {
        if (res.data.VerifyAccount.Response === "Account Already Verified") {
          toast.success("Account Already Verified");
          router.push("/login");
        }

        if (res.data.VerifyAccount.Response === "Account Verified") {
          toast.success("Account Verified");
          router.push("/login");
        }
      }) // if the account is verified, redirect to login page
      .catch((err) => {
        toast.error("Something went wrong");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []); // send the token to the server

  return (
    <div className="w-full flex items-center justify-center h-full">
      <div className="max-w-[550px] w-full px-3 py-[100px]">
        <div className="mb-3">
          <div className="text-2xl xs:text-4xl">Verify Account</div>
        </div>
      </div>
    </div>
  );
};

export default VerifyAccountPage;
