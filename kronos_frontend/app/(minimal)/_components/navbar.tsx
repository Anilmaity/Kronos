// React - Next default
"use client";
import React from "react";

// Components
import Logo from "@/components/logo";
import { ModeToggle } from "@/components/mode-toggle";

const Navbar = () => {
  return (
    <div className="h-[100px] flex w-full items-center justify-between bg-tableBg1 sticky top-0 z-50">
      <div className="px-8 md:px-14 py-5">
        <Logo />
      </div>
      <div className="px-8 md:px-14 py-5 flex items-center gap-4">
        <ModeToggle />
      </div>
    </div>
  );
};

export default Navbar;
