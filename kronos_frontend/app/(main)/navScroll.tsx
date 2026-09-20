"use client";
// React - Next default
import React, { useEffect } from "react";

// components
import { usePathname } from "next/navigation";

const NavScroll = ({
  className,
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) => {
  const pathname = usePathname();
  useEffect(() => {
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: "smooth",
    });
  }, [pathname]);
  return <div className={`${className}`}>{children}</div>;
};

export default NavScroll;
