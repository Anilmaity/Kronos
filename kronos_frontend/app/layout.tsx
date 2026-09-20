// React-Next Default
import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";

// Global styles
import "./website_globals.css";
import "./globals.css";

// Libs
import { Toaster } from "sonner";

// Components
import { ThemeProvider } from "@/components/providers/theme-provider";

/* ── Typography ─────────────────────────────────────────── */
const monoFont = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Kronos",
  description: "Kronos — ICT/SMC XAUUSD Algorithmic Trading Bot",
};

export default function RootLayout({
  children,
}: {
  readonly children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${monoFont.variable} font-sans`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          disableTransitionOnChange
          storageKey="Kronos-theme"
        >
          {children}
          <Toaster
            expand={true}
            closeButton
            richColors
            toastOptions={{
              style: {
                background: "var(--tv-surface)",
                border: "1px solid var(--tv-border)",
                color: "var(--tv-text-1)",
                fontSize: "13px",
              },
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
