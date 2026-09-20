# Primitive base rates — XAUUSD

Source: `m3_scalper/xau_m1_3y.parquet` — 1,074,472 M1 bars, 2023-07-02 to 2026-07-23.

Percentages are of bars on that timeframe. `sweep_*` requires the bar to close back inside the prior bar's range; a close beyond it is counted as `expansion` instead. That split is the single most important distinction in candle-range reasoning, so it is measured separately.

| TF | bars | sweep any | high | low | both | expansion | inside | FVG | swings | displacement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15min | 71,873 |  44.1% |  24.4% |  24.2% |   4.5% |  47.0% |  14.6% |  20.7% |  26.8% |  14.2% |
| 1h | 17,981 |  43.5% |  24.2% |  24.3% |   5.0% |  47.2% |  15.7% |  20.1% |  26.7% |  13.8% |
| 4h | 4,863 |  42.4% |  24.5% |  23.0% |   5.1% |  47.5% |  19.7% |  22.7% |  28.6% |  13.8% |
| 1D | 949 |  40.0% |  22.7% |  22.9% |   5.5% |  50.1% |  22.2% |  26.9% |  26.7% |  16.0% |

## Reading this

A daily candle sweeping the prior day's high or low is *ordinary*, not rare. Any concept built on 'price swept liquidity' therefore carries almost no information on its own — the edge, if there is one, has to come from the conditions attached to it (which level, at what time, in what HTF context). Treat these numbers as the null hypothesis every concept must beat.
