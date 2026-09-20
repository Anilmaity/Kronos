# Pixel Pass A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `/marketplace`, `/backtests`, `/archive` to the tv-token standard and clear the shared legacy leftovers (Loader, Card, navbar seam, tmp debris).

**Architecture:** Pure presentation rework — each page keeps its data layer (queries, mutations, handlers, state) byte-identical and swaps only the rendered JSX/styles to the Reports/Signals pattern. One shared-fix task carries `pnlColor` (already in Task 1), `Loader.tsx`, `ui/card.tsx`, the navbar seam, and debris deletion.

**Tech Stack:** Next.js 14 App Router, Apollo Client, vitest, shadcn Button, `--tv-*` CSS tokens.

**Spec:** `docs/superpowers/specs/2026-08-01-pixel-pass-a-design.md`

## Global Constraints

- Branch: `feat/pixel-pass-a` (already created). **Never push `main`** (Netlify ships).
- **Presentation only**: queries, mutations, variables, handlers, and data flow stay byte-identical in all three pages.
- Zero legacy tokens after this branch in: `app/(main)/marketplace/`, `app/(main)/backtests/`, `app/(main)/archive/`, `components/Loader.tsx`, `components/ui/card.tsx`, `app/(main)/_components/navbar.tsx`. Gate pattern: `--ink|--gold|myGreen|myYellow|myRed|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif`
- Colors: money/win `var(--tv-up)`, loss `var(--tv-down)`, soft `var(--tv-text-soft)`, panels `var(--tv-surface)` + `1px solid var(--tv-border)` + radius 8. No new hex constants.
- Test command (bash — quote paths with parens): `npm run test` for the suite; `npx vitest run utils/format.test.ts` for the focused file.

---

### Task 1: `pnlColor` → tv tokens + Backtests page redesign

**Files:**
- Modify: `utils/format.ts` (pnlColor only)
- Modify: `utils/format.test.ts` (pnlColor expectations only)
- Modify: `app/(main)/backtests/_components/main.tsx` (full rewrite)

**Interfaces:**
- Consumes: existing `fmtNum(v, digits)`, `fmtSigned(v, digits)` from `@/utils/format` (unchanged).
- Produces: `pnlColor(v): string` now returns `var(--tv-down)` (n<0), `var(--tv-up)` (n≥0), `var(--tv-text-soft)` (null/undefined/""/NaN). Only this page imports it — Reports MonthGrid and manager-backtest ResultsPanel define their own local versions; do not touch them.

- [ ] **Step 1: Update the failing test first**

In `utils/format.test.ts`, replace the two `pnlColor` test bodies (currently expecting `#b84c28`, `#50ba60`, `var(--ink-muted)`) with:

```ts
describe("pnlColor", () => {
  it("is tv-down below zero and tv-up at or above zero", () => {
    expect(pnlColor(-0.01)).toBe("var(--tv-down)");
    expect(pnlColor(0)).toBe("var(--tv-up)");
    expect(pnlColor("12.5")).toBe("var(--tv-up)");
  });

  it("is soft for empty/invalid input", () => {
    expect(pnlColor(null)).toBe("var(--tv-text-soft)");
    expect(pnlColor(undefined)).toBe("var(--tv-text-soft)");
    expect(pnlColor("")).toBe("var(--tv-text-soft)");
    expect(pnlColor("abc")).toBe("var(--tv-text-soft)");
  });
});
```

Keep the `describe` block position and everything else in the file unchanged.

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run utils/format.test.ts`
Expected: FAIL — pnlColor tests expect tv tokens, implementation still returns hexes.

- [ ] **Step 3: Update the implementation**

In `utils/format.ts`, replace the `pnlColor` function body (keep the JSDoc line, update its wording):

```ts
/** P&L colour: tv-down below zero, tv-up otherwise, soft for empty/invalid. (backtests) */
export const pnlColor = (v: string | number | null | undefined): string => {
  if (v === null || v === undefined || v === "") return "var(--tv-text-soft)";
  const n = Number(v);
  if (Number.isNaN(n)) return "var(--tv-text-soft)";
  return n < 0 ? "var(--tv-down)" : "var(--tv-up)";
};
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx vitest run utils/format.test.ts` → PASS.
Then `npm run test` → 4 files, 44 tests, all pass.

- [ ] **Step 5: Rewrite the backtests page**

Replace the entire contents of `app/(main)/backtests/_components/main.tsx` with:

```tsx
"use client";

import React, { useEffect, useState } from "react";
import { gql } from "@apollo/client";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { fmtNum, fmtSigned, pnlColor } from "@/utils/format";

interface BacktestReport {
  id: string;
  strategyId: string;
  strategyName: string;
  runLabel: string;
  periodStart: string | null;
  periodEnd: string | null;
  trades: number;
  wins: number;
  losses: number;
  winRatePct: string | null;
  pnlPts: string | null;
  maxDdPts: string | null;
  avgWinPts: string | null;
  avgLossPts: string | null;
  profitFactor: string | null;
  expectancyPts: string | null;
  sourceCsv: string | null;
  notes: string | null;
}

const QUERY = gql`
  query AllBacktestReport {
    allBacktestReport {
      id
      strategyId
      strategyName
      runLabel
      periodStart
      periodEnd
      trades
      wins
      losses
      winRatePct
      pnlPts
      maxDdPts
      avgWinPts
      avgLossPts
      profitFactor
      expectancyPts
      sourceCsv
      notes
    }
  }
`;

const panelStyle: React.CSSProperties = {
  background: "var(--tv-surface)",
  border: "1px solid var(--tv-border)",
  borderRadius: "8px",
};

const soft: React.CSSProperties = { color: "var(--tv-text-soft)" };

const BacktestReportsPage: React.FC = () => {
  const [reports, setReports] = useState<BacktestReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const { data } = await client.query({
        query: QUERY,
        fetchPolicy: "no-cache",
      });
      setReports(data?.allBacktestReport ?? []);
      setError(null);
    } catch (err: any) {
      middleware(err);
      setError(err?.message ?? "Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Backtest Reports</span>
        <span className="text-sm" style={soft}>
          {reports.length} offline runs — points, not USD
        </span>
      </div>

      {loading && (
        <div
          className="w-full flex items-center justify-center px-4 py-16 text-sm"
          style={{ ...panelStyle, ...soft }}
        >
          Loading reports…
        </div>
      )}

      {error && !loading && (
        <div
          className="w-full px-4 py-6 text-sm"
          style={{ ...panelStyle, color: "var(--tv-down)" }}
        >
          {error}
        </div>
      )}

      {!loading && !error && reports.length === 0 && (
        <div
          className="w-full flex items-center justify-center px-4 py-16 text-sm"
          style={{ ...panelStyle, ...soft }}
        >
          No backtest reports
        </div>
      )}

      {!loading && !error && reports.length > 0 && (
        <div className="w-full overflow-x-auto" style={panelStyle}>
          <div
            className="flex items-center w-full px-4 py-3 min-w-[1200px] text-xs font-semibold uppercase tracking-wider"
            style={{ ...soft, borderBottom: "1px solid var(--tv-border)" }}
          >
            <div className="w-[16%]">Strategy</div>
            <div className="w-[14%]">Run</div>
            <div className="w-[12%]">Period</div>
            <div className="w-[6%] text-end">Trades</div>
            <div className="w-[7%] text-end">W / L</div>
            <div className="w-[6%] text-end">Win %</div>
            <div className="w-[8%] text-end">PnL pts</div>
            <div className="w-[7%] text-end">Max DD</div>
            <div className="w-[5%] text-end">PF</div>
            <div className="w-[8%] text-end">E[R] pts</div>
            <div className="w-[11%] pl-3">Notes</div>
          </div>

          {reports.map((r) => (
            <div
              key={r.id}
              className="flex items-center w-full px-4 py-3 min-w-[1200px] text-sm"
              style={{ borderBottom: "1px solid var(--tv-border)" }}
            >
              <div className="w-[16%] truncate" title={r.strategyName}>
                {r.strategyName}
              </div>
              <div className="w-[14%] truncate text-xs" style={soft} title={r.runLabel}>
                {r.runLabel}
              </div>
              <div className="w-[12%] text-xs" style={soft}>
                {r.periodStart && r.periodEnd
                  ? `${r.periodStart} → ${r.periodEnd}`
                  : "—"}
              </div>
              <div className="w-[6%] text-end">{r.trades}</div>
              <div className="w-[7%] text-end text-xs" style={soft}>
                {r.wins}/{r.losses}
              </div>
              <div className="w-[6%] text-end">{fmtNum(r.winRatePct, 1)}</div>
              <div
                className="w-[8%] text-end font-semibold"
                style={{ color: pnlColor(r.pnlPts) }}
              >
                {fmtSigned(r.pnlPts, 2)}
              </div>
              <div className="w-[7%] text-end">{fmtNum(r.maxDdPts, 2)}</div>
              <div className="w-[5%] text-end">{fmtNum(r.profitFactor, 2)}</div>
              <div className="w-[8%] text-end">{fmtNum(r.expectancyPts, 4)}</div>
              <div className="w-[11%] pl-3 truncate text-xs" style={soft} title={r.notes ?? ""}>
                {r.notes ?? "—"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BacktestReportsPage;
```

- [ ] **Step 6: Gates**

Run: `grep -rnE -- "--ink|--gold|myGreen|myYellow|myRed|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif" "app/(main)/backtests/" utils/format.ts` → no matches.
Run: `npm run build` → success.

- [ ] **Step 7: Commit**

```bash
git add utils/format.ts utils/format.test.ts "app/(main)/backtests/_components/main.tsx"
git commit -m "ppa(task1): backtests to tv tokens; pnlColor retokenized (test-first)"
```

---

### Task 2: Archive page redesign

**Files:**
- Modify: `app/(main)/archive/_components/main.tsx` (full rewrite)

**Interfaces:**
- Consumes: existing `GET_ARCHIVED_STRATEGIES`, `UNARCHIVE_STRATEGY`, `formatCapital` — all unchanged. The `ArchivedStrategy` interface stays identical (it already carries `multiplyer` and `totalPositionCount`, previously unrendered).
- Produces: the `/archive` page (default export `ArchivePage`).

- [ ] **Step 1: Rewrite the page**

Replace the entire contents of `app/(main)/archive/_components/main.tsx` with:

```tsx
/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import React, { useCallback, useEffect, useState } from "react";

import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import {
  GET_ARCHIVED_STRATEGIES,
  UNARCHIVE_STRATEGY,
} from "@/GraphQL/strategyControls";

import { formatCapital } from "@/utils/FormatCapital";

interface ArchivedStrategy {
  id: string;
  name: string;
  brokerName: string | null;
  multiplyer: number;
  isActive: boolean;
  createdAt: string;
  totalProfitLoss: number | null;
  totalPositionCount: number | null;
  strategy: { id: string; name: string } | null;
}

const panelStyle: React.CSSProperties = {
  background: "var(--tv-surface)",
  border: "1px solid var(--tv-border)",
  borderRadius: "8px",
};

const soft: React.CSSProperties = { color: "var(--tv-text-soft)" };

const plColor = (n: number): string =>
  n < 0 ? "var(--tv-down)" : n > 0 ? "var(--tv-up)" : "var(--tv-text-soft)";

const restoreBtn: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 600,
  borderRadius: "4px",
  padding: "5px 12px",
  border: "1px solid var(--tv-up)",
  color: "var(--tv-up)",
  cursor: "pointer",
  background: "transparent",
};

const ArchivePage = () => {
  const [rows, setRows] = useState<ArchivedStrategy[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const { data } = await client.query({
        query: GET_ARCHIVED_STRATEGIES,
        fetchPolicy: "no-cache",
      });
      setRows(data.archivedStrategies ?? []);
    } catch (err) {
      middleware(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleUnarchive = (userStrategyId: string) => {
    client
      .mutate({
        mutation: UNARCHIVE_STRATEGY,
        variables: { userStrategyId },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        const message = response.data.UnarchiveStrategy.Response;
        if (message === "Success") {
          toast.success("Strategy Restored");
          fetchData();
        } else {
          toast.error(message);
        }
      })
      .catch((err) => {
        middleware(err);
      });
  };

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Archive</span>
        <span className="text-sm" style={soft}>
          Archived strategies — restore returns them to the dashboard, stopped
        </span>
      </div>

      {loading && (
        <div
          className="w-full flex items-center justify-center px-4 py-16 text-sm"
          style={{ ...panelStyle, ...soft }}
        >
          Loading…
        </div>
      )}

      {!loading && rows.length === 0 && (
        <div
          className="w-full flex items-center justify-center px-4 py-16 text-sm"
          style={{ ...panelStyle, ...soft }}
        >
          Nothing archived
        </div>
      )}

      {!loading && rows.length > 0 && (
        <div className="w-full overflow-x-auto" style={panelStyle}>
          <div
            className="flex items-center w-full px-4 py-3 min-w-[900px] text-xs font-semibold uppercase tracking-wider"
            style={{ ...soft, borderBottom: "1px solid var(--tv-border)" }}
          >
            <div className="w-[24%]">Strategy</div>
            <div className="w-[16%]">Broker</div>
            <div className="w-[8%] text-end">Mult</div>
            <div className="w-[14%] text-end">Archived</div>
            <div className="w-[12%] text-end">P&amp;L</div>
            <div className="w-[10%] text-end">Positions</div>
            <div className="w-[16%] text-end">Actions</div>
          </div>

          {rows.map((row) => (
            <div
              key={row.id}
              className="flex items-center w-full px-4 py-3 min-w-[900px] text-sm"
              style={{ borderBottom: "1px solid var(--tv-border)" }}
            >
              <div className="w-[24%] truncate" title={row.name}>
                {row.name}
              </div>
              <div className="w-[16%] truncate text-xs" style={soft}>
                {row.brokerName || "—"}
              </div>
              <div className="w-[8%] text-end">{row.multiplyer}x</div>
              <div className="w-[14%] text-end text-xs" style={soft}>
                {row.createdAt ? row.createdAt.split("T")[0] : "—"}
              </div>
              <div
                className="w-[12%] text-end font-semibold"
                style={{ color: plColor(Number(row.totalProfitLoss ?? 0)) }}
              >
                {formatCapital(Number(Number(row.totalProfitLoss ?? 0).toFixed(2)))}
              </div>
              <div className="w-[10%] text-end">{row.totalPositionCount ?? 0}</div>
              <div className="w-[16%] flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => handleUnarchive(row.id)}
                  style={restoreBtn}
                >
                  Restore
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ArchivePage;
```

- [ ] **Step 2: Gates**

Run: `grep -rnE -- "--ink|--gold|myGreen|myYellow|myRed|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif" "app/(main)/archive/"` → no matches.
Run: `npm run build` → success.

- [ ] **Step 3: Commit**

```bash
git add "app/(main)/archive/_components/main.tsx"
git commit -m "ppa(task2): archive to tv tokens — table with mult/positions, restore chip"
```

---

### Task 3: Marketplace page redesign

**Files:**
- Modify: `app/(main)/marketplace/_components/MarketplaceManager.tsx` (full rewrite)

**Interfaces:**
- Consumes: existing `DEPLOY_STRATEGY`, `GET_MARKETPLACE`, `GET_ACCOUNTS_WITH_DEPLOYMENTS`, `formatCapital`, shadcn `Button` from `@/components/ui/button`.
- Produces: the `/marketplace` page (default export `MarketplaceManager`).

- [ ] **Step 1: Rewrite the page**

Replace the entire contents of `app/(main)/marketplace/_components/MarketplaceManager.tsx` with:

```tsx
"use client";

import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { formatCapital } from "@/utils/FormatCapital";
import { Button } from "@/components/ui/button";
import {
  DEPLOY_STRATEGY,
  GET_MARKETPLACE,
  GET_ACCOUNTS_WITH_DEPLOYMENTS,
} from "@/GraphQL/marketplaceControls";

interface Strategy {
  id: string;
  name: string;
  description: string;
  capitalRequired: string;
  symbol: string;
  isActive: boolean;
}

interface Account {
  id: string;
  label: string;
  deployedStrategyIds: string[];
}

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

const MarketplaceManager: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [openFor, setOpenFor] = useState<string | null>(null);
  const [pickedAccount, setPickedAccount] = useState<string>("");
  const [multiplier, setMultiplier] = useState<number>(1);

  const loadStrategies = () => {
    client
      .query({ query: GET_MARKETPLACE, fetchPolicy: "no-cache" })
      .then((res) => {
        const all: Strategy[] = res.data?.allStrategy ?? [];
        setStrategies(all.filter((s) => s.isActive));
      })
      .catch((err) => middleware(err));
  };

  const loadAccounts = () => {
    client
      .query({ query: GET_ACCOUNTS_WITH_DEPLOYMENTS, fetchPolicy: "no-cache" })
      .then((res) => {
        const brokers = res.data?.getuserdata?.userbrokers ?? [];
        setAccounts(
          brokers.map(
            (b: {
              id: string;
              label: string;
              userstrategys: { strategy: { id: string } }[];
            }) => ({
              id: b.id,
              label: b.label,
              deployedStrategyIds: (b.userstrategys ?? []).map(
                (us) => us.strategy?.id
              ),
            })
          )
        );
      })
      .catch((err) => middleware(err));
  };

  useEffect(() => {
    loadStrategies();
    loadAccounts();
  }, []);

  const openDeploy = (strategyId: string) => {
    setOpenFor(strategyId);
    setPickedAccount("");
    setMultiplier(1);
  };

  const handleDeploy = (strategyId: string) => {
    if (!pickedAccount) {
      toast.error("Pick an account");
      return;
    }
    client
      .mutate({
        mutation: DEPLOY_STRATEGY,
        variables: {
          strategyId,
          userBrokerId: pickedAccount,
          quantity: multiplier,
        },
        fetchPolicy: "no-cache",
      })
      .then((res) => {
        const resp = res.data.AddStrategy.Response;
        if (resp === "Success") {
          toast.success("Strategy deployed");
          setOpenFor(null);
          loadAccounts();
        } else {
          toast.error(resp);
        }
      })
      .catch((err) => middleware(err));
  };

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Marketplace</span>
        <span className="text-sm" style={soft}>
          Deployable strategies
        </span>
      </div>

      <div
        className="w-full px-4 py-3 text-sm"
        style={{
          ...panelStyle,
          ...soft,
          borderLeft: "3px solid var(--tv-accent)",
        }}
      >
        Deployed strategies trade on the configured runner account until
        per-account trading is enabled. The account you choose here records the
        deployment but does not yet route trades.
      </div>

      {accounts.length === 0 && (
        <div className="text-sm" style={soft}>
          No accounts yet — add one on the Accounts page first.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
        {strategies.length === 0 && (
          <div className="text-sm" style={soft}>
            No strategies available.
          </div>
        )}
        {strategies.map((s) => (
          <div key={s.id} className="p-4 flex flex-col gap-2" style={panelStyle}>
            <div className="font-semibold">{s.name}</div>
            <div className="text-sm" style={soft}>
              {s.description || "—"}
            </div>
            <div className="text-xs" style={soft}>
              {s.symbol} · Capital {formatCapital(parseInt(s.capitalRequired))}
            </div>

            {openFor === s.id ? (
              <div className="flex flex-col gap-2 mt-2">
                <select
                  style={fieldStyle}
                  value={pickedAccount}
                  onChange={(e) => setPickedAccount(e.target.value)}
                >
                  <option value="">Select account…</option>
                  {accounts.map((a) => {
                    const already = a.deployedStrategyIds.includes(s.id);
                    return (
                      <option key={a.id} value={a.id} disabled={already}>
                        {a.label || "(no label)"}
                        {already ? " — Deployed" : ""}
                      </option>
                    );
                  })}
                </select>
                <input
                  style={fieldStyle}
                  type="number"
                  min={1}
                  value={multiplier}
                  onChange={(e) =>
                    setMultiplier(Math.max(1, Number(e.target.value)))
                  }
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => handleDeploy(s.id)}>
                    Confirm deploy
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setOpenFor(null)}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mt-2">
                <Button size="sm" onClick={() => openDeploy(s.id)}>
                  Deploy
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default MarketplaceManager;
```

- [ ] **Step 2: Gates**

Run: `grep -rnE -- "--ink|--gold|myGreen|myYellow|myRed|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif" "app/(main)/marketplace/"` → no matches.
Run: `npm run build` → success.

- [ ] **Step 3: Commit**

```bash
git add "app/(main)/marketplace/_components/MarketplaceManager.tsx"
git commit -m "ppa(task3): marketplace to tv cards + shadcn deploy controls (logic untouched)"
```

---

### Task 4: Shared fixes — Loader, Card, navbar seam, debris

**Files:**
- Modify: `components/Loader.tsx` (full rewrite)
- Modify: `components/ui/card.tsx` (full rewrite)
- Modify: `app/(main)/_components/navbar.tsx` (one line)
- Delete (untracked debris, plain `rm`): `app/(main)/dashboard/_components/StrategyTable.tsx.tmp.11024.1778307371534`, `app/globals.css.tmp.*` (3 files), `app/_components/algorobos/algorobos.css.tmp.*` (4 files)

**Interfaces:**
- Consumes: nothing new.
- Produces: same component exports (`Loader` default; `Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent`) — signatures unchanged, callers unaffected.

- [ ] **Step 1: Rewrite Loader.tsx**

```tsx
"use client";
import { ScaleLoader } from "react-spinners";

const Loader = () => {
  return (
    <div className="h-[70vh] flex flex-col gap-4 justify-center items-center">
      <ScaleLoader
        height={28}
        width={3}
        radius={1}
        margin={3}
        color="var(--tv-accent)"
      />
      <span className="text-xs" style={{ color: "var(--tv-text-soft)" }}>
        Loading
      </span>
    </div>
  );
};

export default Loader;
```

- [ ] **Step 2: Rewrite ui/card.tsx**

```tsx
import * as React from "react"
import { cn } from "@/lib/utils"

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("relative flex flex-col text-card-foreground shadow-sm", className)}
    style={{
      background: "var(--tv-surface)",
      border: "1px solid var(--tv-border)",
      borderRadius: "8px",
    }}
    {...props}
  />
))
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-5", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn("text-base font-semibold leading-none tracking-tight", className)}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm", className)}
    style={{ color: "var(--tv-text-soft)" }}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-5 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-5 pt-0", className)}
    style={{
      borderTop: "1px solid var(--tv-border)",
      marginTop: "auto",
      paddingTop: "16px",
    }}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
```

- [ ] **Step 3: Fix the navbar seam**

In `app/(main)/_components/navbar.tsx` (around line 63), change
`style={{ color: "var(--ink-muted)" }}` → `style={{ color: "var(--tv-text-soft)" }}`.
This is the only `--ink` reference in the file.

- [ ] **Step 4: Delete debris (all untracked — verify then rm)**

```bash
git ls-files | grep -E "\.tmp\." && echo "STOP - tracked tmp file found" || true
rm -f "app/(main)/dashboard/_components/StrategyTable.tsx.tmp.11024.1778307371534" \
      app/globals.css.tmp.* \
      app/_components/algorobos/algorobos.css.tmp.*
```

- [ ] **Step 5: Gates (full)**

Run: `grep -rnE -- "--ink|--gold|myGreen|myYellow|myRed|rgba\(82,229,163|rgba\(20,16,6|rgba\(40,180,130|#4e3c0a|#50ba60|#b84c28|#34d18c|#7a6840|IM Fell|ornament-rule|shadow-gold|font-display|font-serif" "app/(main)/marketplace/" "app/(main)/backtests/" "app/(main)/archive/" components/Loader.tsx components/ui/card.tsx "app/(main)/_components/navbar.tsx"` → no matches.
Run: `npm run test` → 4 files, 44 tests pass.
Run: `npm run build` → success.

- [ ] **Step 6: Commit**

```bash
git add components/Loader.tsx components/ui/card.tsx "app/(main)/_components/navbar.tsx"
git commit -m "ppa(task4): Loader/Card/navbar to tv tokens; sed-debris removed"
```

---

### Task 5: End-to-end browser verification (controller-run)

**Files:** none (verification only; fix-forward commits if issues surface).

- [ ] **Step 1:** Kill any orphaned node on port 3000 first (Deploy Gotchas), then `npm run dev` (background), wait for Ready on port 3000.
- [ ] **Step 2:** Walk `/backtests`, `/archive`, `/marketplace` in dark theme: headers/subtitles render, tables/cards on tv panels, PnL colors correct (backtests has real reports; archive has the Funding Pips rows), marketplace deploy expand → account select shows "— Deployed" disabled options → Cancel (do NOT confirm a deploy).
- [ ] **Step 3:** Toggle light theme, re-walk all three. No jade borders, no parchment, no serif italics anywhere.
- [ ] **Step 4:** Screenshot each tab in both themes (6 shots), save to disk for the user.
- [ ] **Step 5:** Kill the dev server (and verify port 3000 released). Do NOT merge or push — user decision.
