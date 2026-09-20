/* eslint-disable react-hooks/exhaustive-deps */
"use client";
import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { HiBars3BottomLeft, HiXMark } from "react-icons/hi2";
import { useNavbar } from "@/hooks/useNavbar";
import { useUserData } from "@/hooks/useUserData";
import Logo from "@/components/logo";
import { ModeToggle } from "@/components/mode-toggle";
import UserSection from "./userSection";
import { sidebarLinkArray } from "./constants";
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";

const Navbar = () => {
  const { isOpen, toggle } = useNavbar();
  const pathname = usePathname();
  const { setUserData, userData } = useUserData();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { data } = await client.query({
          query: gql`
            query {
              getuserdata {
                id firstName lastName isActive isStaff isSuperuser
              }
            }
          `,
          fetchPolicy: "no-cache",
        });
        setUserData(data.getuserdata);
      } catch (error) {
        console.error("Error fetching user data:", error);
      }
    };
    fetchData();
  }, []);

  const filteredSidebarLinks =
    userData && !userData.isSuperuser
      ? sidebarLinkArray.filter(
          (link) => link.path !== "/controller" && link.path !== "/superadmin"
        )
      : sidebarLinkArray;

  return (
    <div
      className="h-[56px] flex items-center justify-between sticky top-0 z-50 px-6 md:px-10 lg:px-14 w-full"
      style={{
        background: "color-mix(in srgb, var(--tv-surface) 82%, transparent)",
        backdropFilter: "saturate(1.6) blur(14px)",
        WebkitBackdropFilter: "saturate(1.6) blur(14px)",
        borderBottom: "1px solid var(--tv-border)",
      }}
    >
      {/* Mobile menu toggle */}
      <button
        onClick={toggle}
        className="block lg:hidden relative w-full cursor-pointer"
        style={{ color: "var(--tv-text-soft)" }}
      >
        {isOpen ? <HiXMark size={28} /> : <HiBars3BottomLeft size={28} />}

        {isOpen && (
          <div
            className="absolute top-14 -left-6 md:-left-10 z-50 p-3 flex flex-col gap-1 min-w-[240px]"
            style={{
              background: "var(--tv-surface)",
              border: "1px solid var(--tv-border)",
              boxShadow: "0 8px 24px rgba(0,0,0,.35)",
              borderRadius: "6px",
            }}
          >
            {filteredSidebarLinks.map((link) => (
              <div key={link.path} className="w-full relative">
                <Link
                  href={link.path}
                  className="w-full flex items-center gap-3 px-4 py-3 transition-all duration-200"
                  style={{
                    fontSize: "13px",
                    fontWeight: 600,
                    borderRadius: "6px",
                    color: pathname.startsWith(link.path) ? "var(--tv-accent)" : "var(--tv-text-2)",
                    background: pathname.startsWith(link.path) ? "var(--tv-accent-soft)" : "transparent",
                  }}
                >
                  <link.icon size={16} />
                  <span>{link.title}</span>
                </Link>
              </div>
            ))}
          </div>
        )}
      </button>

      {/* Logo */}
      <Link href="/dashboard" className="hidden sm:block w-full">
        <Logo size={26} />
      </Link>

      {/* Right controls */}
      <div className="flex items-center gap-3 w-full justify-end">
        <ModeToggle />
        <UserSection />
      </div>
    </div>
  );
};

export default Navbar;
