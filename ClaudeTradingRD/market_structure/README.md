> **In the monorepo since 2026-09-24.** Copied from the Windows box
> `C:\Projects\PycharmProjects\personal\TradingSkills\MarketStructure` (built 2026-05-24).
> The four large Plotly `charts/*interactive*.html` files were left behind (regenerable);
> `data/*.parquet` is present locally but git-ignored. The `build_*.py` scripts still assume
> the original `TradingSkills/` layout (`ROOT/backtest/data`, `.venv/Scripts/python.exe`) and
> `pull_continuous.py` reads the retired TigerData DB — the saved `data/*.csv` are the usable
> inputs. `zigzag_pct()` from `build_foundation.py` is imported by `../plot_xau.py`.

# Gold (XAU/USD) 16-Month Market-Structure Study

Deep market-structure research on 16 months of XAU/USD, with **Dow Theory**, **AMD**,
and **SMC** applied *individually* as three separate lenses, a multi-scale **zigzag**,
**cycle identification with reasoning**, and **higher-timeframe verification charts**.

## ✅ Data is now CONTINUOUS (read first)
The TimescaleDB feed was backfilled mid-study to a **continuous** series. Gold and silver
now both span **2025-01-01 → 2026-05-22 with NO internal gap** (432 daily bars each).
The earlier 233-day hole is gone, so the study was **rebuilt on one continuous regime**.
The older two-segment artifacts are kept but **superseded** (they missed the summer-2025 cycle).

**The 16-month story:** one primary **bull market 2615 → all-time high 5602 (2026-01-28),
+114%**, built from stacked higher-highs/higher-lows (incl. a previously-hidden +35% summer
melt-up 3244→4381), climaxing in a **blow-off top**, then a **markdown to 4099** — which
landed within 0.23% of the master-range **equilibrium (4108)** — and a sideways correction to 4453.

## 📊 Verification charts (CURRENT) — `charts/`
- **`CONTINUOUS_16mo_daily.png`** — ⭐ full 16 months, Daily candles + zigzag + phase bands + equilibrium line + macro panel
- **`CONTINUOUS_16mo_interactive.html`** — zoomable Plotly of the whole continuous series
- **`WAVES_16mo_elliott.png`** / **`WAVES_16mo_interactive.html`** — Elliott Wave restructure: 5-wave impulse (extended 5th → 9 swings) + A-B-C flat to the 50% retrace
- **`WAVES_H4_subwaves.png`** — Primary count carried onto H4: each wave's sub-waves (5 per motive, 3 per corrective = 21 total)
- **`WAVES_lightweight.html`** — ⭐ single interactive TradingView Lightweight Charts view, H4 candles. **Primary 10%** zigzag skeleton (labelled (1)-(5)/A-B-C); **Sub = per-leg auto-threshold** (each leg's reversal % is auto-chosen to hit its Elliott target); **Minor 2%** (hugs price). Full count now textbook — impulse **W1=5, W2=3, W3=9 (extended 3rd), W4=3, W5=5** (per-leg %: 3.7/5.3/3.4/3.8/5.5) and correction **A=5, B=3, C=5**. A and C have no single-threshold clean 5 (their counts skip 4), so their i-ii-iii-iv is **forced** from representative H4 pivots (`LEG_OVERRIDE`; iii extended, wave-iv below wave-i → valid impulse). Each degree toggle-able; Fib lines; offline (uses `charts/lib/`). **Every pivot is an exact H4 wick** (271/271). Built via `build_lwc.py`.

## 🌊 Elliott Wave restructure — `analysis/WAVES_elliott.md`
Trends as 5 waves (9 when extended), corrections as A-B-C. Gold = clean 5-wave Primary
impulse 2615→5602 with an extended 5th (blow-off), then an A-B-C flat bottoming at 4099 =
the 50% Fib retrace (4108) — the same hinge Dow/AMD/SMC found. Built via `build_waves.py`.

## 📁 Analysis reports (CURRENT) — `analysis/`
- **`CYCLES_synthesis_continuous.md`** — ⭐ cross-framework cycles + the *reasoning behind* (macro)
- `dow_theory_continuous.md` — Dow Theory lens (6 tenets, phases, silver confirmation, volume, reversal verdict)
- `amd_continuous.md` — AMD / Power-of-3 (accumulation/manipulation/distribution, 32-row sweep log, premium/discount)
- `smc_continuous.md` — SMC (BOS/CHoCH, order blocks, FVGs, liquidity, SMT)

## 🔢 Data artifacts — `data/`
- `cont_xau_M15.parquet`, `cont_xag_M15.parquet` — continuous M15 bars pulled from DB (time_bucket)
- `cont_daily.csv`, `cont_h4.csv`, `cont_weekly.csv` — gold resampled OHLC
- `cont_zigzag_<primary|secondary|minor>.csv` — pivots (6/3/1.5% → Dow primary/secondary/minor)
- `cont_silver_daily.csv`, `cont_silver_zigzag_primary.csv` — confirming average / SMT
- `macro_daily.csv` — TNX, DXY, VIX, EURUSD (continuous)

## 🗄️ Superseded (old two-segment study, pre-backfill)
`FOUNDATION.md`, `analysis/{dow_theory,amd,smc,CYCLES_synthesis}.md`,
`charts/{master_*,FINAL_seg*}` — kept for reference; the gap they worked around no longer exists.

## 🔁 Reproduce
```
# 1. pull continuous bars from DB (needs TIGERDATA_URL env var; creds in database.md)
.venv/Scripts/python.exe MarketStructure/pull_continuous.py
# 2. build continuous foundation + zigzag + annotated chart
.venv/Scripts/python.exe MarketStructure/build_continuous.py
```

## The one-line answer
Gold ran a **falling-dollar / falling-real-yield bull** that compounded for 13 months and
went **parabolic into a 5602 blow-off top (2026-01-28)** — exactly as DXY bottomed at a
16-month low (96.4) and VIX hit complacency — then **distributed and marked down straight
to its range equilibrium (4099≈4108)** as yields turned up and a VIX fear-spike forced
de-leveraging. Silver topped alongside (bearish SMT on the 01-29 marginal high) and the
correction is, so far, balanced on the 200-day MA / equilibrium — bull not yet broken, not yet resumed.
