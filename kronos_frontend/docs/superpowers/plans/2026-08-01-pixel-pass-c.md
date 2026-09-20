# Pixel Pass C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** tv redesign of Settings + Admin, CryptoBot metadata sweep, `lib/tvStyles.ts` extraction, `.tv-chip` hover classes.

**Architecture:** Settings/Admin are surgical presentation edits. The extraction is a mechanical dedup: canonical consts move to `lib/tvStyles.ts`; only character-identical definition blocks are swapped for imports. Chips become CSS classes (hover requires them), retiring `chipBtn`/`restoreBtn`.

**Tech Stack:** Next.js 14, `--tv-*` tokens, vitest.

**Spec:** `docs/superpowers/specs/2026-08-01-pixel-pass-c-design.md`

## Global Constraints

- Branch `feat/pixel-pass-c` (created). **Never push `main`.**
- Presentation only: admin's polling loop, disabled Exit handler, ChangePassword mutation/validation byte-identical.
- Gate pattern: `--ink|--gold|text-gold|myGreen|myYellow|myRed|tableBg|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif` → zero matches in `app/(main)/admin/` + `app/(main)/settings/` after Task 2; `grep -rn "CryptoBot" app/ --include="*.tsx"` → zero after Task 1.
- Extraction rule (Task 3): swap ONLY character-identical const blocks; report any variant left in place. Diff discipline: extraction commits contain import swaps + deletion of identical blocks + the two new files' content — nothing else.
- Bash: quote paths with parentheses.

---

### Task 1: Settings restyle + CryptoBot metadata sweep

**Files:**
- Modify: `app/(main)/settings/_components/main.tsx` (full rewrite — 16 lines)
- Modify: `app/(main)/settings/_components/ChangePassword.tsx` (3 surgical edits)
- Modify (metadata only, exact field edits): `app/(main)/admin/page.tsx`, `app/(main)/settings/page.tsx`, `app/(main)/dashboard/page.tsx`, `app/(minimal)/forget-password/page.tsx`, `app/(minimal)/reset-password/[token]/page.tsx`, `app/(minimal)/verify-account/[token]/page.tsx`

**Interfaces:** unchanged exports throughout.

- [ ] **Step 1: Rewrite settings/_components/main.tsx**

```tsx
// React - Next default
"use client";
import React from "react";

// Components
import ChangePassword from "./ChangePassword";

const SettingsPage = () => {
  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Settings</span>
        <span className="text-sm" style={{ color: "var(--tv-text-soft)" }}>
          Account security
        </span>
      </div>
      <ChangePassword />
    </div>
  );
};

export default SettingsPage;
```

- [ ] **Step 2: ChangePassword.tsx surgical edits (3)**

Edit A — title:
Old: `      <div className="font-semibold text-lg">Change Password</div>`
New: `      <div className="text-base font-semibold">Change Password</div>`

Edit B — panel:
Old: `      <div className="w-full bg-tableBg1 rounded-2xl px-2 py-4 md:p-6">`
New:
```tsx
      <div
        className="w-full px-2 py-4 md:p-6"
        style={{
          background: "var(--tv-surface)",
          border: "1px solid var(--tv-border)",
          borderRadius: "8px",
        }}
      >
```

Edit C — button:
Old:
```tsx
          <Button
            disabled={isLoading}
            className="rounded-full text-white w-full"
          >
```
New:
```tsx
          <Button disabled={isLoading} className="w-full">
```

- [ ] **Step 3: Metadata edits (exact field values)**

- `app/(main)/admin/page.tsx`: title `"SuperAdmin - CryptoBot"` → `"Admin - Kronos"`; description `"SuperAdmin CryptoBot"` → `"Superadmin positions for Kronos"`.
- `app/(main)/settings/page.tsx`: title → `"Settings - Kronos"`; description → `"Settings for Kronos"`.
- `app/(main)/dashboard/page.tsx`: description `"Dashboard CryptoBot"` → `"Dashboard for Kronos"` (title already correct — do not touch).
- `app/(minimal)/forget-password/page.tsx`: title → `"Forget Password - Kronos"`; description → `"Forget Password for Kronos"`.
- `app/(minimal)/reset-password/[token]/page.tsx`: title → `"Reset Password - Kronos"`; description → `"Reset Password for Kronos"`.
- `app/(minimal)/verify-account/[token]/page.tsx`: description → `"Verify Account for Kronos"` (edit title too only if it contains CryptoBot).

- [ ] **Step 4: Gates**

`grep -rn "CryptoBot" app/ --include="*.tsx"` → no matches.
`grep -rnE -- "--ink|--gold|text-gold|myGreen|myYellow|myRed|tableBg|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif" "app/(main)/settings/"` → no matches.
`npm run build` → success.

- [ ] **Step 5: Commit**

```bash
git add "app/(main)/settings" "app/(main)/admin/page.tsx" "app/(main)/dashboard/page.tsx" "app/(minimal)"
git commit -m "ppc(task1): settings to tv tokens; CryptoBot metadata sweep -> Kronos"
```

---

### Task 2: Admin restyle

**Files:**
- Modify: `app/(main)/admin/_components/main.tsx` (6 surgical edits)

- [ ] **Step 1: header pattern.** Old:
```tsx
      <div className="flex items-center justify-between w-full">
        <div className="font-semibold text-lg">SUPER ADMIN</div>
      </div>
```
New:
```tsx
      <div className="flex flex-col">
        <span className="text-base font-semibold">Admin</span>
        <span className="text-sm" style={{ color: "var(--tv-text-soft)" }}>
          Per-broker positions — superadmin
        </span>
      </div>
```

- [ ] **Step 2: add canonical panelStyle const** after the `SuperAdminPagetableProps` interface's closing brace (before `const SuperAdminPage = () => {`):
```tsx
const panelStyle: React.CSSProperties = {
  background: "var(--tv-surface)",
  border: "1px solid var(--tv-border)",
  borderRadius: "8px",
};
```

- [ ] **Step 3: broker panel.** Old:
```tsx
                <div className="mt-5 bg-tableBg1 min-h-full w-full rounded-2xl flex flex-col items-start justify-start px-2.5 lg:px-4 py-4 text-[10px] md:text-[12px] xl:text-sm min-w-[500px] md:min-w-[900px] lg:w-full gap-6">
```
New:
```tsx
                <div
                  className="mt-5 min-h-full w-full flex flex-col items-start justify-start px-2.5 lg:px-4 py-4 text-[10px] md:text-[12px] xl:text-sm min-w-[500px] md:min-w-[900px] lg:w-full gap-6"
                  style={panelStyle}
                >
```

- [ ] **Step 4: section titles (2 sites).** For BOTH `Algo Positions` and `Actual Broker Positions`:
Old shape: `<div className="my-2 font-bold underline underline-offset-4 text-[12px] md:text-sm xl:text-base">`
New shape: `<div className="my-2 text-sm font-semibold">`
(Two separate exact edits — the inner text differs.)

- [ ] **Step 5: PnL colors (2 sites).** For BOTH the `strategy.profitLoss` and `position.profitLoss` cells:
Old shape:
```tsx
                            <div
                              className={`w-2/12 text-center ${
                                parseFloat(strategy.profitLoss) < 0
                                  ? "text-myRed1"
                                  : "text-myGreen1"
                              } `}
                            >
```
New shape:
```tsx
                            <div
                              className="w-2/12 text-center"
                              style={{
                                color:
                                  parseFloat(strategy.profitLoss) < 0
                                    ? "var(--tv-down)"
                                    : "var(--tv-up)",
                              }}
                            >
```
Second site — Old:
```tsx
                            <div
                              className={`w-2/12 text-center ${
                                parseFloat(position.profitLoss) < 0
                                  ? "text-myRed1"
                                  : "text-myGreen1"
                              } `}
                            >
```
New:
```tsx
                            <div
                              className="w-2/12 text-center"
                              style={{
                                color:
                                  parseFloat(position.profitLoss) < 0
                                    ? "var(--tv-down)"
                                    : "var(--tv-up)",
                              }}
                            >
```

- [ ] **Step 6: Exit dialog action.** Old:
`                                    <AlertDialogAction
                                      className="bg-myYellow1 text-black hover:bg-myYellow1"`
New:
`                                    <AlertDialogAction
                                      className="bg-[var(--tv-down)] text-white hover:bg-[var(--tv-down)]"`
(The commented-out onClick block below it stays exactly as is.)

- [ ] **Step 7: Gates.**
`grep -rnE -- "--ink|--gold|text-gold|myGreen|myYellow|myRed|tableBg|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif" "app/(main)/admin/"` → no matches.
`npm run build` → success.

- [ ] **Step 8: Commit**

```bash
git add "app/(main)/admin/_components/main.tsx"
git commit -m "ppc(task2): admin to tv tokens — panel, tables, PnL colors, exit action (logic untouched)"
```

---

### Task 3: tvStyles extraction + tv-chip classes

**Files:**
- Create: `lib/tvStyles.ts`
- Modify: `app/globals.css` (append chip classes)
- Modify (import swaps only): the files listed in Step 3
- Modify (chip adoption): `app/(main)/accounts/_components/AccountsManager.tsx`, `app/(main)/archive/_components/main.tsx`

- [ ] **Step 1: Create `lib/tvStyles.ts`**

```ts
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
```

- [ ] **Step 2: Append to `app/globals.css`** (at the end of the file):

```css
/* tv chips — class-based so hover states work (inline styles cannot) */
.tv-chip {
  font-size: 12px;
  font-weight: 600;
  border-radius: 4px;
  padding: 5px 12px;
  border: 1px solid var(--tv-border);
  color: var(--tv-text-soft);
  cursor: pointer;
  background: transparent;
  transition: border-color 120ms ease, background 120ms ease;
}
.tv-chip:hover {
  border-color: var(--tv-accent);
  background: color-mix(in srgb, var(--tv-accent) 8%, transparent);
}
.tv-chip--danger {
  border-color: var(--tv-down);
  color: var(--tv-down);
}
.tv-chip--danger:hover {
  border-color: var(--tv-down);
  background: color-mix(in srgb, var(--tv-down) 8%, transparent);
}
.tv-chip--up {
  border-color: var(--tv-up);
  color: var(--tv-up);
}
.tv-chip--up:hover {
  border-color: var(--tv-up);
  background: color-mix(in srgb, var(--tv-up) 8%, transparent);
}
```

- [ ] **Step 3: Import swaps.** For EACH file below: if its `panelStyle` / `soft` / `fieldStyle` definition block is **character-identical** to Step 1's canonical values, delete the block and add (or extend) `import { panelStyle, soft, fieldStyle } from "@/lib/tvStyles";` importing ONLY the names that file uses. If a definition differs in ANY character, leave that definition in place and record it in your report. Do not touch any other const (e.g. `chipStyle` in reports/signals stays).

Files (panelStyle sites): accounts/AccountsManager.tsx, archive/main.tsx, backtests/main.tsx, manager/main.tsx, manager-backtest/NewRunCard.tsx, manager-backtest/ResultsPanel.tsx, manager-backtest/RunsTable.tsx, marketplace/MarketplaceManager.tsx, reports/main.tsx, reports/MonthGrid.tsx, signals/main.tsx, signals/SignalMonthGrid.tsx, admin/_components/main.tsx (from Task 2).
Also swap `soft` (8 sites) and `fieldStyle` (accounts, marketplace) under the same identical-only rule.

- [ ] **Step 4: Chip adoption.**
- `AccountsManager.tsx`: delete the `chipBtn` const; Edit button → `className="tv-chip"` (no style prop); Delete button → `className="tv-chip tv-chip--danger"` (no style prop). Handlers unchanged.
- `archive/main.tsx`: delete the `restoreBtn` const; Restore button → `className="tv-chip tv-chip--up"` (no style prop). Handler unchanged.

- [ ] **Step 5: Gates.** `npm run test` → 44 pass. `npm run build` → success. `grep -rn "const panelStyle" app/ | grep -v ".tmp."` → only files reported as variants (expect zero or the variants you recorded). `git diff --stat` reviewed: only expected files.

- [ ] **Step 6: Commit**

```bash
git add lib/tvStyles.ts app/globals.css "app/(main)"
git commit -m "ppc(task3): extract tvStyles lib; tv-chip hover classes; retire chipBtn/restoreBtn"
```

---

### Task 4: End-to-end browser verification (controller-run)

- [ ] Kill port-3000 orphan, `npm run dev`, wait Ready.
- [ ] `/settings` dark+light: header, tv panel, PasswordInputs, Save button (do NOT submit).
- [ ] `/admin` dark+light: header, panels/tables if data renders (page may be empty outside NSE hours / without dummy brokers — chrome check only). No Exit clicks.
- [ ] `/accounts` + `/archive`: unchanged look post-extraction; hover a chip — border/tint appears; tab titles show Kronos (settings/admin).
- [ ] Screenshots (settings dark/light, admin dark/light, one chip-hover shot).
- [ ] Kill dev server + orphan check. No merge/push — user decision.
