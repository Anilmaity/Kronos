# Signals Page — Calendar View + tv-Token Migration

**Date:** 2026-08-01
**Status:** Approved (brainstorm 2026-08-01)
**Repos touched:** kronos_frontend only — no backend change, no box deploy.

## What

Add a month-calendar view to `/signals` showing per-day signal counts split by
status, with day drill-down into the existing signals table — and migrate the
whole page from legacy styling to the `--tv-*` token system (its pending pixel
pass), so calendar, chips, and table match Reports/Manager in both themes.

## Why

The signals table is a flat latest-500 list; there is no way to see gate
activity over time (how many signals fired, how many the entry gates rejected,
which days were busy). The Reports PnL calendar proved the month-grid pattern;
signals get the same navigator.

## Decisions (locked in brainstorm)

1. **Day cells: status split** — up to three small count chips per day:
   PLACED (in `--tv-up`), REJECTED (in `--tv-down`), FIRED (accent/amber).
   Empty days render blank.
2. **Layout: calendar + day drill-down** — calendar sits above the table.
   Clicking a day selects it (ring highlight) and filters the table to that
   day; clicking again or a "× <day>" clear chip deselects. No view toggle.
3. **Styling: full tv-token migration** — the page's title row, chips, states,
   table, and the new calendar all move to `--tv-*` tokens. No legacy
   `--ink`/mint rgba values remain on the page.

## Data layer (Approach A — frontend-only)

The existing `allStrategySignal` GraphQL query already supports everything
needed: `since: DateTime`, `until: DateTime`, `status`, `limit` (default 500,
no server cap), resolver ordered `-signal_at`.

- On month change (and initial load), fetch the visible month **once**:
  `allStrategySignal(since: <monthStartUtc>, until: <monthEndUtc>, limit: 5000)`
  — **no status arg**. All filtering below happens client-side on this dataset.
- Status chips (ALL / FIRED / PLACED / REJECTED) filter both the calendar
  counts and the table rows, instantly, without refetch.
- Day selection filters the table to that day's rows (post-chip-filter).
- Known bound: a month with more than 5,000 signals would undercount. Current
  volume is roughly two orders of magnitude below this; accepted.

### Time math (IST days, matching Reports)

`StrategySignal.signal_at` is correct UTC (unlike Order/Position
`created_at` — see Database Seam note). Day bucketing matches the Reports
calendar: **IST calendar days**.

- Day key: `signalAt` epoch + 5 h 30 m → `YYYY-MM-DD` via UTC accessors.
- Month fetch window: IST month bounds converted to UTC —
  `since` = 1st 00:00 IST = **18:30 UTC on the last day of the previous
  month**; `until` = last day 23:59:59.999 IST = 18:29:59.999 UTC on the
  month's last day.
- Rows with null `signalAt`: excluded from the calendar and from day
  drill-down; still listed in the table when no day is selected (sorted last).

Why aware UTC `since`/`until` params are safe against this backend: Django on
Postgres creates `DateTimeField` columns as `timestamptz` and the engine
writes aware IST instants, so comparison is exact-instant despite the
backend's `USE_TZ = False` — do not change `signal_at` to a naive column
without revisiting this window math.

## Components

```
app/(main)/signals/_components/
  main.tsx            — rework: month state, single month fetch, chip +
                        day filters, summary line, tv-token restyle
  SignalMonthGrid.tsx — NEW: month grid adapted from reports/MonthGrid.tsx
```

### `SignalMonthGrid.tsx` (new)

- Reuses the Reports grid math verbatim: Monday-start `buildWeeks`, `dateKey`
  with UTC accessors, string-key cell matching (copy, not import — payload
  types differ; keep the DST-safety comment).
- **No Week-totals column** (7 columns, not 8).
- Props: `days: Record<string, {placed: number; rejected: number; fired: number}>`,
  `year`, `month`, `selectedDay: string | null`, `onSelectDay(key | null)`.
  The `days` payload is already chip-filtered by the parent — the grid is a
  dumb renderer plus click reporting.
- Cell: day number (soft), then up to three count chips (`3 P` / `5 R` /
  `1 F` styled with tv up/down/accent). Selected day gets an accent ring;
  out-of-month cells dimmed exactly like Reports.
- Panel styling identical to Reports: `--tv-surface`, `--tv-border`,
  radius 8.

### `main.tsx` (rework)

- State: `year/month` (defaults: current IST month), `signals` (month
  dataset), `statusFilter`, `selectedDay`, `loading`, `error`.
- Header row: "Strategy Signals" title (tv type ramp), summary line
  ("142 signals — 18 placed / 96 rejected / 28 fired"; always the **full
  unfiltered month** breakdown, so it stays a stable reference while chips
  filter the calendar/table below), status chips (tv pill styling), month
  strip `‹ August 2026 ›` (same control as Reports).
- Month navigation triggers refetch; chip/day changes never do.
- Selected-day indicator: "× Fri 01 Aug" clear chip next to the summary.
- Table: same nine columns; restyled to tv tokens — surface/border, soft
  header text, `--tv-up`/`--tv-down` side colors; status colors PLACED=up,
  REJECTED=down, FIRED=accent. Shows month rows (newest first), or the
  selected day's rows. Empty/loading/error states restyled to tv panels
  ("No signals in <Month>" for an empty month).

## Error handling

- Fetch failure: existing pattern — `middleware(err)` (auth redirect) + error
  panel with message; calendar and table both hidden behind the error state.
- Month with zero signals: calendar renders (all cells blank) + empty-state
  panel below.

## Testing & verification

- `npm run build` green (lint + types) before any push.
- Drive on the dev server against prod data (`npm run dev`, logged in):
  chip filtering updates calendar + table together; day click filters and
  clears; month navigation across a boundary (July ↔ August) refetches and
  re-buckets correctly; IST edge — a signal near 00:00 IST lands on the IST
  day, not the UTC day; both themes via the navbar toggle.
- No backend tests: no backend change.

## Out of scope

- Backend `signalCalendar` aggregate query (Approach B — revisit only if
  month volume approaches the 5,000 cap).
- Other legacy tabs' pixel passes (accounts, marketplace, backtests…).
- Any change to signal generation or the `allStrategySignal` resolver.
