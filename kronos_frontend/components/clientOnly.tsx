/* eslint-disable react-hooks/exhaustive-deps */
// React - Next default
"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { client } from "@/GraphQL/client";
import { gql } from "@apollo/client";
import { toast } from "sonner";
import { STORAGE_KEYS } from "@/lib/storage";

interface ClientOnlyProps {
  children: React.ReactNode;
}

const ClientOnly: React.FC<ClientOnlyProps> = ({ children }) => {
  const [hasMounted, setHasMounted] = useState(false);
  const router = useRouter();

  const verifyToken = () => {
    const token = localStorage.getItem(STORAGE_KEYS.token);
    if (token) {
      const mutation = gql`
        mutation {
          VerifyToken(token: "${token}"){
            success
          }
        }
      `;
      client
        .mutate({
          mutation: mutation,
          fetchPolicy: "no-cache",
        })
        .then((res) => {
          if (res.data.VerifyToken.success) {
            router.refresh();
          }
        })
        .catch((err) => {
          if (err.message === "Signature has expired") {
            localStorage.clear();
          } else {
            toast.error(err.message);
          }
        });
    }
  }

  useEffect(() => {
    if (
      localStorage.getItem(STORAGE_KEYS.token) === null ||
      localStorage.getItem(STORAGE_KEYS.userEmail) === null
    ) {
      router.push("/login");
    }
  }, [router]);

  useEffect(() => {
    verifyToken();
  }, [router]);

  useEffect(() => {
    setHasMounted(true);
  }, []); // useEffect is a hook that runs a function when a component is mounted or updated

  if (!hasMounted) {
    return null;
  } // if the component has not mounted, return null

  return children;
};

export default ClientOnly;
