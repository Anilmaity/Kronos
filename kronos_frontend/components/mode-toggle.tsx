"use client";
import * as React from "react";
import { useTheme } from "next-themes";
import { FiMoon, FiSun } from "react-icons/fi";
import { Button } from "@/components/ui/button";

export function ModeToggle() {
  const { setTheme, theme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      style={{ width: 34, height: 34, padding: 0 }}
    >
      {theme === "dark" ? (
        <FiMoon size={15} style={{ color: "var(--tv-text-2)" }} />
      ) : (
        <FiSun size={15} style={{ color: "var(--tv-text-2)" }} />
      )}
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
