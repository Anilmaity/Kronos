# Pixel Pass C — Admin + Settings + Series Close-Out

**Date:** 2026-08-01
**Status:** Approved (brainstorm 2026-08-01; user approved design and waived separate spec review — "write the plan and go")
**Repos touched:** kronos_frontend only.
**Series:** final group (A: marketplace/backtests/archive — live; B: accounts/accountprofile — live).

## What

1. tv redesign of `/settings` (ChangePassword panel) and `/admin` (SuperAdmin positions screen) — presentation-only.
2. **CryptoBot metadata sweep**: the seven remaining "CryptoBot" title/description sites → Kronos.
3. **Style-const extraction**: new `lib/tvStyles.ts` (`panelStyle`, `soft`, `fieldStyle`); all character-identical duplicates across converted pages become imports.
4. **Chip hover states**: `.tv-chip` / `.tv-chip--danger` / `.tv-chip--up` classes in `globals.css` (hover = accent/danger tint via `color-mix`), adopted by the static chips (accounts Edit/Delete, archive Restore) — replacing their `chipBtn`/`restoreBtn` consts. State-dependent chips (reports/signals) keep inline styles.

## Hard constraints

- **Presentation only** on settings/admin: form logic, mutations, the admin 1-second
  NSE-hours polling loop, and the disabled Exit handler stay byte-identical.
  (Fossils noted: admin's superuser gate is commented out, Exit onClick is
  commented out, and the poll window is Indian-equities hours — a future
  decision should retire or rebuild this page; NOT this pass.)
- Gate (extended pattern) → zero matches in `app/(main)/admin/` and
  `app/(main)/settings/` after this branch; and repo-wide `CryptoBot` grep in
  `app/` → zero matches.
- Extraction may only swap definition blocks that are **character-identical**
  to the canonical `tvStyles.ts` values; any variant stays put and is reported.
- After this pass: zero legacy tokens in all of `app/(main)`. Legacy bridge
  removal remains a separate future cleanup (landing page still bridges).
- Branch `feat/pixel-pass-c` off main (`d13e99b`). Never push `main`.

## Per-screen design

**Settings**: `_components/main.tsx` gains the header pattern ("Settings" /
"Account security"); `ChangePassword.tsx` — title to `text-base font-semibold`,
`bg-tableBg1 rounded-2xl` panel → tv panel, Save button drops
`rounded-full text-white` (keeps `w-full`, disabled logic unchanged). Inputs are
already the reworked `PasswordInput`. Mutation untouched (pre-existing
string-interpolation noted as a future logic-pass item).

**Admin**: "SUPER ADMIN" heading → header pattern ("Admin" / "Per-broker
positions — superadmin"); broker panel `bg-tableBg1 rounded-2xl` → local
canonical `panelStyle` (so Task 3 swaps it to the import); section titles drop
the underline for `text-sm font-semibold`; both table header rows get the soft
uppercase treatment; the two PnL `myRed1/myGreen1` template sites → inline
`var(--tv-down)`/`var(--tv-up)` (sign tests preserved); AlertDialogAction
`bg-myYellow1 text-black hover:bg-myYellow1` → `bg-[var(--tv-down)] text-white
hover:bg-[var(--tv-down)]`.

**Metadata sweep** (titles `X - Kronos`, descriptions `X for Kronos`):
admin ("Admin - Kronos"), settings, dashboard (description only — title already
Kronos), forget-password, reset-password, verify-account.

## Testing & verification

Per-task: directory grep gate + `npm run build`. Extraction task: `npm run test`
(44) + build + a diff-discipline rule (import swaps only). Browser walk:
settings + admin dark/light (no password submission, no Exit clicks), plus one
Pass A page (archive) and accounts to confirm the extraction/chip refactor
changed nothing visually except hover. Merge/push = user decision.
