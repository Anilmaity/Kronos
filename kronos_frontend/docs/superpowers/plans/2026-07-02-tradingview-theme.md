# TradingView Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the jade/gold "Alchemist's Codex" theme with a faithful TradingView design system (dark + light, toggle, new logo) on the shell, login, dashboard, chart, and manager screens.

**Architecture:** All colors flow from CSS variables (`--tv-*` for direct use, shadcn HSL vars for `components/ui`). Tailwind's existing utility names (`text-ink`, `bg-card`, `gold`, `market-up`, `myGreen1`…) are re-pointed at the new palette so untouched pages inherit it (legacy bridge). Core screens are then hand-restyled. Charts read colors from one `chartTheme()` helper.

**Tech Stack:** Next.js 14 App Router, Tailwind, shadcn/ui, next-themes 0.2.1 (already installed, class-based), lucide-react, lightweight-charts/ApexCharts.

**Spec:** `docs/superpowers/specs/2026-07-02-tradingview-ui-redesign-design.md`

## Global Constraints

- Palette (exact, from spec): dark `--bg #131722`, `--surface #1E222D`, `--surface-2/border #2A2E39`, text `#D1D4DC/#B2B5BE/#787B86`; light `--bg #FFFFFF`, `--surface #F0F3FA`, `--surface-2/border #E0E3EB`, text `#131722/#434651/#6A6D78`; both: accent `#2962FF` (hover `#1E53E5`), up `#089981`, down `#F23645`, warn `#FF9800`.
- Font: `-apple-system, 'Segoe UI', Roboto, Ubuntu, sans-serif`. No serif on core screens. Numbers get `tabular-nums`.
- Theme mechanism: KEEP next-themes with `attribute="class"` (`.dark` class, matches Tailwind `darkMode: ["class"]`). Light = `:root` defaults, dark = `.dark` overrides. Default dark, `enableSystem` removed.
- This repo has NO test framework. Every task verifies with `npm run lint` + `npm run build` + stated grep checks; visual checks happen in `npm run dev`.
- Work on branch `feat/tradingview-theme`. NEVER push to `main` (push = Netlify production deploy).
- Windows repo — run npm/git from `E:\Projects\Kronos\kronos_frontend`.

---

### Task 0: Branch

- [ ] **Step 0.1:** `git checkout -b feat/tradingview-theme` (from `main`). Expected: `Switched to a new branch`.

---

### Task 1: Token foundation (globals.css + tailwind.config.ts)

**Files:**
- Modify: `app/globals.css` (lines 25–199: token blocks, body, scrollbar, autofill; delete paper-grain `body::before` at 239–251 and green gradients at 293–314)
- Modify: `tailwind.config.ts` (colors, fontFamily, borderRadius, boxShadow)

**Interfaces:**
- Produces CSS vars every later task uses: `--tv-bg, --tv-surface, --tv-surface-2, --tv-border, --tv-text-1, --tv-text-2, --tv-text-3, --tv-accent, --tv-accent-hover, --tv-accent-soft, --tv-up, --tv-down, --tv-warn`.
- Produces Tailwind utilities: `bg-bg`, `bg-surface`, `bg-surface-2`, `border-line`, `text-ink`, `text-ink-muted`, `text-ink-faint`, `text-accent`, `bg-accent`, `text-up`, `text-down`, `text-warn`, `.tnum` (CSS utility class).
- Legacy names that must still resolve: `gold`, `ink`, `bg.card/soft/deep`, `market.up/down`, `myGreen1/myRed1/myGray1...` and CSS vars `--gold, --ink, --ink-muted, --ink-faint, --bg-card, --line, --line-faint, --market-up, --market-down`.

- [ ] **Step 1.1: Replace the token sections of `app/globals.css`.** Replace lines 25–147 (`:root` custom tokens, `.light`, shadcn `@layer base` blocks) with:

```css
/* ── TradingView Token System ─────────────────────────────── */
:root {
  /* light theme is the :root default; .dark overrides below */
  --tv-bg:            #FFFFFF;
  --tv-surface:       #F0F3FA;
  --tv-surface-2:     #E0E3EB;
  --tv-border:        #E0E3EB;
  --tv-text-1:        #131722;
  --tv-text-2:        #434651;
  --tv-text-3:        #6A6D78;
  --tv-accent:        #2962FF;
  --tv-accent-hover:  #1E53E5;
  --tv-accent-soft:   rgba(41, 98, 255, 0.08);
  --tv-up:            #089981;
  --tv-down:          #F23645;
  --tv-warn:          #FF9800;

  /* legacy bridge — old Algorobos names now resolve to the new palette */
  --gold:        var(--tv-accent);
  --gold-deep:   var(--tv-accent-hover);
  --gold-dim:    var(--tv-text-3);
  --bg-deep:     var(--tv-bg);
  --bg:          var(--tv-bg);
  --bg-soft:     var(--tv-surface);
  --bg-card:     var(--tv-surface);
  --ink:         var(--tv-text-1);
  --ink-muted:   var(--tv-text-2);
  --ink-faint:   var(--tv-text-3);
  --market-up:   var(--tv-up);
  --market-down: var(--tv-down);
  --line:        var(--tv-border);
  --line-faint:  var(--tv-border);

  /* legacy RGB triplets for rgba(var(--x)) utilities */
  --myBlue1:    41, 98, 255;
  --myBlue2:    30, 83, 229;
  --myCyan1:    41, 98, 255;
  --myPurple1:  41, 98, 255;
  --myPurple2:  30, 83, 229;
  --myText1:    19, 23, 34;
  --myGray1:    106, 109, 120;
  --myGray2:    106, 109, 120;
  --myGreen1:   8, 153, 129;
  --myRed1:     242, 54, 69;
  --myRed2:     242, 54, 69;
  --myYellow1:  255, 152, 0;
  --myYellow2:  255, 152, 0;
  --table-bg-1: 240, 243, 250;
  --main-bg:    255, 255, 255;
  --myPink1:    242, 54, 69;
  --myOrange1:  255, 152, 0;
}

.dark {
  --tv-bg:            #131722;
  --tv-surface:       #1E222D;
  --tv-surface-2:     #2A2E39;
  --tv-border:        #2A2E39;
  --tv-text-1:        #D1D4DC;
  --tv-text-2:        #B2B5BE;
  --tv-text-3:        #787B86;
  --tv-accent-soft:   rgba(41, 98, 255, 0.13);

  --myText1:    209, 212, 220;
  --myGray1:    120, 123, 134;
  --myGray2:    120, 123, 134;
  --table-bg-1: 30, 34, 45;
  --main-bg:    19, 23, 34;
}

/* ── Shadcn/ui HSL Variables (TradingView values) ─────────── */
@layer base {
  :root {
    --background: 0 0% 100%;            /* #FFFFFF */
    --foreground: 225 28% 10%;          /* #131722 */
    --card: 220 50% 96%;                /* #F0F3FA */
    --card-foreground: 225 28% 10%;
    --popover: 0 0% 100%;
    --popover-foreground: 225 28% 10%;
    --primary: 224 100% 58%;            /* #2962FF */
    --primary-foreground: 0 0% 100%;
    --secondary: 220 50% 96%;
    --secondary-foreground: 225 28% 10%;
    --muted: 220 22% 90%;               /* #E0E3EB */
    --muted-foreground: 227 6% 45%;     /* #6A6D78 */
    --accent: 220 50% 96%;
    --accent-foreground: 224 100% 58%;
    --destructive: 355 89% 58%;         /* #F23645 */
    --destructive-foreground: 0 0% 100%;
    --border: 220 22% 90%;
    --input: 220 22% 90%;
    --ring: 224 100% 58%;
    --radius: 0.375rem;                 /* 6px */
  }

  .dark {
    --background: 222 29% 10%;          /* #131722 */
    --foreground: 220 12% 84%;          /* #D1D4DC */
    --card: 220 20% 15%;                /* #1E222D */
    --card-foreground: 220 12% 84%;
    --popover: 220 20% 15%;
    --popover-foreground: 220 12% 84%;
    --primary: 224 100% 58%;
    --primary-foreground: 0 0% 100%;
    --secondary: 220 15% 20%;           /* #2A2E39 */
    --secondary-foreground: 220 12% 84%;
    --muted: 220 15% 20%;
    --muted-foreground: 225 5% 50%;     /* #787B86 */
    --accent: 220 15% 20%;
    --accent-foreground: 220 12% 84%;
    --destructive: 355 89% 58%;
    --destructive-foreground: 0 0% 100%;
    --border: 220 15% 20%;
    --input: 220 15% 20%;
    --ring: 224 100% 58%;
  }
}
```

- [ ] **Step 1.2: Replace the body/base block** (old lines 149–173) with:

```css
@layer base {
  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground;
    font-family: -apple-system, "Segoe UI", Roboto, Ubuntu, sans-serif;
    font-size: 14px;
    font-weight: 400;
    line-height: 1.5;
  }

  h1, h2, h3, h4, h5, h6 {
    font-family: inherit;
    letter-spacing: -0.01em;
    color: var(--tv-text-1);
    font-weight: 600;
  }
}

.tnum {
  font-variant-numeric: tabular-nums;
}
```

(The ambient `background-image` radial glows are deleted with this replacement.)

- [ ] **Step 1.3: Neutralize chrome CSS.** In the same file: scrollbar thumb `rgba(40,180,130,.30)` → `var(--tv-surface-2)` and hover `rgba(40,180,130,.55)` → `var(--tv-text-3)`; autofill block → `-webkit-box-shadow: 0 0 0px 1000px var(--tv-surface) inset; -webkit-text-fill-color: var(--tv-text-1); caret-color: var(--tv-accent);`. In `.ornament-rule::before/::after`, `rgba(40,180,130,.30)` → `var(--tv-border)` (legacy pages still render it, just neutral). Delete the entire `body::before` paper-grain rule and the `.gradient-01` / `.hero-gradient` / `.glassmorphism` green values → replace the three with accent-blue equivalents:

```css
.gradient-01 {
  background-image: linear-gradient(270deg, rgba(41,98,255,.35) 0%, rgba(30,83,229,.22) 50%, rgba(19,23,34,.15) 100%);
  filter: blur(125px);
}
.hero-gradient {
  background: linear-gradient(97.86deg, #1E53E5 0%, #2962FF 53.65%, #131722 100%);
}
.glassmorphism {
  background: rgba(30,34,45,.6);
  box-shadow: 0 8px 32px 0 rgba(41,98,255,.10);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--tv-border);
}
```

- [ ] **Step 1.4: Re-point Tailwind colors.** In `tailwind.config.ts` replace the `/* Algorobos Design Tokens */` block (lines 58–78) with:

```ts
        /* TradingView semantic tokens (legacy utility names kept, re-pointed) */
        gold: {
          DEFAULT: "var(--tv-accent)",
          deep:    "var(--tv-accent-hover)",
          dim:     "var(--tv-text-3)",
        },
        ink: {
          DEFAULT: "var(--tv-text-1)",
          muted:   "var(--tv-text-2)",
          faint:   "var(--tv-text-3)",
        },
        bg: {
          deep: "var(--tv-bg)",
          DEFAULT: "var(--tv-bg)",
          soft: "var(--tv-surface)",
          card: "var(--tv-surface)",
        },
        surface: {
          DEFAULT: "var(--tv-surface)",
          "2":     "var(--tv-surface-2)",
        },
        line:  "var(--tv-border)",
        up:    "var(--tv-up)",
        down:  "var(--tv-down)",
        warn:  "var(--tv-warn)",
        market: {
          up:   "var(--tv-up)",
          down: "var(--tv-down)",
        },
```

Also: `fontFamily` block → replace all four entries with

```ts
      fontFamily: {
        sans:    ["-apple-system", "'Segoe UI'", "Roboto", "Ubuntu", "sans-serif"],
        display: ["-apple-system", "'Segoe UI'", "Roboto", "Ubuntu", "sans-serif"],
        serif:   ["-apple-system", "'Segoe UI'", "Roboto", "Ubuntu", "sans-serif"],
        accent:  ["-apple-system", "'Segoe UI'", "Roboto", "Ubuntu", "sans-serif"],
        mono:    ["var(--font-mono)", "ui-monospace", "SF Mono", "Menlo", "monospace"],
      },
```

`borderRadius` → `lg: "8px", md: "6px", sm: "4px", DEFAULT: "6px"`. `boxShadow` gold entries → neutral: `gold: "0 4px 16px -8px rgba(0,0,0,.4)"`, `"gold-sm": "0 2px 8px -4px rgba(0,0,0,.3)"`, `"gold-glow": "none"`.

- [ ] **Step 1.5: Verify.** Run `npm run lint && npm run build`. Expected: clean build. Then `grep -n "rgba(40,180,130" app/globals.css` → no matches; `grep -n "34d18c" tailwind.config.ts` → no matches.

- [ ] **Step 1.6: Commit.** `git add app/globals.css tailwind.config.ts && git commit -m "feat(theme): TradingView token system + legacy bridge"`

---

### Task 2: Root layout — fonts, theme provider, toaster

**Files:**
- Modify: `app/layout.tsx`

**Interfaces:**
- Consumes tokens from Task 1. Produces the `<body>` with `font-sans` and mono var only; ThemeProvider stays `attribute="class"`, `defaultTheme="dark"`, NO `enableSystem`.

- [ ] **Step 2.1:** Replace the font imports and body class: remove `Cormorant_Garamond`, `Libre_Baskerville`, `IM_Fell_English` imports and their three `const` declarations (keep `JetBrains_Mono`). Body className becomes `` `${monoFont.variable} font-sans` ``. In `ThemeProvider`, delete the `enableSystem` prop. Replace the `Toaster` `toastOptions.style` with:

```tsx
            toastOptions={{
              style: {
                background: "var(--tv-surface)",
                border: "1px solid var(--tv-border)",
                color: "var(--tv-text-1)",
                fontSize: "13px",
              },
            }}
```

Update `metadata.description` stays; `icons` unchanged for now (Task 3 replaces the SVG file itself).

- [ ] **Step 2.2: Verify.** `npm run build` clean; `grep -n "Cormorant\|Baskerville\|IM_Fell" app/layout.tsx` → no matches. Legacy pages will fall back to sans via Tailwind's re-pointed `font-serif` — expected.

- [ ] **Step 2.3: Commit.** `git commit -am "feat(theme): system sans stack, dark-default provider, neutral toasts"`

---

### Task 3: Logo — component, public asset, favicon

**Files:**
- Rewrite: `components/logo.tsx`
- Replace: `public/logo.svg`
- Create: `app/icon.svg` (Next App Router favicon; then remove `icons` from `metadata` in `app/layout.tsx`)

**Interfaces:**
- Produces `<Logo size={number} withWordmark={boolean} />` (defaults `size=28`, `withWordmark=true`). K-diagonals use `currentColor` so the mark adapts to theme via the parent's text color.

- [ ] **Step 3.1: Rewrite `components/logo.tsx`:**

```tsx
import React from "react";

const KronosMark = ({ size = 28 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 48 48" aria-label="Kronos">
    <rect x="12" y="10" width="6" height="28" rx="1.5" fill="#2962FF" />
    <rect x="27" y="8" width="6" height="12" rx="1.5" fill="#089981" />
    <rect x="29.5" y="4" width="1" height="4" fill="#089981" />
    <rect x="27" y="28" width="6" height="12" rx="1.5" fill="#F23645" />
    <rect x="29.5" y="40" width="1" height="4" fill="#F23645" />
    <path
      d="M18 24 L27 13 M18 24 L27 35"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      fill="none"
    />
  </svg>
);

const Logo = ({
  size = 28,
  withWordmark = true,
}: {
  size?: number;
  withWordmark?: boolean;
}) => (
  <div
    className="flex items-center gap-2.5 select-none"
    style={{ color: "var(--tv-text-1)" }}
  >
    <KronosMark size={size} />
    {withWordmark && (
      <span
        className="font-sans"
        style={{ fontWeight: 700, fontSize: "1.05rem", letterSpacing: "0.03em" }}
      >
        KRONOS
      </span>
    )}
  </div>
);

export default Logo;
```

- [ ] **Step 3.2: Replace `public/logo.svg`** with the standalone mark (dark-surface tile so it works on any background):

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
  <rect width="48" height="48" rx="10" fill="#1E222D"/>
  <rect x="12" y="10" width="6" height="28" rx="1.5" fill="#2962FF"/>
  <rect x="27" y="8" width="6" height="12" rx="1.5" fill="#089981"/>
  <rect x="29.5" y="4" width="1" height="4" fill="#089981"/>
  <rect x="27" y="28" width="6" height="12" rx="1.5" fill="#F23645"/>
  <rect x="29.5" y="40" width="1" height="4" fill="#F23645"/>
  <path d="M18 24 L27 13 M18 24 L27 35" stroke="#D1D4DC" stroke-width="3" stroke-linecap="round" fill="none"/>
</svg>
```

- [ ] **Step 3.3:** Copy the same SVG content to `app/icon.svg`, and in `app/layout.tsx` delete the `icons:` entry from `metadata` (App Router picks up `app/icon.svg` automatically).

- [ ] **Step 3.4: Check old asset references.** `grep -rn "Antikythera" app components` — if only `components/logo.tsx` referenced it (now rewritten), leave the PNG file in place (other pages may use `/images/...`; deleting files is not required for the theme to work).

- [ ] **Step 3.5: Verify.** `npm run build` clean. In `npm run dev`, navbar shows mark + KRONOS wordmark in both themes (K legs flip color with theme).

- [ ] **Step 3.6: Commit.** `git add components/logo.tsx public/logo.svg app/icon.svg app/layout.tsx && git commit -m "feat(brand): candlestick-K logo, wordmark, favicon"`

---

### Task 4: Shell — navbar + sidebar

**Files:**
- Modify: `app/(main)/_components/navbar.tsx`
- Modify: `app/(main)/_components/sidebar.tsx`
- Check: `components/mode-toggle.tsx` (already exists and is rendered in the navbar — restyle only if it hardcodes greens)

**Interfaces:**
- Consumes `Logo` from Task 3 and tokens from Task 1. No API changes; purely presentational.

- [ ] **Step 4.1: Navbar.** In `navbar.tsx` replace the container `style` with `{ background: "var(--tv-surface)", borderBottom: "1px solid var(--tv-border)" }` (drop the blur), height `h-[56px]`, and `<Logo size={26} />`. Mobile dropdown panel style → `{ background: "var(--tv-surface)", border: "1px solid var(--tv-border)", boxShadow: "0 8px 24px rgba(0,0,0,.35)", borderRadius: "6px" }`. Each mobile link style →

```tsx
                  style={{
                    fontSize: "13px",
                    fontWeight: 600,
                    borderRadius: "6px",
                    color: pathname.startsWith(link.path) ? "var(--tv-accent)" : "var(--tv-text-2)",
                    background: pathname.startsWith(link.path) ? "var(--tv-accent-soft)" : "transparent",
                  }}
```

(remove the mono font-family, letterSpacing, textTransform, borderLeft lines).

- [ ] **Step 4.2: Sidebar.** In `sidebar.tsx`: container border → `1px solid var(--tv-border)`, `top-[56px]`, `min-h-[calc(100vh-56px)]`. Link style →

```tsx
                style={{
                  paddingLeft: "20px",
                  paddingRight: "16px",
                  fontSize: "14px",
                  fontWeight: isActive ? 600 : 500,
                  borderRadius: "6px",
                  margin: "0 8px",
                  color: isActive ? "var(--tv-accent)" : "var(--tv-text-2)",
                  background: isActive ? "var(--tv-accent-soft)" : "transparent",
                }}
```

Delete the right-edge active bar `<div>` and the `◆ Kronos` footer block (replace with `<Logo size={20} withWordmark={false} />` wrapped in the same absolute container, opacity 0.5). Remove mono/uppercase/letterSpacing styles.

- [ ] **Step 4.3:** Open `components/mode-toggle.tsx`; if it contains hardcoded jade colors (`#34d18c`, `rgba(82,229,163…)`, `--gold`), swap them for `var(--tv-text-2)` icon color and `var(--tv-surface-2)` hover background. Keep its `useTheme()` logic untouched.

- [ ] **Step 4.4: Verify.** `npm run build`; dev-check both themes: 56px flat navbar, blue active pill in sidebar, no green edge bar. `grep -n "82,229,163" app/\(main\)/_components/navbar.tsx app/\(main\)/_components/sidebar.tsx` → no matches.

- [ ] **Step 4.5: Commit.** `git commit -am "feat(theme): TradingView shell (navbar + sidebar)"`

---

### Task 5: Login + OTP

**Files:**
- Modify: `app/(auth)/login/_components/loginForm.tsx`, `app/(auth)/login/_components/otpForm.tsx`, `app/(auth)/layout.tsx` (and `app/(auth)/login/page.tsx` if it carries styling)

**Interfaces:** presentational only; auth logic (Login mutation, localStorage token, AUTH_STEP) untouched.

- [ ] **Step 5.1:** Read the four files first. Apply this mapping everywhere in them (this is the standard mapping for ALL restyle tasks):

| Old | New |
|---|---|
| `var(--font-display)` / `var(--font-serif)` / `var(--font-accent)` + serif styles | delete (inherit sans) |
| `fontFamily: var(--font-mono)` on labels | delete; labels get `fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.4px", color: "var(--tv-text-3)"` |
| `rgba(82,229,163,.NN)` borders | `var(--tv-border)` |
| `background: rgba(20,16,6,.5)` / `#0d0d10` / `var(--bg-card)` | `var(--tv-surface)` |
| `color: var(--ink)` | `var(--tv-text-1)` |
| `color: var(--ink-muted)` | `var(--tv-text-2)` |
| `color: var(--ink-faint)` / `#4e3c0a` | `var(--tv-text-3)` |
| gold/jade CTA buttons | `background: var(--tv-accent)`, white text, `borderRadius: 6px`, hover `var(--tv-accent-hover)` |
| `borderRadius: "2px"` / `"1px"` | `"6px"` |
| ornament rules `<div className="ornament-rule">…` | delete the element |
| `#34d18c` positive / `#b84c28` negative | `var(--tv-up)` / `var(--tv-down)` |

- [ ] **Step 5.2:** Structure the login card: page container `flex min-h-screen items-center justify-center` on `var(--tv-bg)`; card `width: 360px, background: var(--tv-surface), border: 1px solid var(--tv-border), borderRadius: 8px, padding: 32px`, `<Logo />` centered at top, inputs as shadcn `Input` (they inherit Task 1 tokens), primary button full-width. Add the existing `<ModeToggle />` (`components/mode-toggle.tsx`) absolutely positioned top-right of the page (`position: absolute; top: 16px; right: 16px;`). OTP screen: same card, `input-otp` slots get `border: 1px solid var(--tv-border); border-radius: 6px;` and accent ring on focus.

- [ ] **Step 5.3: Verify.** `npm run build`; dev-check `/login` both themes including OTP step. `grep -rn "82,229,163\|font-display\|font-accent" app/\(auth\)` → no matches.

- [ ] **Step 5.4: Commit.** `git commit -am "feat(theme): TradingView login + OTP"`

---

### Task 6: Dashboard

**Files:**
- Modify: `app/(main)/dashboard/_components/main.tsx`, `StrategyTable.tsx`, `UserBrokerPositionTable.tsx`, plus any `_components/*.tsx` siblings that render stat cards.

**Interfaces:** GraphQL queries and Zustand stores untouched.

- [ ] **Step 6.1:** Read each file; apply the Task 5.1 mapping table.
- [ ] **Step 6.2:** Specific treatments: stat tiles → `background: var(--tv-surface); border: 1px solid var(--tv-border); borderRadius: 8px;` with 11px uppercase `--tv-text-3` label and 20px/700 `.tnum` value colored `var(--tv-up)`/`var(--tv-down)` when signed. Tables: header row 11px uppercase `--tv-text-3` with bottom `1px solid var(--tv-border)`; body rows 36px, hairline `var(--tv-border)`, hover `background: var(--tv-surface-2)`; all numeric cells add className `tnum`; P&L cells `var(--tv-up)`/`var(--tv-down)`. Status chips → `border: 1px solid; borderRadius: 4px; fontSize: 11px; padding: 2px 8px;` colored: Running `var(--tv-up)`, Paused `var(--tv-text-3)`, paper `var(--tv-warn)`.
- [ ] **Step 6.3:** Any ApexCharts/Recharts config in these files: set `grid.borderColor`/stroke props to `var(--tv-border)` equivalents via the `chartTheme` helper if hex is required (helper arrives in Task 7 — if Task 6 runs first, hardcode `#2A2E39`/`#E0E3EB` per theme via `useTheme()` and leave a `// TODO(chartTheme)` — then Task 7 Step 7.3 removes it; this is the ONLY allowed TODO and Task 7 deletes it).
- [ ] **Step 6.4: Verify.** `npm run build`; dev-check `/dashboard` both themes; `grep -rn "82,229,163\|IM Fell\|font-display" app/\(main\)/dashboard` → no matches.
- [ ] **Step 6.5: Commit.** `git commit -am "feat(theme): TradingView dashboard"`

---

### Task 7: Chart page + chartTheme helper

**Files:**
- Create: `utils/chartTheme.ts`
- Modify: `app/(main)/chart/**` components (read directory first: `ls app/(main)/chart`)

**Interfaces:**
- Produces `chartTheme(theme: "dark" | "light")` consumed by chart + dashboard:

```ts
export type ThemeName = "dark" | "light";

export interface ChartTheme {
  bg: string; surface: string; border: string;
  text1: string; text2: string; text3: string;
  accent: string; up: string; down: string; warn: string;
}

export function chartTheme(theme: ThemeName): ChartTheme {
  return theme === "dark"
    ? { bg: "#131722", surface: "#1E222D", border: "#2A2E39",
        text1: "#D1D4DC", text2: "#B2B5BE", text3: "#787B86",
        accent: "#2962FF", up: "#089981", down: "#F23645", warn: "#FF9800" }
    : { bg: "#FFFFFF", surface: "#F0F3FA", border: "#E0E3EB",
        text1: "#131722", text2: "#434651", text3: "#6A6D78",
        accent: "#2962FF", up: "#089981", down: "#F23645", warn: "#FF9800" };
}
```

- [ ] **Step 7.1:** Create `utils/chartTheme.ts` with the code above (complete file).
- [ ] **Step 7.2:** In the chart page component(s): `const { resolvedTheme } = useTheme(); const t = chartTheme(resolvedTheme === "light" ? "light" : "dark");` and feed lightweight-charts:

```ts
    layout: { background: { color: t.bg }, textColor: t.text3 },
    grid: { vertLines: { color: t.border }, horzLines: { color: t.border } },
    // candlestick series:
    upColor: t.up, downColor: t.down, wickUpColor: t.up, wickDownColor: t.down,
    borderVisible: false,
```

Re-create or `applyOptions` on the chart inside a `useEffect` keyed on `resolvedTheme`. Apply the Task 5.1 mapping to the page's toolbar/selects.
- [ ] **Step 7.3:** Replace any `// TODO(chartTheme)` left by Task 6 with `chartTheme()` usage. `grep -rn "TODO(chartTheme)" app` → must return nothing after this step.
- [ ] **Step 7.4: Verify.** `npm run build`; dev-check `/chart` both themes — candles teal/red, grid hairlines, no green. Toggling theme recolors the chart without reload.
- [ ] **Step 7.5: Commit.** `git commit -am "feat(theme): chartTheme helper + TradingView chart page"`

---

### Task 8: Manager

**Files:**
- Modify: `app/(main)/manager/_components/main.tsx`

**Interfaces:** GraphQL operations (`STRATEGY_MANAGER_STATE`, mutations) untouched.

- [ ] **Step 8.1:** Replace the four style constants at the top of the file:

```tsx
const labelStyle: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 500,
  letterSpacing: "0.4px",
  textTransform: "uppercase",
  color: "var(--tv-text-3)",
};

const panelStyle: React.CSSProperties = {
  background: "var(--tv-surface)",
  border: "1px solid var(--tv-border)",
  borderRadius: "8px",
};

const smallMono: React.CSSProperties = {
  fontSize: "11px",
  letterSpacing: "0.3px",
  textTransform: "uppercase",
  color: "var(--tv-text-3)",
};

const chipBase: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  borderRadius: "4px",
  padding: "3px 10px",
  border: "1px solid var(--tv-border)",
};
```

- [ ] **Step 8.2:** Recolor the helpers: `volColor` → LOW `#787B86`, NORMAL `#089981`, HIGH `#FF9800`, EXTREME `#F23645` (default `#787B86`). `actionColor` → START `#089981`, PAUSE `#FF9800`, KILL_SWITCH `#F23645`, default `#787B86`. In JSX: every `"#34d18c"`/`"#50ba60"` → `var(--tv-up)`; `"#b84c28"` → `var(--tv-down)`; `"#d1b334"` → `var(--tv-warn)`; `"#4e3c0a"` and `"var(--ink-faint)"` → `var(--tv-text-3)`; `"IM Fell English"` italic blocks → plain `fontSize: 13, color: "var(--tv-text-3)"` (remove fontFamily/fontStyle); `rgba(82,229,163,.NN)` borders → `var(--tv-border)`; `rgba(80,186,96,.5)` → `var(--tv-up)`; delete the two `ornament-rule` divs; `className="font-display text-lg"` → `className="text-base font-semibold"`; `text-myRed1`/`text-myGreen1` in `pnlCell` → `text-down`/`text-up`; add `tnum` class to the P&L span and Open-positions span.
- [ ] **Step 8.3: Verify.** `npm run build`; dev-check `/manager` both themes: surface panels, blue switch (shadcn tokens from Task 1), teal/amber/red chips. `grep -n "82,229,163\|IM Fell\|34d18c\|b84c28\|d1b334" app/\(main\)/manager/_components/main.tsx` → no matches.
- [ ] **Step 8.4: Commit.** `git commit -am "feat(theme): TradingView manager tab"`

---

### Task 9: Final sweep + verification

**Files:** none new — checks and fixes only.

- [ ] **Step 9.1:** Sweep for stragglers on core paths: `grep -rn "82,229,163\|34d18c\|Cormorant\|IM Fell\|ornament-rule" app/\(auth\) app/\(main\)/dashboard app/\(main\)/chart app/\(main\)/manager app/\(main\)/_components components/logo.tsx` → fix any hit with the Task 5.1 mapping.
- [ ] **Step 9.2:** `npm run lint && npm run build` — both clean.
- [ ] **Step 9.3:** Manual pass in `npm run dev`: the four core screens at 1440px and 375px, BOTH themes; toggle flips instantly incl. charts; legacy tabs (accounts, backtests, marketplace, signals, admin, settings, archive) open and are readable (rough styling accepted).
- [ ] **Step 9.4:** `git commit -am "chore(theme): final sweep"` (if the sweep changed anything).
- [ ] **Step 9.5:** STOP. Present to the user for local review (`npm run dev`). Do NOT merge to `main` or push — push deploys to production Netlify.
