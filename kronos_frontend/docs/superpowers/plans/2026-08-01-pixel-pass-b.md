# Pixel Pass B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `/accounts` and `/accountprofile` to the tv-token standard, presentation-only.

**Architecture:** Two small files are rewritten whole (`AccountsManager.tsx`, `RiskProfileTable.tsx`); the two logic-heavy files (`accountprofile/main.tsx`, `DataTable.tsx`) get surgical exact-string edits so their sorting/pagination/filter/mutation logic is untouchable by construction.

**Tech Stack:** Next.js 14 App Router, Apollo Client, shadcn Button/Select/DropdownMenu, `--tv-*` CSS tokens.

**Spec:** `docs/superpowers/specs/2026-08-01-pixel-pass-b-design.md`

## Global Constraints

- Branch: `feat/pixel-pass-b` (already created). **Never push `main`** (Netlify ships).
- **Presentation only**: no new `useState`; queries, mutations, handlers, hooks, sorting/pagination/filter logic byte-identical. The `/accounts` **Delete button behavior stays exactly as-is** (`window.confirm` → `DELETE_USER_BROKER`) — operator decision; restyle only.
- Gate pattern (spec's + `tableBg` discovered during planning):
  `--ink|--gold|text-gold|myGreen|myYellow|myRed|tableBg|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif`
  → zero matches in `app/(main)/accounts/` and `app/(main)/accountprofile/` after this branch.
- Colors: `var(--tv-up)` / `var(--tv-down)` / `var(--tv-text-soft)`; panels `var(--tv-surface)` + `1px solid var(--tv-border)` + radius 8. No new hex constants.
- Bash: quote paths containing parentheses.

---

### Task 1: Accounts page rewrite

**Files:**
- Modify: `app/(main)/accounts/_components/AccountsManager.tsx` (full rewrite)

**Interfaces:**
- Consumes: existing `ADD_ACCOUNT`, `UPDATE_ACCOUNT`, `DELETE_USER_BROKER`, `GET_ACCOUNTS` from `@/GraphQL/accountControls`; shadcn `Button` from `@/components/ui/button`.
- Produces: the `/accounts` page (default export `AccountsManager`).

- [ ] **Step 1: Rewrite the page**

Replace the entire contents of `app/(main)/accounts/_components/AccountsManager.tsx` with:

```tsx
"use client";

import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { Button } from "@/components/ui/button";
import {
  ADD_ACCOUNT,
  UPDATE_ACCOUNT,
  DELETE_USER_BROKER,
  GET_ACCOUNTS,
} from "@/GraphQL/accountControls";

interface Account {
  id: string;
  label: string;
  metaAccountId: string;
  metaApiTokenLast4: string;
  hasToken: boolean;
  isActive: boolean;
  status: string;
}

const emptyForm = { id: "", label: "", metaAccountId: "", metaApiToken: "" };

const panelStyle: React.CSSProperties = {
  background: "var(--tv-surface)",
  border: "1px solid var(--tv-border)",
  borderRadius: "8px",
};

const soft: React.CSSProperties = { color: "var(--tv-text-soft)" };

const fieldStyle: React.CSSProperties = {
  background: "var(--tv-bg)",
  border: "1px solid var(--tv-border)",
  borderRadius: "6px",
  padding: "6px 10px",
  fontSize: "13px",
  color: "inherit",
};

const chipBtn = (danger: boolean): React.CSSProperties => ({
  fontSize: "12px",
  fontWeight: 600,
  borderRadius: "4px",
  padding: "5px 12px",
  border: `1px solid ${danger ? "var(--tv-down)" : "var(--tv-border)"}`,
  color: danger ? "var(--tv-down)" : "var(--tv-text-soft)",
  cursor: "pointer",
  background: "transparent",
});

const AccountsManager: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [form, setForm] = useState({ ...emptyForm });
  const [editing, setEditing] = useState(false);

  const load = () => {
    client
      .query({ query: GET_ACCOUNTS, fetchPolicy: "no-cache" })
      .then((res) => {
        setAccounts(res.data?.getuserdata?.userbrokers ?? []);
      })
      .catch((err) => middleware(err));
  };

  useEffect(() => {
    load();
  }, []);

  const resetForm = () => {
    setForm({ ...emptyForm });
    setEditing(false);
  };

  const handleSubmit = () => {
    if (editing) {
      const variables: Record<string, string> = {
        id: form.id,
        label: form.label,
        metaAccountId: form.metaAccountId,
      };
      if (form.metaApiToken) variables.metaApiToken = form.metaApiToken;
      client
        .mutate({ mutation: UPDATE_ACCOUNT, variables, fetchPolicy: "no-cache" })
        .then((res) => {
          if (res.data.UpdateAccount.Response === "Success") {
            toast.success("Account updated");
            resetForm();
            load();
          } else {
            toast.error(res.data.UpdateAccount.Response);
          }
        })
        .catch((err) => middleware(err));
    } else {
      client
        .mutate({
          mutation: ADD_ACCOUNT,
          variables: {
            label: form.label,
            metaAccountId: form.metaAccountId,
            metaApiToken: form.metaApiToken,
          },
          fetchPolicy: "no-cache",
        })
        .then((res) => {
          if (res.data.AddAccount.Response === "Success") {
            toast.success("Account added");
            resetForm();
            load();
          } else {
            toast.error(res.data.AddAccount.Response);
          }
        })
        .catch((err) => middleware(err));
    }
  };

  const handleEdit = (a: Account) => {
    setForm({
      id: a.id,
      label: a.label,
      metaAccountId: a.metaAccountId,
      metaApiToken: "",
    });
    setEditing(true);
  };

  const handleDelete = (id: string) => {
    if (
      typeof window !== "undefined" &&
      !window.confirm("Delete this account? This cannot be undone.")
    ) {
      return;
    }
    client
      .mutate({
        mutation: DELETE_USER_BROKER,
        variables: { brokerId: id },
        fetchPolicy: "no-cache",
      })
      .then((res) => {
        if (res.data.DeleteUserBroker.Response === "Success") {
          toast.success("Account deleted");
          load();
        } else {
          toast.error(res.data.DeleteUserBroker.Response);
        }
      })
      .catch((err) => middleware(err));
  };

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Accounts</span>
        <span className="text-sm" style={soft}>
          MetaAPI broker accounts
        </span>
      </div>

      <div className="flex flex-col gap-3 p-4 max-w-xl w-full" style={panelStyle}>
        <div className="font-semibold">
          {editing ? "Edit account" : "Add account"}
        </div>
        <input
          style={fieldStyle}
          placeholder="Label (e.g. Primary Live)"
          value={form.label}
          onChange={(e) => setForm({ ...form, label: e.target.value })}
        />
        <input
          style={fieldStyle}
          placeholder="MetaAPI account ID"
          value={form.metaAccountId}
          onChange={(e) => setForm({ ...form, metaAccountId: e.target.value })}
        />
        <input
          style={fieldStyle}
          type="password"
          placeholder={
            editing ? "Token (leave blank to keep current)" : "MetaAPI token"
          }
          value={form.metaApiToken}
          onChange={(e) => setForm({ ...form, metaApiToken: e.target.value })}
        />
        <div className="flex gap-2">
          <Button size="sm" onClick={handleSubmit}>
            {editing ? "Save" : "Add"}
          </Button>
          {editing && (
            <Button size="sm" variant="ghost" onClick={resetForm}>
              Cancel
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-2 w-full">
        {accounts.length === 0 && (
          <div className="text-sm" style={soft}>
            No accounts yet.
          </div>
        )}
        {accounts.map((a) => (
          <div
            key={a.id}
            className="flex items-center justify-between px-4 py-3 w-full"
            style={panelStyle}
          >
            <div className="flex flex-col">
              <span className="font-semibold">{a.label || "(no label)"}</span>
              <span className="text-sm" style={soft}>
                {a.metaAccountId}
              </span>
            </div>
            <div className="text-sm" style={soft}>
              {a.hasToken ? `••••${a.metaApiTokenLast4}` : "no token set"}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                style={chipBtn(false)}
                onClick={() => handleEdit(a)}
              >
                Edit
              </button>
              <button
                type="button"
                style={chipBtn(true)}
                onClick={() => handleDelete(a.id)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AccountsManager;
```

- [ ] **Step 2: Gates**

Run: `grep -rnE -- "--ink|--gold|text-gold|myGreen|myYellow|myRed|tableBg|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif" "app/(main)/accounts/"` → no matches.
Run: `npm run build` → success.

- [ ] **Step 3: Commit**

```bash
git add "app/(main)/accounts/_components/AccountsManager.tsx"
git commit -m "ppb(task1): accounts to tv tokens — panel form, row panels, chip actions (logic untouched)"
```

---

### Task 2: RiskProfileTable rewrite + accountprofile chrome

**Files:**
- Modify: `app/(main)/accountprofile/_components/RiskProfileTable.tsx` (full rewrite)
- Modify: `app/(main)/accountprofile/_components/main.tsx` (5 surgical edits — exact strings below; touch NOTHING else in the file)

**Interfaces:**
- Consumes: `RiskProfileTableData` from `./main` (unchanged); ui/table primitives; shadcn Button/Select (already imported in main.tsx).
- Produces: same default exports; `main.tsx` keeps its `Controllerpage` export and all state/hooks.

- [ ] **Step 1: Rewrite RiskProfileTable.tsx**

Replace the entire contents with:

```tsx
// Components
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RiskProfileTableData } from "./main";

const cellBorder: React.CSSProperties = { borderColor: "var(--tv-border)" };

const RiskProfileTable = ({
  riskProfileData,
}: {
  riskProfileData: RiskProfileTableData[];
}) => {
  return (
    <div className="w-full flex flex-col gap-4">
      <div className="flex items-center justify-between w-full">
        <div className="text-base font-semibold">Risk Profiles</div>
      </div>
      <Table className="text-[10px] md:text-[12px] xl:text-sm">
        <TableHeader>
          <TableRow className="hover:bg-background">
            <TableHead rowSpan={2} className="border text-center" style={cellBorder}>
              Name
            </TableHead>
            <TableHead colSpan={2} className="border text-center" style={cellBorder}>
              Daily
            </TableHead>
            <TableHead colSpan={2} className="border text-center" style={cellBorder}>
              Weekly
            </TableHead>
            <TableHead colSpan={2} className="border text-center" style={cellBorder}>
              Monthly
            </TableHead>
          </TableRow>
          <TableRow className="hover:bg-background">
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-down)" }}>
              Loss
            </TableHead>
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-up)" }}>
              Profit
            </TableHead>
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-down)" }}>
              Loss
            </TableHead>
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-up)" }}>
              Profit
            </TableHead>
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-down)" }}>
              Loss
            </TableHead>
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-up)" }}>
              Profit
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {riskProfileData.map((riskProfile) => (
            <TableRow key={riskProfile.id}>
              <TableCell className="border text-center" style={cellBorder}>
                {riskProfile.name}
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.dailyLossLimitPercentage) * 100} %
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.dailyProfitLimitPercentage) * 100} %
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.weeklyLossLimitPercentage) * 100} %
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.weeklyProfitLimitPercentage) * 100} %
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.monthlyLossLimitPercentage) * 100} %
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.monthlyProfitLimitPercentage) * 100} %
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default RiskProfileTable;
```

- [ ] **Step 2: main.tsx surgical edit 1 — page header**

Old:
```tsx
  return (
    <div className="h-full flex flex-col items-start w-full gap-4">
      <div className="w-full overflow-auto">
```
New:
```tsx
  return (
    <div className="h-full flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Account Profile</span>
        <span className="text-sm" style={{ color: "var(--tv-text-soft)" }}>
          Risk profiles and account controls
        </span>
      </div>
      <div className="w-full overflow-auto">
```

- [ ] **Step 3: main.tsx surgical edit 2 — section title**

Old: `          <div className="font-semibold text-lg">Users Risk Profile</div>`
New: `          <div className="text-base font-semibold">Users Risk Profile</div>`

- [ ] **Step 4: main.tsx surgical edit 3 — search input**

Old:
```tsx
              <input
                type="text"
                placeholder="Search"
                value={queryFilter}
                onChange={(e) => {
                  setQueryFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-[200px] rounded-full p-2 px-4 placeholder:pl-6"
              />
```
New:
```tsx
              <input
                type="text"
                placeholder="Search"
                value={queryFilter}
                onChange={(e) => {
                  setQueryFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-[200px]"
                style={{
                  background: "var(--tv-bg)",
                  border: "1px solid var(--tv-border)",
                  borderRadius: "6px",
                  padding: "6px 10px",
                  fontSize: "13px",
                  color: "inherit",
                }}
              />
```

- [ ] **Step 5: main.tsx surgical edit 4 — Refresh button + page-size trigger**

Old: `              <Button
                className="rounded-full text-white"
                onClick={() => {
                  getAllUserData();
                }}
              >`
New: `              <Button
                size="sm"
                onClick={() => {
                  getAllUserData();
                }}
              >`

Old: `                <SelectTrigger
                  className="w-[150px] rounded-full"
                  name="expiry-selector"
                >`
New: `                <SelectTrigger
                  className="w-[150px]"
                  name="expiry-selector"
                >`

- [ ] **Step 6: main.tsx surgical edit 5 — pagination buttons**

Old:
```tsx
            <Button
              key={item}
              onClick={() => handlePageChange(item)}
              className={
                item === currentPage
                  ? "bg-blue-500 text-white"
                  : "bg-black dark:bg-white"
              }
            >
```
New:
```tsx
            <Button
              key={item}
              size="sm"
              variant={item === currentPage ? "default" : "ghost"}
              onClick={() => handlePageChange(item)}
            >
```

- [ ] **Step 7: Gates**

Run: `grep -rnE -- "--ink|--gold|text-gold|myGreen|myYellow|myRed|tableBg|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif" "app/(main)/accountprofile/_components/RiskProfileTable.tsx" "app/(main)/accountprofile/_components/main.tsx"` → no matches.
Run: `npm run build` → success.

- [ ] **Step 8: Commit**

```bash
git add "app/(main)/accountprofile/_components/RiskProfileTable.tsx" "app/(main)/accountprofile/_components/main.tsx"
git commit -m "ppb(task2): accountprofile chrome + risk-profile grid to tv tokens"
```

---

### Task 3: DataTable surgical edits + full gates

**Files:**
- Modify: `app/(main)/accountprofile/_components/DataTable.tsx` (7 surgical edits — exact strings below; sorting handlers, dropdown flow, and `changeRiskProfile` mutation must not change)

**Interfaces:**
- Consumes/produces: unchanged (`DataTableProps`, default export).

- [ ] **Step 1: wrapper panel (drops `bg-tableBg1`)**

Old:
```tsx
      <div className="bg-tableBg1 min-h-full w-full rounded-2xl flex flex-col items-start justify-start px-2.5 lg:px-4 py-4 text-[10px] md:text-[12px]  min-w-[900px] lg:w-full">
```
New:
```tsx
      <div
        className="min-h-full w-full flex flex-col items-start justify-start px-2.5 lg:px-4 py-4 text-[10px] md:text-[12px]  min-w-[900px] lg:w-full"
        style={{
          background: "var(--tv-surface)",
          border: "1px solid var(--tv-border)",
          borderRadius: "8px",
        }}
      >
```

- [ ] **Step 2: header row treatment**

Old:
```tsx
        <div className="flex items-center justify-normal w-full border-b py-1 md:py-2 font-semibold">
          <div className="w-1/12 text-center">Id</div>
```
New:
```tsx
        <div
          className="flex items-center justify-normal w-full border-b py-1 md:py-2 font-semibold uppercase tracking-wider"
          style={{ color: "var(--tv-text-soft)" }}
        >
          <div className="w-1/12 text-center">Id</div>
```

- [ ] **Step 3: status style logic (class → style object)**

Old:
```tsx
          const decryptedStatus: string = (item.status);
          let statusClass: string;

          if (
            decryptedStatus !== "Currently active" &&
            decryptedStatus !== "Currently Active"
          ) {
            statusClass = decryptedStatus.includes("-")
              ? "text-myRed1"
              : "text-myGreen1";
          } else {
            statusClass = "text-foreground";
          }
```
New:
```tsx
          const decryptedStatus: string = (item.status);
          let statusStyle: React.CSSProperties;

          if (
            decryptedStatus !== "Currently active" &&
            decryptedStatus !== "Currently Active"
          ) {
            statusStyle = decryptedStatus.includes("-")
              ? { color: "var(--tv-down)" }
              : { color: "var(--tv-up)" };
          } else {
            statusStyle = {};
          }
```

- [ ] **Step 4: daily PnL cell**

Old:
```tsx
              <div
                className={`w-1/12 text-center font-semibold ${
                  parseFloat((item.dailyPnlPercentage)) < 0
                    ? "text-myRed1"
                    : "text-myGreen1"
                }`}
              >
```
New:
```tsx
              <div
                className="w-1/12 text-center font-semibold"
                style={{
                  color:
                    parseFloat((item.dailyPnlPercentage)) < 0
                      ? "var(--tv-down)"
                      : "var(--tv-up)",
                }}
              >
```

- [ ] **Step 5: weekly PnL cell** — same shape as Step 4 with `weeklyPnlPercentage` in both the old and new strings.

Old:
```tsx
              <div
                className={`w-1/12 text-center font-semibold ${
                  parseFloat((item.weeklyPnlPercentage)) < 0
                    ? "text-myRed1"
                    : "text-myGreen1"
                }`}
              >
```
New:
```tsx
              <div
                className="w-1/12 text-center font-semibold"
                style={{
                  color:
                    parseFloat((item.weeklyPnlPercentage)) < 0
                      ? "var(--tv-down)"
                      : "var(--tv-up)",
                }}
              >
```

- [ ] **Step 6: monthly PnL cell** — same shape with `monthlyPnlPercentage`.

Old:
```tsx
              <div
                className={`w-1/12 text-center font-semibold ${
                  parseFloat((item.monthlyPnlPercentage)) < 0
                    ? "text-myRed1"
                    : "text-myGreen1"
                }`}
              >
```
New:
```tsx
              <div
                className="w-1/12 text-center font-semibold"
                style={{
                  color:
                    parseFloat((item.monthlyPnlPercentage)) < 0
                      ? "var(--tv-down)"
                      : "var(--tv-up)",
                }}
              >
```

- [ ] **Step 7: status cell uses the style object**

Old:
```tsx
              <div
                className={`w-1/12 text-center font-semibold ${statusClass}`}
              >
```
New:
```tsx
              <div
                className="w-1/12 text-center font-semibold"
                style={statusStyle}
              >
```

- [ ] **Step 8: Full gates**

Run: `grep -rnE -- "--ink|--gold|text-gold|myGreen|myYellow|myRed|tableBg|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif" "app/(main)/accounts/" "app/(main)/accountprofile/"` → no matches.
Run: `npm run test` → 4 files, 44 tests pass (no test files touched).
Run: `npm run build` → success.

- [ ] **Step 9: Commit**

```bash
git add "app/(main)/accountprofile/_components/DataTable.tsx"
git commit -m "ppb(task3): DataTable to tv tokens — panel wrapper, soft header, PnL/status colors"
```

---

### Task 4: End-to-end browser verification (controller-run)

**Files:** none (verification only; fix-forward commits if issues surface).

- [ ] **Step 1:** Kill any orphaned node on port 3000, `npm run dev` (background), wait for Ready on 3000.
- [ ] **Step 2:** `/accounts` dark: header, form panel + tv fields, row panels, Edit populates the form (then Cancel), Delete chip is `tv-down`-bordered — do NOT click Delete, do NOT submit Add/Save.
- [ ] **Step 3:** `/accountprofile` dark: header, Risk Profiles grid (Loss/Profit colored), Users table (sort by 2 columns — arrows flip; search filter narrows; page-size Select opens; pagination buttons if >1 page). Do NOT change any risk profile.
- [ ] **Step 4:** Toggle light theme; re-walk both. No legacy remnants.
- [ ] **Step 5:** Screenshot both tabs in both themes (4 shots), save to disk.
- [ ] **Step 6:** Kill the dev server and verify port 3000 released. Do NOT merge or push — user decision.
