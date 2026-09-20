# Kronos UI Redesign — TradingView Theme

**Date:** 2026-07-02
**Repo:** kronos_frontend (Next.js 14 App Router, Tailwind, shadcn/ui)
**Status:** Approved by user (logo + theme validated visually in brainstorm session)

## Goal

Replace the "Alchemist's Codex" dark-academic gold/serif design with a faithful
TradingView-style system: neutral surfaces, one blue accent, teal/red market
colors, crisp sans-serif, light + dark themes with a toggle. New Kronos logo.

## Decisions (locked)

1. **Theme modes:** dark AND light, user toggle, dark default.
2. **Brand:** name stays **Kronos**; new mark = "K of candlesticks"
   (blue price bar + teal up-candle + red down-candle forming a K), new wordmark
   in the system sans stack.
3. **Fidelity:** faithful TradingView palette (exact hexes below), not a remix.
4. **Scope this phase:** core screens only — **/login (incl. OTP), /dashboard,
   /chart, /manager** — plus the shared shell (navbar, sidebar, toasts, dialogs).
   Remaining tabs (accounts, backtests, marketplace, signals, admin,
   accountprofile, settings, archive) inherit colors via the legacy bridge and
   get pixel passes later.
5. **Architecture:** token swap + semantic layer + legacy bridge (below).

## Color tokens

CSS variables on `:root[data-theme="dark"]` / `:root[data-theme="light"]`,
exposed to Tailwind as semantic names.

| Token          | Dark      | Light     | Role |
|----------------|-----------|-----------|------|
| `--bg`         | `#131722` | `#FFFFFF` | page background, chart canvas |
| `--surface`    | `#1E222D` | `#F0F3FA` | cards, nav, panels, stat tiles |
| `--surface-2`  | `#2A2E39` | `#E0E3EB` | hover states, wells, input bg |
| `--border`     | `#2A2E39` | `#E0E3EB` | all hairlines |
| `--text-1`     | `#D1D4DC` | `#131722` | headings, primary values |
| `--text-2`     | `#B2B5BE` | `#434651` | body |
| `--text-3`     | `#787B86` | `#6A6D78` | labels, metadata, disabled |
| `--accent`     | `#2962FF` | `#2962FF` | links, active tab, primary button, focus ring |
| `--accent-hover`| `#1E53E5`| `#1E53E5` | button hover |
| `--accent-soft`| `#2962FF22` | `#2962FF14` | active-tab pill, selected row |
| `--up`         | `#089981` | `#089981` | gains, up candles, buy |
| `--down`       | `#F23645` | `#F23645` | losses, down candles, sell |
| `--warn`       | `#FF9800` | `#FF9800` | paper-mode chips, warnings |

Tailwind config maps these 1:1: `bg`, `surface`, `surface-2`, `border`,
`text-1/2/3`, `accent`, `up`, `down`, `warn` (replacing the old
`myGreen1`/`myRed1`/gold utilities on core screens).

### Legacy bridge

`globals.css` re-points the old variables so untouched pages render in the new
palette without edits:

```css
--gold: var(--accent);      --gold-deep: var(--accent);
--gold-dim: var(--text-3);  --ink: var(--text-1);
--ink-muted: var(--text-2); --ink-faint: var(--text-3);
--bg-deep: var(--bg);       --bg-soft: var(--surface);
--bg-card: var(--surface);  --line: var(--border);
--line-faint: var(--border);
```

Ambient parchment glows, paper-grain overlays, and `ornament-rule` decorations
are removed globally (deleted from `globals.css` / `algorobos.css`), not bridged.
`text-market-up`/`text-market-down`/`text-myGreen1`/`text-myRed1` re-point to
`--up`/`--down`.

## Theme switching

- `next-themes` (already installed, keep `attribute="class"` to match Tailwind's
  `darkMode: ["class"]`), `defaultTheme="dark"`, no system preference (trader
  default is dark), persisted to localStorage. Light = `:root` defaults,
  dark = `.dark` overrides.
- Inline no-flash script comes free with next-themes' `ThemeProvider` in
  `app/layout.tsx`.
- Sun/moon icon toggle (lucide `Sun`/`Moon`) in the main navbar and on the
  login page's top-right corner.

## Typography

- Font stack everywhere on core screens:
  `-apple-system, 'Segoe UI', Roboto, Ubuntu, sans-serif` (no webfont download).
- Serif families (Cormorant Garamond, Libre Baskerville, IM Fell English) are
  removed from core screens; the `next/font` imports stay until the last legacy
  page is migrated, then get deleted.
- All numeric cells (prices, P&L, counts): `font-variant-numeric: tabular-nums`
  via a `.tnum` utility.
- Scale: page title 20/600, section heading 14/600, body 13/400, label
  11/500 uppercase +0.4px tracking, big stat value 20/700.

## Logo

- `components/logo.tsx`: inline SVG, props `size` and `withWordmark`.
  Mark: rounded-square tile, `#2962FF` price bar, `#089981` up candle with wick,
  `#F23645` down candle with wick, K-diagonals in `var(--text-1)` so the mark
  adapts to theme. Tile background transparent in-app (navbar), solid `--surface`
  on the favicon.
- Replace `public/logo.svg`; regenerate `app/favicon.ico` (or `icon.svg`) from
  the mark. Delete unused gold logo assets from `public/`.
- Wordmark: "KRONOS", 700 weight, +0.5px letter-spacing, `var(--text-1)`.

## Core screen treatments

**Shell (navbar + sidebar).** Navbar: `--surface`, bottom `--border` hairline,
logo + wordmark left, route tabs as text links (`--text-3`, active =
`--accent` text on `--accent-soft` pill), theme toggle + user menu right.
Sidebar: keeps its current structure and routes, restyled only — flat
`--surface`, icon+label rows, active row `--accent-soft` with `--accent` icon;
no gold rules or ornaments.

**Login/OTP.** Flat `--bg` page, single centered 360px `--surface` card
(1px `--border`, 8px radius): logo+wordmark, 13px inputs on `--surface-2`
with `--accent` focus ring, full-width `--accent` primary button, `--text-3`
helper links. OTP screen matches.

**Dashboard.** Stat cards row (Total P&L, Today, Open positions, Win rate) as
`--surface` tiles per the approved mockup; strategy and position tables:
36px rows, `--border` row hairlines, `--text-3` 11px uppercase column headers,
P&L values in `--up`/`--down`, status chips (Running/Paused/paper) as small
outlined pills; row hover `--surface-2`.

**Chart.** lightweight-charts options from tokens: background `--bg`, grid
lines `--border` at 50%, candles `--up`/`--down` (wicks same), crosshair +
watermark `--text-3`. Toolbar/selects restyled to `--surface-2` inputs.

**Manager.** Master bar, regime panel, strategy cards, action log keep their
layout but drop all gold/serif styling: panels = `--surface` + `--border`,
labels = 11px uppercase `--text-3`, regime chips = outlined pills (bias
bullish `--up` / bearish `--down`, vol LOW→gray HIGH→`--warn` EXTREME→`--down`,
session/trend neutral), arm-mode select = shadcn select on `--surface-2`,
kill-switch status Nominal `--up` / TRIPPED `--down`, 24h vol strip keeps its
bar heights but recolors (LOW `--text-3`, NORMAL `--up`, HIGH `--warn`,
EXTREME `--down`). "IM Fell English" italics replaced with regular
`--text-3` body text.

**shadcn/ui base (used by all of the above).** `components/ui/*` styles come
from the CSS variables shadcn already consumes — update the shadcn theme block
(`--background`, `--foreground`, `--primary`, `--destructive`, `--ring`, etc.)
to the new tokens in both modes; radius 6px. Toasts (sonner): `--surface`
background, `--border`, accent/`--down` icons.

## Chart/library theming

`utils/chartTheme.ts` exports `chartTheme(theme: "dark" | "light")` returning
the token hexes for: lightweight-charts (`layout`, `grid`, `candlestick`
colors), ApexCharts (`theme.mode`, `colors`, `grid.borderColor`), Recharts
(stroke/fill props). Components re-create charts on theme change (subscribe via
`useTheme()`).

## Out of scope this phase

- Pixel passes on the eight non-core tabs (they run on the legacy bridge).
- Marketing/landing pages under `app/website` and `(minimal)` routes beyond
  what the bridge recolors.
- Any backend or GraphQL change. No route/layout restructuring.

## Verification

- `npm run lint` and `npm run build` clean.
- Manual pass of the four core screens in BOTH themes at 1440px and 375px:
  no gold remnants, no serif remnants, contrast sane, toggle instant, charts
  recolor with theme.
- Legacy tabs spot-checked: readable, functional (styling roughness accepted).
- User approves locally (`npm run dev`) before any push to `main`
  (push = Netlify production deploy).

## Rollout

Single PR-sized change on a branch (`feat/tradingview-theme`); user reviews
locally; push to `main` only on explicit approval.
