export type ThemeName = "dark" | "light";

export interface ChartTheme {
  bg: string; surface: string; border: string;
  text1: string; text2: string; text3: string;
  accent: string; up: string; down: string; warn: string;
}

// lightweight-charts needs concrete colors (no CSS vars). Keep these in step
// with the globals.css token values for each theme (2026-08 rework palette).
export function chartTheme(theme: ThemeName): ChartTheme {
  return theme === "dark"
    ? { bg: "#12151F", surface: "#1A1E29", border: "#262B38",
        text1: "#E3E6ED", text2: "#B4B8C2", text3: "#7C8090",
        accent: "#2962FF", up: "#089981", down: "#F23645", warn: "#FF9800" }
    : { bg: "#FFFFFF", surface: "#FAFAFC", border: "#E7E8EE",
        text1: "#16181D", text2: "#4B4F58", text3: "#85888F",
        accent: "#2962FF", up: "#089981", down: "#F23645", warn: "#FF9800" };
}
