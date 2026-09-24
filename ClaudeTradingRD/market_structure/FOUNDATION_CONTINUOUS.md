# FOUNDATION (CONTINUOUS) — XAU/USD 16-Month Market-Structure Study

## DATA REALITY (updated)
The TimescaleDB feed was backfilled to a **continuous** series. Gold and silver now
both span **2025-01-01 → 2026-05-22 with NO internal gap** (432 daily bars each; only
normal 2–3 day weekend/holiday breaks). The earlier 233-day hole is GONE. **Analyze the
whole 16 months as ONE regime** — do NOT split into segments.

- Gold: 2615 (2025-01-06) → all-time high **5602 (2026-01-28)** → 4453 (current). One
  large bull market (+114% low-to-high) culminating in a blow-off top, then a correction.
- Silver: 28.94 → peak **121.67 (2026-01-29, one day after gold's top)** → ~75. More
  volatile; use as the confirming average / SMT instrument.

## Gold PRIMARY pivots (6% zigzag) — the backbone (analyze the whole path)
| Date | Price | Kind | Leg |
|---|---|---|---|
| 2025-01-06 | 2615 | L | cycle start |
| 2025-04-02 | 3168 | H | +21% |
| 2025-04-07 | 2957 | L | -7% |
| 2025-04-22 | 3500 | H | +18% |
| 2025-05-15 | 3121 | L | -11% |
| 2025-06-15 | 3452 | H | +11% |
| 2025-06-29 | 3244 | L | -6% |
| 2025-10-20 | 4381 | H | +35% (summer rally) |
| 2025-10-28 | 3886 | L | -11% |
| 2025-12-26 | 4550 | H | +17% |
| 2025-12-31 | 4274 | L | -6% |
| 2026-01-28 | 5602 | H | +31% BLOW-OFF TOP |
| 2026-02-02 | 4402 | L | -21% |
| 2026-03-02 | 5420 | H | lower high |
| 2026-03-23 | 4099 | L | -24% markdown low |
| 2026-04-17 | 4891 | H | +19% |
| 2026-05-04 | 4501 | L | |
| 2026-05-12 | 4774 | H | |
| 2026-05-20 | 4453 | L | current |
(Note: 2026-01-29 5097↔5595 intraday flip is blow-off noise; 5602 is THE peak.)

## Macro at key pivots (TNX=US10Y%, DXY, VIX) — continuous, drives the "why"
| Date | Gold | TNX | DXY | VIX | note |
|---|---|---|---|---|---|
| 2025-01-06 | 2615 | 4.62 | 108.3 | 16 | start |
| 2025-04-22 | 3500 | 4.39 | 98.9 | **30.6** | April tariff/risk-off spike; gold haven bid |
| 2025-05-15 | 3121 | 4.45 | 100.9 | 17.8 | DXY bounce → gold pullback |
| 2025-06-29 | 3244 | 4.28 | 97.4 | 16.3 | |
| 2025-10-20 | 4381 | **3.99** | 98.6 | 18.2 | yields at lows → summer melt-up |
| 2025-12-26 | 4550 | 4.14 | 98.0 | **13.6** | complacency |
| 2026-01-28 | **5602** | 4.25 | **96.4** | 16.4 | DXY 16-mo low + low VIX = blow-off |
| 2026-03-23 | 4099 | 4.33 | 98.9 | **26.1** | fear spike + $ bounce = markdown |
| 2026-05-20 | 4453 | **4.57** | 99.1 | 17.4 | yields rising = headwind |

## Artifacts (paths relative to MarketStructure/)
- `data/cont_daily.csv`, `data/cont_h4.csv` (2215 bars), `data/cont_weekly.csv` — gold OHLC (continuous). 'ticks' = volume proxy.
- `data/cont_zigzag_primary.csv` (27 pivots), `cont_zigzag_secondary.csv` (93), `cont_zigzag_minor.csv` (289) — columns date,price,kind[H/L]. Map to Dow primary/secondary/minor.
- `data/cont_silver_daily.csv`, `data/cont_silver_zigzag_primary.csv` — silver (confirming average / SMT).
- `data/macro_daily.csv` — TNX, DXY, VIX, EURUSD (continuous incl. full range).
- `charts/CONTINUOUS_16mo_daily.png`, `charts/CONTINUOUS_16mo_interactive.html`.
