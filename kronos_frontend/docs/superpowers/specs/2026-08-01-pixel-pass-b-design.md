# Pixel Pass B — Accounts + Accountprofile → tv Redesign

**Date:** 2026-08-01
**Status:** Approved (brainstorm 2026-08-01)
**Repos touched:** kronos_frontend only — no backend change, no box deploy.
**Series:** Group B of the legacy-tab redesign (A: marketplace/backtests/archive —
shipped `13b1ead`, live; C: admin + settings — next).

## What

Full redesign of the account pair — `/accounts` and `/accountprofile` — to the
tv-token standard set by Reports/Signals/Pass A: header pattern, tv panels and
tables, shadcn controls, both themes, zero legacy tokens.

## Hard constraints

- **Presentation only.** Queries, mutations, variables, handlers, hooks, state,
  sorting/pagination/filter logic stay byte-identical. No new `useState`.
- **State-coverage exception (explicit):** pages whose legacy code lacks
  loading/error state variables keep that behavior — do NOT add state to
  satisfy the shared frame. Accounts has no loading/error UI (loads silently);
  accountprofile keeps its existing `isLoading` usage as-is, restyled only.
- **The Delete button on /accounts stays exactly as it behaves today**
  (`window.confirm` → `DELETE_USER_BROKER`). This was a considered decision
  (2026-08-01): the operator chose presentation-only purism over removing or
  hardening it. Restyle only (tv-down bordered chip). The ops rule "archive
  brokers by flags, never DeleteUserBroker" remains a human-discipline rule.
- **Zero legacy tokens** in `app/(main)/accounts/` and `app/(main)/accountprofile/`
  after this branch. Gate (the Pass-A extended pattern + `text-gold`):
  `--ink|--gold|text-gold|myGreen|myYellow|myRed|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif`
- Colors: money/win `var(--tv-up)`, loss `var(--tv-down)`, soft
  `var(--tv-text-soft)`, panels `var(--tv-surface)` + `1px solid var(--tv-border)`
  + radius 8. No new hex constants.
- Branch `feat/pixel-pass-b` off main (`13b1ead`). Never push `main` (Netlify ships).

## Per-screen design

### `/accounts` (`app/(main)/accounts/_components/AccountsManager.tsx`, 206 lines)

- Header: "Accounts" / subtitle "MetaAPI broker accounts".
- Add/Edit form: tv panel (`max-w-xl` kept), form title semibold
  ("Edit account" / "Add account" logic unchanged), the three inputs restyled
  with the marketplace `fieldStyle` idiom (`var(--tv-bg)` background,
  `1px solid var(--tv-border)`, radius 6, 13px; password type kept on the token
  field, placeholder strings unchanged).
- Buttons: Save/Add → shadcn `Button` default `size="sm"`; Cancel (edit mode
  only, unchanged conditional) → `variant="ghost" size="sm"`.
- Account list: one tv row-panel per account (flex row as today): label
  semibold with "(no label)" fallback, MetaAPI id soft small beneath; token
  status soft small (`••••{last4}` / "no token set" logic unchanged); actions —
  Edit as a bordered soft chip button, Delete as a `var(--tv-down)`-bordered
  chip (same handlers, same confirm).
- Empty state: "No accounts yet." as soft tv text (no panel — matches its
  legacy inline placement).

### `/accountprofile` (3 components, logic-heavy — restyle only)

**`main.tsx` (347 lines):** header pattern ("Account Profile" title + soft
subtitle "risk profiles and account controls"); the search/filter input to the
`fieldStyle` idiom; pagination controls to shadcn ghost `size="sm"` buttons and
soft page-count text; panel wrappers to tv panels. All hooks (`useRiskProfiles`,
`useUserData`), fetches, sorting state machine, pagination math, and the
risk-profile assignment flow (already on shadcn Select/Button) unchanged.

**`DataTable.tsx` (310 lines):** keep the ui/table primitives and every column,
sort indicator, and click handler. Replace the eight `text-myRed1`/`text-myGreen1`
PnL/status classes with inline `style={{ color: "var(--tv-down)" }}` /
`"var(--tv-up)"` (negative → down, else up — preserve each site's existing
sign test exactly). Header row to the soft uppercase treatment where it
deviates; hairline `var(--tv-border)` row borders.

**`RiskProfileTable.tsx` (91 lines):** keep the two-row grouped header
(Name | Daily/Weekly/Monthly × Loss/Profit) and the `colSpan` structure.
`text-myRed1` → inline `var(--tv-down)`, `text-myGreen1` → inline `var(--tv-up)`
on the Loss/Profit sub-headers. Soften the grid: `border-2` → `border` with
`borderColor: var(--tv-border)` (inline or via the primitives' default).
Section title "Risk Profile Table" → the standard semibold + optional soft
subtitle. Percentage math (`parseFloat(x) * 100 %`) unchanged.

## Explicitly out of scope

- Removing/hardening the Delete button (operator decision recorded above).
- Group C (admin, settings), the legacy bridge, the landing page.
- Any change to sorting/pagination/filtering behavior or the risk-profile
  assignment flow.
- pnlColor consolidation (four local copies exist — noted follow-up from the
  Pass A review, separate cleanup).

## Testing & verification

- Gates per task: the grep above on the task's directory → no matches;
  `npm run build`. Final task adds `npm run test` (suite 44 — no test files
  change in this pass).
- Browser walk on the dev server (kill any port-3000 orphan first): both tabs,
  dark AND light. Accounts: exercise the Edit flow (populate form, Cancel) —
  do NOT submit Add/Save with real values, do NOT press Delete. Accountprofile:
  exercise sorting on 2 columns, pagination if >1 page, search filter typing,
  and open (not save) the risk-profile Select.
- Merge/push is a user decision (ships via Netlify).
