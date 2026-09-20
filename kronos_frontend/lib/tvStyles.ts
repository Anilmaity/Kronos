// Shared inline-style constants for the tv-token design system.
// Extracted after Pixel Pass C — the single source for converted pages.
// Chips are CSS classes (.tv-chip in globals.css), not consts: hover
// states need real selectors.
import type { CSSProperties } from "react";

export const panelStyle: CSSProperties = {
  background: "var(--tv-surface)",
  border: "1px solid var(--tv-border)",
  borderRadius: "8px",
};

export const soft: CSSProperties = { color: "var(--tv-text-soft)" };

export const fieldStyle: CSSProperties = {
  background: "var(--tv-bg)",
  border: "1px solid var(--tv-border)",
  borderRadius: "6px",
  padding: "6px 10px",
  fontSize: "13px",
  color: "inherit",
};
