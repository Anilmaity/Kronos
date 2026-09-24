# FOUNDATION — XAU/USD 16-Month Market-Structure Study

## CRITICAL DATA REALITY

The feed spans 2025-01-01 .. 2026-05-19 but is **discontinuous**. A ~233-day hole (2025-04-01 .. 2025-11-19) splits it into TWO segments. **Never analyze structure across the gap** — treat A and B as separate regimes.

### segA
- Span: 2025-01-01 .. 2025-03-30  (76 daily bars)
- Open 2625 -> Close 3089; Low 2615 / High 3098 (range 483 pts, 18.5%)
- Zigzag pivots: {'primary': 2, 'secondary': 4, 'minor': 32}

### segB
- Span: 2025-11-19 .. 2026-05-19  (155 daily bars)
- Open 4077 -> Close 4550; Low 4022 / High 5602 (range 1580 pts, 39.3%)
- Zigzag pivots: {'primary': 17, 'secondary': 51, 'minor': 125}

## Macro context (daily, continuous incl. the gap)
- At 2025-01-02: TNX 4.57 | DXY 109.4 | VIX 17.9
- At 2025-03-28: TNX 4.26 | DXY 104.0 | VIX 21.6
- At 2025-11-19: TNX 4.13 | DXY 100.2 | VIX 23.7
- At 2026-01-28 (peak): TNX 4.25 | DXY 96.4 | VIX 16.4
- At 2026-05-18: TNX 4.62 | DXY 99.0 | VIX 17.8

## Artifacts (all paths relative to MarketStructure/)
- `data/daily_<seg>.csv`, `data/h4_<seg>.csv`, `data/weekly_<seg>.csv`
- `data/zigzag_<seg>_<primary|secondary|minor>.csv` (columns: date, price, kind[H/L]); thresholds {'primary': 6.0, 'secondary': 3.0, 'minor': 1.5}
- `data/macro_daily.csv` (TNX, DXY, VIX, EURUSD)
- `charts/master_segA.png`, `charts/master_segB.png`, `charts/master_interactive.html`