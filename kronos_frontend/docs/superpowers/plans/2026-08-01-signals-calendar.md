# Signals Calendar + tv-Token Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a status-split month calendar with day drill-down to `/signals`, migrating the whole page to `--tv-*` tokens.

**Architecture:** All date/bucketing logic lives in a pure module (`signalCalendar.ts`) unit-tested with vitest; `SignalMonthGrid.tsx` is a thin renderer over it; `main.tsx` fetches one month per navigation via the existing `allStrategySignal(since, until, limit)` query and derives calendar + table client-side. Frontend-only — no backend change.

**Tech Stack:** Next.js 14 App Router, Apollo Client, vitest (jsdom), lucide-react icons, shadcn Button, `--tv-*` CSS tokens.

**Spec:** `docs/superpowers/specs/2026-08-01-signals-calendar-design.md`

## Global Constraints

- Branch: `feat/signals-calendar` (already created). **Never push `main`** — pushing main ships to Netlify.
- No backend changes of any kind; the GraphQL query is `allStrategySignal` exactly as deployed.
- Styling: `--tv-*` tokens only; no `--ink*` vars or `rgba(82,229,163,…)` mint values may remain in `app/(main)/signals/` after Task 3.
- FIRED accent color is the literal `#d4a648` (exported once from `signalCalendar.ts`); PLACED = `var(--tv-up)`; REJECTED = `var(--tv-down)`.
- Day bucketing is IST (`UTC+5:30`); month fetch window is the IST month converted to UTC.
- Month fetch `limit: 5000`; statuses counted in cells are exactly `PLACED`, `REJECTED`, `FIRED`.
- Test command: `npx vitest run app/\(main\)/signals/_components/signalCalendar.test.ts` (bash: escape parens). Full check: `npm run test` then `npm run build`.

---

### Task 1: Pure calendar logic module (`signalCalendar.ts`)

**Files:**
- Create: `app/(main)/signals/_components/signalCalendar.ts`
- Test: `app/(main)/signals/_components/signalCalendar.test.ts`

**Interfaces:**
- Consumes: nothing (pure module, no imports).
- Produces (used by Tasks 2–3):
  - `interface CalendarSignal { signalAt: string | null; status: string }`
  - `interface DayCounts { placed: number; rejected: number; fired: number }`
  - `interface MonthSummary { total: number; placed: number; rejected: number; fired: number }`
  - `interface DayCell { key: string; dayNumber: number; inMonth: boolean }`
  - `type StatusFilter = "ALL" | "FIRED" | "PLACED" | "REJECTED"`
  - `const FIRED_COLOR = "#d4a648"`
  - `istDayKey(signalAt: string | null): string | null`
  - `monthWindowUtc(year: number, month: number): { since: string; until: string }`
  - `bucketByDay(signals: CalendarSignal[], filter: StatusFilter): Record<string, DayCounts>`
  - `monthSummary(signals: CalendarSignal[]): MonthSummary`
  - `buildWeeks(year: number, month: number): DayCell[][]`
  - `dayLabel(key: string): string` — `"2026-08-01"` → `"Sat 01 Aug"`

- [ ] **Step 1: Write the failing tests**

Create `app/(main)/signals/_components/signalCalendar.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import {
  buildWeeks,
  bucketByDay,
  dayLabel,
  istDayKey,
  monthSummary,
  monthWindowUtc,
  CalendarSignal,
} from "./signalCalendar";

describe("istDayKey", () => {
  it("maps a UTC instant to its IST calendar day", () => {
    // 18:30:00Z is exactly 00:00 IST the NEXT day
    expect(istDayKey("2026-07-31T18:30:00.000Z")).toBe("2026-08-01");
  });
  it("keeps instants just before the IST midnight on the same IST day", () => {
    expect(istDayKey("2026-07-31T18:29:59.999Z")).toBe("2026-07-31");
  });
  it("returns null for null and unparseable input", () => {
    expect(istDayKey(null)).toBeNull();
    expect(istDayKey("not-a-date")).toBeNull();
  });
});

describe("monthWindowUtc", () => {
  it("covers the IST month for August 2026", () => {
    expect(monthWindowUtc(2026, 8)).toEqual({
      since: "2026-07-31T18:30:00.000Z",
      until: "2026-08-31T18:29:59.999Z",
    });
  });
  it("crosses the year boundary for January", () => {
    expect(monthWindowUtc(2026, 1)).toEqual({
      since: "2025-12-31T18:30:00.000Z",
      until: "2026-01-31T18:29:59.999Z",
    });
  });
});

const sig = (signalAt: string | null, status: string): CalendarSignal => ({
  signalAt,
  status,
});

describe("bucketByDay", () => {
  const signals: CalendarSignal[] = [
    sig("2026-08-01T04:00:00.000Z", "PLACED"),   // Aug 1 IST
    sig("2026-08-01T05:00:00.000Z", "REJECTED"), // Aug 1 IST
    sig("2026-08-01T06:00:00.000Z", "REJECTED"), // Aug 1 IST
    sig("2026-08-01T18:30:00.000Z", "FIRED"),    // Aug 2 IST (rolls over)
    sig(null, "PLACED"),                          // no timestamp - excluded
    sig("2026-08-01T07:00:00.000Z", "WEIRD"),    // unknown status - no chip
  ];

  it("splits counts by status per IST day", () => {
    expect(bucketByDay(signals, "ALL")).toEqual({
      "2026-08-01": { placed: 1, rejected: 2, fired: 0 },
      "2026-08-02": { placed: 0, rejected: 0, fired: 1 },
    });
  });

  it("applies the status filter", () => {
    expect(bucketByDay(signals, "REJECTED")).toEqual({
      "2026-08-01": { placed: 0, rejected: 2, fired: 0 },
    });
  });
});

describe("monthSummary", () => {
  it("counts every row in total, known statuses in their buckets", () => {
    const signals: CalendarSignal[] = [
      sig("2026-08-01T04:00:00.000Z", "PLACED"),
      sig("2026-08-01T05:00:00.000Z", "REJECTED"),
      sig(null, "FIRED"),
      sig("2026-08-01T07:00:00.000Z", "WEIRD"),
    ];
    expect(monthSummary(signals)).toEqual({
      total: 4,
      placed: 1,
      rejected: 1,
      fired: 1,
    });
  });
});

describe("buildWeeks", () => {
  it("builds Monday-start weeks covering August 2026", () => {
    const weeks = buildWeeks(2026, 8);
    expect(weeks).toHaveLength(6);
    expect(weeks.every((w) => w.length === 7)).toBe(true);
    // Aug 1 2026 is a Saturday -> 5 leading July cells
    expect(weeks[0][0]).toEqual({
      key: "2026-07-27",
      dayNumber: 27,
      inMonth: false,
    });
    expect(weeks[0][5]).toEqual({
      key: "2026-08-01",
      dayNumber: 1,
      inMonth: true,
    });
    expect(weeks[5][6].key).toBe("2026-09-06");
  });
});

describe("dayLabel", () => {
  it("renders a short weekday-day-month label", () => {
    expect(dayLabel("2026-08-01")).toBe("Sat 01 Aug");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run "app/(main)/signals/_components/signalCalendar.test.ts"`
Expected: FAIL — cannot resolve `./signalCalendar`.

- [ ] **Step 3: Write the implementation**

Create `app/(main)/signals/_components/signalCalendar.ts`:

```ts
// Pure calendar logic for the signals page - no React, no GraphQL, unit-tested.
// Day bucketing is IST (UTC+5:30), matching the Reports PnL calendar.

export interface CalendarSignal {
  signalAt: string | null;
  status: string;
}

export interface DayCounts {
  placed: number;
  rejected: number;
  fired: number;
}

export interface MonthSummary {
  total: number;
  placed: number;
  rejected: number;
  fired: number;
}

export interface DayCell {
  key: string; // "YYYY-MM-DD"
  dayNumber: number;
  inMonth: boolean;
}

export type StatusFilter = "ALL" | "FIRED" | "PLACED" | "REJECTED";

// The tv token set has no amber; FIRED keeps the page's historical amber.
export const FIRED_COLOR = "#d4a648";

const IST_OFFSET_MS = (5 * 60 + 30) * 60 * 1000;

const pad2 = (n: number): string => String(n).padStart(2, "0");

// "YYYY-MM-DD" IST calendar day for a UTC timestamp string; null when the
// timestamp is missing or unparseable (such rows never reach the calendar).
export const istDayKey = (signalAt: string | null): string | null => {
  if (!signalAt) return null;
  const t = Date.parse(signalAt);
  if (Number.isNaN(t)) return null;
  const d = new Date(t + IST_OFFSET_MS);
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(
    d.getUTCDate()
  )}`;
};

// UTC fetch window covering the IST month: [1st 00:00 IST, next month 00:00 IST).
// graphene.DateTime on the backend parses these ISO-8601 strings directly.
export const monthWindowUtc = (
  year: number,
  month: number
): { since: string; until: string } => {
  const startMs = Date.UTC(year, month - 1, 1) - IST_OFFSET_MS;
  const endMs = Date.UTC(year, month, 1) - IST_OFFSET_MS - 1;
  return {
    since: new Date(startMs).toISOString(),
    until: new Date(endMs).toISOString(),
  };
};

const matchesFilter = (s: CalendarSignal, f: StatusFilter): boolean =>
  f === "ALL" || s.status === f;

export const bucketByDay = (
  signals: CalendarSignal[],
  filter: StatusFilter
): Record<string, DayCounts> => {
  const out: Record<string, DayCounts> = {};
  for (const s of signals) {
    if (!matchesFilter(s, filter)) continue;
    const key = istDayKey(s.signalAt);
    if (!key) continue;
    if (!out[key]) out[key] = { placed: 0, rejected: 0, fired: 0 };
    if (s.status === "PLACED") out[key].placed += 1;
    else if (s.status === "REJECTED") out[key].rejected += 1;
    else if (s.status === "FIRED") out[key].fired += 1;
  }
  return out;
};

// Always the full unfiltered month - the header's stable reference line.
export const monthSummary = (signals: CalendarSignal[]): MonthSummary => {
  const out: MonthSummary = { total: 0, placed: 0, rejected: 0, fired: 0 };
  for (const s of signals) {
    out.total += 1;
    if (s.status === "PLACED") out.placed += 1;
    else if (s.status === "REJECTED") out.rejected += 1;
    else if (s.status === "FIRED") out.fired += 1;
  }
  return out;
};

// All date math below uses UTC accessors (Date.UTC / getUTC*) on purpose -
// day keys are plain "YYYY-MM-DD" strings with no timezone attached, and
// mixing in local-time Date methods would drift the grid by a day around
// DST/timezone boundaries. (Same approach as reports/MonthGrid.tsx.)
const dateKey = (y: number, m0: number, d: number): string => {
  const dt = new Date(Date.UTC(y, m0, d));
  return `${dt.getUTCFullYear()}-${pad2(dt.getUTCMonth() + 1)}-${pad2(
    dt.getUTCDate()
  )}`;
};

// Full Monday-start week rows covering the month, including dimmed
// leading/trailing cells belonging to adjacent months.
export const buildWeeks = (year: number, month: number): DayCell[][] => {
  const monthIndex = month - 1;
  const firstOfMonth = new Date(Date.UTC(year, monthIndex, 1));
  const leading = (firstOfMonth.getUTCDay() + 6) % 7; // Mon=0 .. Sun=6
  const daysInMonth = new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate();
  const totalCells = Math.ceil((leading + daysInMonth) / 7) * 7;

  const cells: DayCell[] = [];
  for (let i = 0; i < totalCells; i += 1) {
    const dayOffset = i - leading + 1;
    const dt = new Date(Date.UTC(year, monthIndex, dayOffset));
    cells.push({
      key: dateKey(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate()),
      dayNumber: dt.getUTCDate(),
      inMonth: dayOffset >= 1 && dayOffset <= daysInMonth,
    });
  }

  const weeks: DayCell[][] = [];
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7));
  }
  return weeks;
};

// "2026-08-01" -> "Sat 01 Aug" (for the selected-day clear chip).
export const dayLabel = (key: string): string => {
  const [y, m, d] = key.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  const weekday = dt.toLocaleString("en-US", {
    weekday: "short",
    timeZone: "UTC",
  });
  const monthName = dt.toLocaleString("en-US", {
    month: "short",
    timeZone: "UTC",
  });
  return `${weekday} ${pad2(d)} ${monthName}`;
};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run "app/(main)/signals/_components/signalCalendar.test.ts"`
Expected: PASS — 10 tests.

Then run the full suite to check nothing else broke:
`npm run test` — Expected: 4 files, 44 tests, all pass.

- [ ] **Step 5: Commit**

```bash
git add "app/(main)/signals/_components/signalCalendar.ts" "app/(main)/signals/_components/signalCalendar.test.ts"
git commit -m "sig(task1): pure IST calendar logic for signals page"
```

---

### Task 2: `SignalMonthGrid` component

**Files:**
- Create: `app/(main)/signals/_components/SignalMonthGrid.tsx`

**Interfaces:**
- Consumes (from Task 1): `buildWeeks`, `DayCounts`, `FIRED_COLOR`.
- Produces (used by Task 3):

```tsx
interface SignalMonthGridProps {
  days: Record<string, DayCounts>; // already chip-filtered by the parent
  year: number;
  month: number;
  selectedDay: string | null;
  onSelectDay: (key: string | null) => void;
}
export default SignalMonthGrid;
```

There is no test runner story for JSX in this repo (no testing-library); the
grid is a dumb renderer over Task 1's tested math. Verification is the type
gate (`npm run build`) here plus the browser drive in Task 4.

- [ ] **Step 1: Write the component**

Create `app/(main)/signals/_components/SignalMonthGrid.tsx`:

```tsx
"use client";

import React from "react";

import {
  buildWeeks,
  DayCounts,
  FIRED_COLOR,
} from "./signalCalendar";

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const panelStyle: React.CSSProperties = {
  background: "var(--tv-surface)",
  border: "1px solid var(--tv-border)",
  borderRadius: "8px",
};

const countChip = (color: string): React.CSSProperties => ({
  fontSize: "11px",
  fontWeight: 700,
  color,
  lineHeight: 1.2,
});

interface SignalMonthGridProps {
  days: Record<string, DayCounts>; // already chip-filtered by the parent
  year: number;
  month: number;
  selectedDay: string | null;
  onSelectDay: (key: string | null) => void;
}

const SignalMonthGrid: React.FC<SignalMonthGridProps> = ({
  days,
  year,
  month,
  selectedDay,
  onSelectDay,
}) => {
  const weeks = buildWeeks(year, month);

  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-[640px]">
        <div className="grid grid-cols-7 gap-1 mb-1">
          {WEEKDAY_LABELS.map((label) => (
            <div
              key={label}
              className="text-center text-xs font-semibold py-1"
              style={{ color: "var(--tv-text-soft)" }}
            >
              {label}
            </div>
          ))}
        </div>

        {weeks.map((week, wi) => (
          <div key={wi} className="grid grid-cols-7 gap-1 mb-1">
            {week.map((cell) => {
              const counts = days[cell.key];
              const selected = selectedDay === cell.key;
              const clickable = cell.inMonth && !!counts;
              return (
                <button
                  type="button"
                  key={cell.key}
                  disabled={!clickable}
                  onClick={() => onSelectDay(selected ? null : cell.key)}
                  className="flex flex-col items-start gap-0.5 p-2 min-h-[64px] text-left"
                  style={{
                    ...panelStyle,
                    opacity: cell.inMonth ? 1 : 0.35,
                    cursor: clickable ? "pointer" : "default",
                    outline: selected
                      ? "2px solid var(--tv-accent)"
                      : "none",
                    outlineOffset: "-2px",
                  }}
                >
                  <span
                    className="text-xs"
                    style={{ color: "var(--tv-text-soft)" }}
                  >
                    {cell.dayNumber}
                  </span>
                  {counts && counts.placed > 0 && (
                    <span style={countChip("var(--tv-up)")}>
                      {counts.placed} P
                    </span>
                  )}
                  {counts && counts.rejected > 0 && (
                    <span style={countChip("var(--tv-down)")}>
                      {counts.rejected} R
                    </span>
                  )}
                  {counts && counts.fired > 0 && (
                    <span style={countChip(FIRED_COLOR)}>
                      {counts.fired} F
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

export default SignalMonthGrid;
```

- [ ] **Step 2: Type-check via build**

Run: `npm run build`
Expected: build succeeds (component compiles; not yet imported anywhere).

- [ ] **Step 3: Commit**

```bash
git add "app/(main)/signals/_components/SignalMonthGrid.tsx"
git commit -m "sig(task2): SignalMonthGrid - status-split day cells over tested grid math"
```

---

### Task 3: `main.tsx` rework — month fetch, filters, drill-down, tv restyle

**Files:**
- Modify: `app/(main)/signals/_components/main.tsx` (full rewrite)

**Interfaces:**
- Consumes (Task 1): `CalendarSignal`, `StatusFilter`, `FIRED_COLOR`, `bucketByDay`, `monthSummary`, `monthWindowUtc`, `istDayKey`, `dayLabel`.
- Consumes (Task 2): `SignalMonthGrid` default export with the props above.
- Consumes (existing): `client`, `middleware`, `fmtNum`, `fmtTime`, shadcn `Button`, `ChevronLeft`/`ChevronRight` from lucide-react.
- Produces: the `/signals` page (default export `SignalsPage`) — nothing downstream.

- [ ] **Step 1: Rewrite main.tsx**

Replace the entire contents of `app/(main)/signals/_components/main.tsx` with:

```tsx
/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { gql } from "@apollo/client";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { fmtNum, fmtTime } from "@/utils/format";
import { Button } from "@/components/ui/button";

import SignalMonthGrid from "./SignalMonthGrid";
import {
  bucketByDay,
  dayLabel,
  FIRED_COLOR,
  istDayKey,
  monthSummary,
  monthWindowUtc,
  StatusFilter,
} from "./signalCalendar";

interface StrategySignal {
  id: string;
  symbol: string;
  side: string;
  entryPrice: string | null;
  stopLoss: string | null;
  takeProfit: string | null;
  reason: string | null;
  status: string;
  rejectionReason: string | null;
  signalAt: string | null;
  strategyName: string | null;
  strategyId: string | null;
  positionId: string | null;
}

const QUERY = gql`
  query AllStrategySignal($since: DateTime, $until: DateTime, $limit: Int) {
    allStrategySignal(since: $since, until: $until, limit: $limit) {
      id
      symbol
      side
      entryPrice
      stopLoss
      takeProfit
      reason
      status
      rejectionReason
      signalAt
      strategyName
      strategyId
      positionId
    }
  }
`;

const STATUS_FILTERS: StatusFilter[] = ["ALL", "FIRED", "PLACED", "REJECTED"];

// Known bound (spec): a month with >5000 signals would undercount; current
// volume is ~2 orders of magnitude below this.
const MONTH_LIMIT = 5000;

// Month navigation clamp, same policy as the Reports calendar.
const MIN_YEAR = 2026;
const MIN_MONTH = 1;
const MAX_YEAR = new Date().getFullYear() + 1;
const toIndex = (year: number, month: number) => year * 12 + (month - 1);
const fromIndex = (idx: number) => ({
  year: Math.floor(idx / 12),
  month: (idx % 12) + 1,
});
const MIN_IDX = toIndex(MIN_YEAR, MIN_MONTH);
const MAX_IDX = toIndex(MAX_YEAR, 12);

const monthLabelText = (year: number, month: number) =>
  new Date(year, month - 1, 1).toLocaleString("en-US", {
    month: "long",
    year: "numeric",
  });

const panelStyle: React.CSSProperties = {
  background: "var(--tv-surface)",
  border: "1px solid var(--tv-border)",
  borderRadius: "8px",
};

const soft: React.CSSProperties = { color: "var(--tv-text-soft)" };

const chipStyle = (selected: boolean): React.CSSProperties => ({
  fontSize: "12px",
  fontWeight: 600,
  borderRadius: "4px",
  padding: "5px 12px",
  border: `1px solid ${selected ? "var(--tv-up)" : "var(--tv-border)"}`,
  color: selected ? "var(--tv-up)" : "var(--tv-text-soft)",
  cursor: "pointer",
  background: "transparent",
});

const sideColor = (side: string): string =>
  side === "BUY" ? "var(--tv-up)" : side === "SELL" ? "var(--tv-down)" : "var(--tv-text-soft)";

const statusColor = (status: string): string =>
  status === "PLACED"
    ? "var(--tv-up)"
    : status === "REJECTED"
    ? "var(--tv-down)"
    : status === "FIRED"
    ? FIRED_COLOR
    : "var(--tv-text-soft)";

// Stamped result: rendering only trusts a payload fetched for the month
// currently on screen (same race-guard pattern as the Reports calendar).
interface MonthResult {
  signals: StrategySignal[];
  forYear: number;
  forMonth: number;
}

const SignalsPage: React.FC = () => {
  const [year, setYear] = useState<number>(() => new Date().getFullYear());
  const [month, setMonth] = useState<number>(() => new Date().getMonth() + 1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const [result, setResult] = useState<MonthResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const requestIdRef = useRef(0);

  const fetchMonth = useCallback(async () => {
    const requestId = (requestIdRef.current += 1);
    const reqYear = year;
    const reqMonth = month;
    const { since, until } = monthWindowUtc(reqYear, reqMonth);
    setLoading(true);
    try {
      const { data } = await client.query({
        query: QUERY,
        variables: { since, until, limit: MONTH_LIMIT },
        fetchPolicy: "no-cache",
      });
      if (requestIdRef.current !== requestId) return; // superseded
      setResult({
        signals: data?.allStrategySignal ?? [],
        forYear: reqYear,
        forMonth: reqMonth,
      });
      setError(null);
      setLoading(false);
    } catch (err: any) {
      if (requestIdRef.current !== requestId) return; // superseded
      middleware(err);
      setError(err?.message ?? "Failed to load signals");
      setLoading(false);
    }
  }, [year, month]);

  useEffect(() => {
    fetchMonth();
  }, [year, month]);

  // Day selection never survives a month change.
  const navigate = (delta: number) => {
    const idx = Math.min(MAX_IDX, Math.max(MIN_IDX, toIndex(year, month) + delta));
    const next = fromIndex(idx);
    setSelectedDay(null);
    setYear(next.year);
    setMonth(next.month);
  };
  const atMin = toIndex(year, month) <= MIN_IDX;
  const atMax = toIndex(year, month) >= MAX_IDX;

  const stampMatches =
    result !== null && result.forYear === year && result.forMonth === month;
  const monthSignals = stampMatches ? result.signals : [];

  const summary = useMemo(() => monthSummary(monthSignals), [monthSignals]);
  const days = useMemo(
    () => bucketByDay(monthSignals, statusFilter),
    [monthSignals, statusFilter]
  );

  // Table rows: chip filter, then optional day drill-down. Null-signalAt
  // rows are excluded from day drill-down (they have no day) but listed
  // last in the month view.
  const tableRows = useMemo(() => {
    const filtered = monthSignals.filter(
      (s) => statusFilter === "ALL" || s.status === statusFilter
    );
    if (selectedDay) {
      return filtered.filter((s) => istDayKey(s.signalAt) === selectedDay);
    }
    const dated = filtered.filter((s) => s.signalAt !== null);
    const undated = filtered.filter((s) => s.signalAt === null);
    return [...dated, ...undated];
  }, [monthSignals, statusFilter, selectedDay]);

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex items-center justify-between w-full gap-4 flex-wrap">
        <div className="flex flex-col">
          <span className="text-base font-semibold">Strategy Signals</span>
          <span className="text-sm" style={soft}>
            {summary.total} signals — {summary.placed} placed /{" "}
            {summary.rejected} rejected / {summary.fired} fired
          </span>
        </div>
        <div className="flex items-center gap-1">
          {STATUS_FILTERS.map((f) => (
            <button
              type="button"
              key={f}
              onClick={() => setStatusFilter(f)}
              style={chipStyle(f === statusFilter)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-4 w-full px-4 py-4" style={panelStyle}>
        <div className="flex items-center gap-3 flex-wrap">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(-1)}
            disabled={atMin}
            aria-label="Previous month"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-semibold min-w-[140px] text-center">
            {monthLabelText(year, month)}
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(1)}
            disabled={atMax}
            aria-label="Next month"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          {selectedDay && (
            <button
              type="button"
              onClick={() => setSelectedDay(null)}
              style={chipStyle(true)}
              className="inline-flex items-center gap-1"
            >
              <X className="h-3 w-3" />
              {dayLabel(selectedDay)}
            </button>
          )}
        </div>

        {error && !loading && (
          <span className="text-sm" style={{ color: "var(--tv-down)" }}>
            {error}
          </span>
        )}

        {!error && (
          <div style={{ opacity: loading ? 0.6 : 1, transition: "opacity 150ms ease" }}>
            <SignalMonthGrid
              days={days}
              year={year}
              month={month}
              selectedDay={selectedDay}
              onSelectDay={setSelectedDay}
            />
          </div>
        )}
      </div>

      {!loading && !error && tableRows.length === 0 && (
        <div
          className="w-full flex items-center justify-center px-4 py-16 text-sm"
          style={{ ...panelStyle, ...soft }}
        >
          {selectedDay
            ? `No ${statusFilter === "ALL" ? "" : statusFilter.toLowerCase() + " "}signals on ${dayLabel(selectedDay)}`
            : `No signals in ${monthLabelText(year, month)}`}
        </div>
      )}

      {!error && tableRows.length > 0 && (
        <div className="w-full overflow-x-auto" style={panelStyle}>
          <div
            className="flex items-center w-full px-4 py-3 min-w-[1200px] text-xs font-semibold uppercase tracking-wider"
            style={{ ...soft, borderBottom: "1px solid var(--tv-border)" }}
          >
            <div className="w-[13%]">Time (IST)</div>
            <div className="w-[18%]">Strategy</div>
            <div className="w-[8%]">Symbol</div>
            <div className="w-[6%]">Side</div>
            <div className="w-[8%] text-end">Entry</div>
            <div className="w-[8%] text-end">SL</div>
            <div className="w-[8%] text-end">TP</div>
            <div className="w-[8%]">Status</div>
            <div className="w-[23%]">Reason</div>
          </div>

          {tableRows.map((s) => (
            <div
              key={s.id}
              className="flex items-center w-full px-4 py-3 min-w-[1200px] text-sm"
              style={{ borderBottom: "1px solid var(--tv-border)" }}
            >
              <div className="w-[13%] text-xs" style={soft}>
                {fmtTime(s.signalAt)}
              </div>
              <div className="w-[18%] truncate" title={s.strategyName ?? ""}>
                {s.strategyName ?? "—"}
              </div>
              <div className="w-[8%]">{s.symbol}</div>
              <div
                className="w-[6%] font-semibold"
                style={{ color: sideColor(s.side) }}
              >
                {s.side}
              </div>
              <div className="w-[8%] text-end">{fmtNum(s.entryPrice, 2)}</div>
              <div className="w-[8%] text-end">{fmtNum(s.stopLoss, 2)}</div>
              <div className="w-[8%] text-end">{fmtNum(s.takeProfit, 2)}</div>
              <div
                className="w-[8%] text-xs font-semibold"
                style={{ color: statusColor(s.status) }}
              >
                {s.status}
              </div>
              <div
                className="w-[23%] truncate text-xs"
                title={s.status === "REJECTED" ? s.rejectionReason ?? "" : s.reason ?? ""}
                style={soft}
              >
                {s.status === "REJECTED" ? s.rejectionReason ?? "—" : s.reason ?? "—"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SignalsPage;
```

- [ ] **Step 2: Verify no legacy styling remains**

Run: `grep -nE "var\(--ink|rgba\(82,229,163|rgba\(20,16,6|#4e3c0a|#50ba60|#b84c28|IM Fell" "app/(main)/signals/_components/main.tsx"`
Expected: no matches. (FIRED `#d4a648` lives only in `signalCalendar.ts`.)

- [ ] **Step 3: Full test + build gates**

Run: `npm run test` — Expected: 4 files, 44 tests pass.
Run: `npm run build` — Expected: build succeeds, `/signals` route listed.

- [ ] **Step 4: Commit**

```bash
git add "app/(main)/signals/_components/main.tsx"
git commit -m "sig(task3): month calendar + day drill-down + tv-token migration for /signals"
```

---

### Task 4: End-to-end browser verification

**Files:** none (verification only; fix-forward commits if issues surface).

**Interfaces:** consumes the finished page from Task 3.

- [ ] **Step 1: Start the dev server**

Run: `npm run dev` (background). Wait for `Ready`, then open
`http://localhost:3000/signals` in the browser (user session already logged
in from earlier sessions; if redirected to /login, ask the user to sign in).

- [ ] **Step 2: Verify against the spec checklist**

- Calendar renders the current month with status-split counts; summary line
  matches the visible chips' totals when ALL is selected.
- Clicking each status chip updates calendar counts and table rows together,
  with no network request (confirm via devtools/network or instant response).
- Clicking a day with signals filters the table to that day; the "× <day>"
  chip appears; clicking either clears it.
- Month navigation `‹ ›`: July 2026 shows July's signals (there were many);
  navigating back to August re-renders correctly; day selection resets on
  navigation.
- IST edge: find a signal timestamped after 18:30 UTC (evening US session)
  and confirm it lands on the NEXT IST calendar day in the grid.
- Theme toggle: both light and dark render correctly (no illegible text, no
  legacy mint/gold remnants).
- Empty state: navigate to a month with no signals (e.g. far past) — empty
  calendar + "No signals in <Month>" panel.

- [ ] **Step 3: Screenshot both themes for the user**

Capture `/signals` in dark and light (calendar + table visible), save to disk,
include paths in the report.

- [ ] **Step 4: Stop the dev server**

Kill the background dev-server task. Do NOT merge to `main` or push — that is
a user decision (pushing main ships to Netlify).
