# ClaudeTradingRD

Trading strategy R&D scratchpad.

## FVG ICT strategy

Fair Value Gap detection (3-candle pattern, ported from
`KronosStrategies/strategies/strategy/ict_engine.py`) with a classic ICT
retest entry model on XAUUSD (GC=F proxy, 15m, last 60 days via yfinance):
structure-aligned FVGs only, entry on retrace into the gap, SL beyond the
zone, TP at 2R.

```bash
.venv/bin/python fvg_ict.py     # run backtest, writes chart_data.js
.venv/bin/python plot_fvg.py    # native lightweight-charts window (candles + FVG boxes + trades)
open chart.html                 # browser fallback (needs chart_data.js)
```

Setup: `python3 -m venv .venv && .venv/bin/pip install pandas yfinance lightweight-charts "pywebview<6"`
(pywebview must stay <6 — the 6.x JS bridge breaks lightweight-charts 2.1: black window.)

The original, fuller version of this strategy lives in
`C:\Projects\ClaudeProjects\ClaudeTradingBot` on the Windows PC (`ssh anilm`)
and is pending copy into this repo.
