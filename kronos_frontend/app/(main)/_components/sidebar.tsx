"use client";
import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUserData } from "@/hooks/useUserData";
import { sidebarLinkArray } from "./constants";
import Logo from "@/components/logo";

const Sidebar = () => {
  const { userData } = useUserData();
  const pathname = usePathname();

  const filteredSidebarLinks =
    userData && !userData.isSuperuser
      ? sidebarLinkArray.filter(
          (link) => link.path !== "/controller" && link.path !== "/superadmin"
        )
      : sidebarLinkArray;

  return (
    <div
      className="hidden lg:block lg:w-[240px] xl:w-[260px] min-h-[calc(100vh-56px)] pt-8 sticky top-[56px] flex-shrink-0"
      style={{ borderRight: "1px solid var(--tv-border)" }}
    >
      <div className="flex flex-col items-start gap-0.5">
        {filteredSidebarLinks.map((link) => {
          const isActive = pathname.startsWith(link.path);
          return (
            <div key={link.path} className="w-full relative">
              {isActive && (
                <span
                  aria-hidden
                  style={{
                    position: "absolute",
                    left: 0,
                    top: "50%",
                    transform: "translateY(-50%)",
                    width: "3px",
                    height: "22px",
                    borderRadius: "0 3px 3px 0",
                    background: "var(--tv-accent)",
                  }}
                />
              )}
              <Link
                href={link.path}
                className="flex items-center gap-3 py-3 transition-all hover:bg-secondary"
                style={{
                  paddingLeft: "20px",
                  paddingRight: "16px",
                  fontSize: "14px",
                  fontWeight: isActive ? 600 : 500,
                  borderRadius: "var(--tv-radius)",
                  margin: "0 8px",
                  width: "calc(100% - 16px)",
                  color: isActive ? "var(--tv-accent)" : "var(--tv-text-2)",
                  background: isActive ? "var(--tv-accent-soft)" : undefined,
                  transitionDuration: "var(--tv-dur-fast)",
                }}
              >
                <link.icon size={18} style={{ flexShrink: 0 }} />
                <span>{link.title}</span>
              </Link>
            </div>
          );
        })}
      </div>

      <div className="absolute bottom-8 left-0 w-full px-5">
        <div style={{ opacity: 0.5 }}>
          <Logo size={20} withWordmark={false} />
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
