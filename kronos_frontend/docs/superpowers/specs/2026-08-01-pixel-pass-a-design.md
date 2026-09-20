# Pixel Pass A — Marketplace, Backtests, Archive → tv Redesign

**Date:** 2026-08-01
**Status:** Approved (brainstorm 2026-08-01)
**Repos touched:** kronos_frontend only — no backend change, no box deploy.
**Series:** Group A of the legacy-tab redesign (A: this spec; B: accounts +
accountprofile; C: admin + settings — each its own spec/plan/ship cycle).

## What

Full redesign of the three strategy-list screens — `/marketplace`, `/backtests`,
`/archive` — to the standard the reworked screens (Reports, Signals, Manager) set:
tv-token panels, header pattern, table treatment, shadcn controls, both themes.
Plus the shared fixes this first group carries: `components/Loader.tsx`,
`components/ui/card.tsx`, the navbar's last legacy seam, and deletion of stray
`*.tmp.*` sed-debris files.

## Why

These tabs still wear pre-TradingView styling (Alchemist parchment panels, IM
Fell serif, ornament dividers, myGreen/myYellow classes, bare unstyled cards) —
worst in light mode. The signals rework finished the pattern language; this
series applies it everywhere else.

## Hard constraints

- **Presentation only.** Queries, mutations, variables, handlers, and data flow
  stay byte-identical. No new GraphQL fields, no behavior changes (the only
  visible behavior difference allowed: nicer loading/error/empty states).
- **Zero legacy tokens** in `app/(main)/marketplace/`, `app/(main)/backtests/`,
  `app/(main)/archive/`, `components/Loader.tsx`, `components/ui/card.tsx`, and
  `app/(main)/_components/navbar.tsx` after this branch. Gate (same as signals):
  `grep -rnE -- "--ink|--gold|myGreen|myYellow|myRed|rgba\(82,229,163|rgba\(20,16,6|#4e3c0a|#50ba60|#b84c28|IM Fell|ornament-rule" <paths>` → no matches.
- Colors: money/win = `var(--tv-up)`, loss = `var(--tv-down)`, soft text =
  `var(--tv-text-soft)`, panels = `var(--tv-surface)` + `1px solid var(--tv-border)`
  + radius 8. No new hex constants.
- Branch `feat/pixel-pass-a` off main (59d6fc1). Never push `main` (Netlify ships).

## Shared frame (all three pages)

Header: `text-base font-semibold` title + one-line `--tv-text-soft` subtitle
(the Reports/Signals pattern — no mono uppercase letter-spaced titles, no `◆`).
States: loading = soft text in a tv panel (`px-4 py-16` centered); error = tv
panel with `var(--tv-down)` message; empty = tv panel with soft message.

## Per-screen design

### `/backtests` (`app/(main)/backtests/_components/main.tsx`)

- Header: "Backtest Reports" / subtitle "offline runs — points, not USD".
- One tv table (signals treatment: uppercase 12px soft header row, hairline
  `var(--tv-border)` row borders, `overflow-x-auto` with a min-width):
  Strategy · Run label · Period (`periodStart → periodEnd`, dates only) ·
  Trades · W/L (`wins/losses`) · Win % · PnL pts (`fmtSigned`, colored by
  `pnlColor` — both already imported) · Max DD · PF · Expectancy · Notes
  (truncated, full text in `title`).
- Empty state: "No backtest reports".

### `/archive` (`app/(main)/archive/_components/main.tsx`)

- Header: "Archive" / subtitle "archived strategies — restore returns them to
  the dashboard, stopped".
- tv table: Name · Broker · Multiplier · Archived (date from `createdAt`) ·
  P&L (`formatCapital`, `tv-up`/`tv-down` by sign, keep existing null → "—") ·
  Positions · Restore (chip-style button, `handleUnarchive` unchanged).
- Remove the `ornament-rule` divider and the "06 — Archive" label styling.
- Empty state: "Nothing archived".

### `/marketplace` (`app/(main)/marketplace/_components/MarketplaceManager.tsx`)

- Header: "Marketplace" / subtitle "deployable strategies".
- Warning banner restyles to a tv callout: `var(--tv-surface)` panel with a
  `var(--tv-accent)`-tinted left border (3px) and soft text — same copy.
- Strategy cards: tv panel per card (grid unchanged `md:grid-cols-2`), semibold
  name, soft description, soft small line `SYMBOL · Capital X`.
- Deploy flow keeps its exact logic (inline expand per card, account select
  with deployed accounts disabled, multiplier `min={1}`, same toasts):
  - Deploy / Confirm deploy → shadcn `Button` (default variant, `size="sm"`).
  - Cancel → shadcn `Button` `variant="ghost"` `size="sm"`.
  - Account picker + multiplier → native `<select>`/`<input>` restyled with tv
    tokens (border `var(--tv-border)`, background `var(--tv-bg)`, radius 6) —
    native select keeps the `disabled` option semantics with zero logic change.
- "No accounts yet" and "No strategies available" lines become soft tv text.

## Shared fixes (carried by this group)

- `components/Loader.tsx` — replace legacy tokens with tv equivalents (spinner
  border colors → `var(--tv-border)` / `var(--tv-accent)`).
- `components/ui/card.tsx` — replace legacy tokens with the tv-token classes the
  other reworked shadcn primitives use (match `components/ui/table.tsx` idiom).
- `app/(main)/_components/navbar.tsx` — the remaining `var(--ink-muted)`
  hamburger seam → `var(--tv-text-soft)`.
- Delete debris: `app/(main)/dashboard/_components/StrategyTable.tsx.tmp.*`,
  `app/globals.css.tmp.*`, `app/_components/algorobos/algorobos.css.tmp.*`
  (verify each is untracked or unreferenced junk before deleting; they are
  sed/editor artifacts from July sessions).

## Explicitly out of scope

- The legacy bridge in `globals.css` and legacy names in `tailwind.config.ts`
  stay (the landing page and Groups B/C still resolve through them). Bridge
  retirement is a candidate for after Group C.
- The marketing landing page (`app/_components/algorobos/`) — separate design
  system, untouched.
- Groups B (accounts, accountprofile) and C (admin, settings).
- Any sorting/filtering/features these pages don't have today (YAGNI).

## Testing & verification

- No unit-test story for these pages (no logic changes; pure JSX/styling) —
  gates are `npm run test` (suite stays 44 green — no test files touched),
  `npm run build`, and the legacy-token grep above.
- Browser walk on the dev server (logged in, port-3000 orphan check first —
  see Deploy Gotchas): each of the three tabs in dark AND light, exercising
  marketplace's deploy expand/cancel (no actual deploy confirm), archive's
  table render, backtests' table with real reports.
- Merge/push is a user decision (ships via Netlify).
