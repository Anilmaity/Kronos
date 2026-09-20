# XAUUSD M1 deep-history audit — `m3_scalper/xau_m1_full.parquet`

Built 2026-08-25 by `research/python/fetch_xau_history.py`.
Source: OANDA practice v3 `/instruments/XAU_USD/candles`, granularity M1, mid prices.

## What was built

`m3_scalper/xau_m1_full.parquet` — **5,772,702 M1 bars, 2010-01-03 22:55 UTC to
2026-07-23 04:07 UTC (16.55 years)**. That is 5.37x the 1,074,472 bars in
`xau_m1_3y.parquet`, which is left in place and untouched.

Schema is byte-identical in shape to the 3y file — a `RangeIndex`, a `time`
column of `datetime64[ns, UTC]`, and float64 `open/high/low/close` — so
`bars.load_m1(path)` reads it with no change. Verified: sorted, monotonic, zero
duplicate timestamps, and resampling to 5min/15min/1h/4h/1D all succeed.

4,704,939 bars were fetched in 941 paged requests (~10 minutes). The fetch
checkpoints into `m3_scalper/_xau_hist_cache/` and resumes from
`xau_hist_progress.json`, so it survives being killed. That cache directory is
retained; it also carries the per-bar tick `volume` that the final parquet
drops, which is what makes the liquidity analysis below possible.

### The seam is clean

The fetch deliberately ran five days *past* the start of the 3y file to make the
join checkable rather than assumed. It produced **6,709 overlapping timestamps,
and all four OHLC fields agree to exactly 0.0 on every one of them** — zero bars
differing by even 1e-9. The two halves are the same feed. Where they overlap the
existing 3y file is kept as authoritative, so any result already computed on the
3y file reproduces unchanged on the full file.

The apparent $-0.42 step at the join (2023-06-30 20:58 close 1919.525 -> 2023-07-02
22:03 open 1919.105) is an ordinary 49-hour weekend gap, not a splice
discontinuity. There is no price discontinuity at the seam.

## Coverage and quality by year

`day fill%` is the median share of a full Tue–Thu session that is actually
populated, measured against the calendar that applied in that year (1440 minutes
before Oct 2015, 1376 after). `h17` is bars in New York hour 17, which should be
zero. `zero-rng` is the share of bars with `high == low`. `tick med` is the
median OANDA tick count per minute — the direct measure of feed density, and
available only where the fetch cache covers the year (through 2023-06).

| year | bars | days | day fill% | h17 | sat | zero-rng | tick med | price range | return | ann vol | med daily range |
|------|------|------|-----------|-----|-----|----------|----------|-------------|--------|---------|-----------------|
| 2010 | 345,326 | 314 | 93.5% | 3,726 | 2 | 2.87% | 17 | 1044–1431 | +29.5% | 13.4% | 1.21% |
| 2011 | 353,312 | 352 | 95.5% | 3,228 | **434** | 2.02% | 29 | 1308–1921 | +10.1% | 16.8% | 1.18% |
| 2012 | 344,992 | 320 | 93.9% | 2,158 | 8 | 3.46% | 16 | 1527–1796 | +7.1% | 13.4% | 1.04% |
| 2013 | 354,950 | 313 | 96.5% | 2,759 | 1 | 0.61% | 83 | 1181–1697 | **−28.0%** | 18.8% | 1.36% |
| 2014 | 347,900 | 312 | 94.9% | 2,052 | 0 | 1.75% | 47 | 1131–1392 | −1.8% | 12.8% | 1.04% |
| 2015 | 339,013 | 311 | 93.9% | 1,813 | 0 | 2.43% | 27 | 1046–1308 | −10.5% | 12.1% | 1.12% |
| 2016 | 348,283 | 311 | 98.8% | 0 | 0 | 0.67% | 63 | 1061–1375 | +8.5% | 14.8% | 1.17% |
| 2017 | 345,097 | 309 | 98.5% | 2 | 0 | 0.41% | 117 | 1146–1358 | +13.3% | 9.2% | 0.87% |
| 2018 | 349,978 | 312 | 99.3% | 1 | 0 | 0.13% | 172 | 1160–1366 | −1.6% | **8.4%** | 0.80% |
| 2019 | 337,111 | 312 | 96.7% | 17 | 0 | **4.33%** | **11** | 1266–1557 | +18.3% | 10.8% | 0.80% |
| 2020 | 352,841 | 312 | 99.9% | 2 | 0 | 1.05% | 29 | 1451–2075 | +24.9% | 17.6% | 1.25% |
| 2021 | 351,435 | 310 | 99.6% | 0 | 0 | 1.03% | 24 | 1677–1959 | −4.2% | 11.8% | 1.07% |
| 2022 | 352,677 | 310 | 99.9% | 0 | 0 | 0.32% | 62 | 1615–2071 | −0.4% | 13.6% | 1.16% |
| 2023 | 351,962 | 309 | 99.9% | 0 | 0 | 0.21% | 33 | 1805–2149 | +12.9% | 12.1% | 0.98% |
| 2024 | 354,689 | 313 | 100.0% | 0 | 0 | 0.06% | — | 1984–2790 | +27.1% | 13.2% | 1.09% |
| 2025 | 348,603 | 309 | 100.0% | 0 | 0 | 0.01% | — | 2615–4550 | **+64.7%** | 16.9% | 1.29% |
| 2026 | 194,533 | 174 | 100.0% | 0 | 0 | 0.00% | — | 3942–5602 | −4.8% | **28.5%** | 1.94% |

2026 is a partial year (to 23 July). Annualised vol is from New-York-day closes
scaled by sqrt(252); it is deliberately not computed from 1-minute returns,
because at M1 that statistic is dominated by microstructure noise whose level
itself changes across the span, which would confound volatility with feed
granularity.

## Gap profile — the trading calendar changed in October 2015

The stated convention is Sunday 18:00 to Friday 17:00 New York with a daily
break 17:00–18:04, hence no bars in NY hour 17 and none on Saturday. **That
convention does not hold for the first six years of the span.**

From 2010-01 through **2015-09** the instrument traded a genuine 24-hour day:
NY hour 17 carries 1,800–3,700 bars a year and all 24 hours are present. Hour-17
activity stops abruptly in **October 2015** — 142 bars in September 2015, zero in
October 2015 and every month after. From 2016 onward hour 17 is empty apart from
22 stray bars across eleven years, and Saturday is empty everywhere except 2011.

This is a structural change in the instrument's schedule, not noise, and it is
the single most consequential finding for a session-based method. Before Oct 2015
there is no daily break, so "the daily candle", the 17:00 daily boundary, and any
kill-zone or session-open logic mean something different. A detector written
against the modern calendar will silently produce different objects on
pre-Oct-2015 data rather than failing loudly.

2011 has a second calendar defect: **434 Saturday bars across 40 distinct
Saturdays** (~11 each, January to October), spread thinly over all 24 New York
hours rather than clustered at either end of the weekend. It is only 0.12% of
that year's bars, but any weekly-boundary logic that assumes Saturday is empty
will see spurious data in 2011. Across the whole fetched history there are 445
Saturday bars on 50 Saturdays, so 2011 accounts for 98% of the problem.

### Long gaps are almost entirely legitimate

Every one of the 22 New York weekdays with zero bars across the whole 16.55 years
is a real market holiday — Good Friday each year, Christmas Day, New Year's Day,
4 July 2025, Thanksgiving Friday 2025. Nothing unexplained.

Weekday gaps longer than six hours that a known holiday does not explain number
**17 in 16.55 years**, and they are concentrated:

- **15 fall in 2010–2013**, mostly the weekend-boundary artifact described above
  (a stray Saturday or Sunday bar makes an ordinary weekend look like a mid-week
  hole). Sizes 7.0h to 37.1h.
- **Zero fall between 2014 and 2025.** Eleven consecutive years with no
  unexplained multi-hour weekday hole at all.
- **2 fall in the existing 3y file** and are discussed next.

### Two whole days are missing from the existing 3y file

`xau_m1_3y.parquet` is missing **2025-12-09 (24.0h gap)** and **2026-01-21
(29.5h gap, 2026-01-20 18:29 to 2026-01-22 00:00)**. Neither is a holiday. I
re-probed both against OANDA and **each is served in full, 1,376 M1 bars** — so
these are defects of the existing 3y file, inherited by the splice, not market
closures.

They are **not repaired** in `xau_m1_full.parquet`, on purpose: keeping the
splice faithful to the 3y file is what guarantees that prior results reproduce.
`python/fetch_xau_history.py patch-holes` fetches both days and writes a
*separate* `m3_scalper/xau_m1_full_patched.parquet`, leaving the primary file
alone. Whether to adopt the patched file is the next stage's call. At 2,752 bars
out of 5.77M the statistical effect is negligible; the reason to care is that a
daily or weekly candle spanning those dates is wrong, not merely absent.

## Structural integrity — clean everywhere

Across all 5,772,702 bars, in every year without exception:

- duplicate timestamps: **0**
- `high < low`: **0**
- open outside `[low, high]`: **0**
- close outside `[low, high]`: **0**
- zero or negative prices: **0**

There is no year in which any of these is non-zero. Whatever else is true of the
early data, it is not internally malformed.

The price levels also survive an external check against gold's well-known
landmarks, which is worth doing because a mis-scaled or wrong-instrument feed
would pass every internal test above. The 2011 high in this data is **1921.07**
against the widely reported September 2011 record of ~1920.9; the 2015 low is
**1046.43** against the December 2015 bottom of ~1046. The series is real
XAUUSD at the right scale, not a proxy or a rebased index.

Implausible jumps are also absent. Minute-to-minute moves above 1% on
*consecutive* minutes number 0–6 per year through 2025 and 10 in 2026; moves
above 2% occur three times in 16.55 years (2013, 2015, 2026). These are
consistent with real news spikes, not with corrupt prints, and none were altered.

## The real quality axis is tick density, not structure

The defect that actually varies across the span is how many ticks the feed saw
per minute. Where the minute contains one tick, the bar has `high == low` and
carries no intrabar information at all — the `zero-rng` and `tick med` columns
are two views of the same thing: **98.5% of the 73,295 zero-range bars in the
fetched history are single-tick minutes**, so a flat bar is almost always a
minute the feed only saw once, not a minute in which gold genuinely did not move.

Two periods stand out:

**2010–2012** runs at 16–29 ticks per minute with 2.0–3.5% of bars flat —
between one bar in thirty and one in fifty carrying no range — on top of
93.5–95.5% minute completeness.

**2019-02 through 2020-02** is a sharp, isolated regression in otherwise modern
data, and it is worth stating explicitly because the year-level table understates
how concentrated it is:

| month | bars | zero-range | tick median |
|-------|------|-----------|-------------|
| 2018-12 | 26,787 | 0.3% | 108 |
| 2019-01 | 29,515 | 0.7% | 83 |
| 2019-02 | 25,075 | **7.6%** | **6** |
| 2019-03 | 26,529 | 6.6% | 7 |
| 2019-04 | 25,975 | 8.8% | 6 |
| 2019-05 | 27,980 | **9.0%** | 6 |
| 2019-06 | 26,991 | 3.3% | 13 |
| 2019-12 | 27,206 | 6.2% | 8 |
| 2020-02 | 27,068 | 1.5% | 20 |
| 2020-03 | 30,514 | 0.4% | 67 |

Median tick count falls from 83–186 to 6, and up to 9% of minutes are flat. This
is a feed regression, not a market event — 2019 was not a quiet year, and its
daily-range and volatility figures are unremarkable. It sits inside what is
otherwise the trustworthy span, so it needs handling by exclusion or by
sensitivity check rather than by moving the span boundary.

By contrast **2022 onward is essentially perfect**: 99.9–100% minute
completeness, zero-range bars falling from 0.32% (2022) to 0.06% (2024), 0.01%
(2025) and 0.00% (2026).

## Regimes — what the extra history actually buys

The 3y file is one regime. Gold ran 1919 -> 5602 across it with volatility rising
monotonically, and every full year in it is a strong up year (+12.9%, +27.1%,
+64.7%). Nothing in it tests a bear market, a flat market, or a low-volatility
market. The deep history supplies all three:

- **2010–2012, bull into the top.** 1044 -> 1921 peak (Sept 2011), then a
  two-year distribution. Vol 13–17%.
- **2013–2015, the bear market.** 1921 -> 1046. 2013 alone is **−28.0%**, the
  single largest annual move in the span and the only severe down year anywhere
  in 16.55 years. This regime exists nowhere else in the data.
- **2016–2018, low-volatility range.** 1061–1375, then 1146–1366, then a
  1160–1366 grind. **2018 is the calmest year in the entire span**: 8.4%
  annualised vol, 0.80% median daily range, less than half the 2026 figure.
- **2019–2020, breakout and COVID.** Range expansion, vol to 17.6%.
- **2021–2022, chop.** −4.2% then −0.4%, two flat years back to back.
- **2023–2026, the current bull.** Vol climbing 12.1% -> 28.5%, median daily range
  0.98% -> 1.94%.

One caution for anything that fits a threshold. Gold went from ~$1,100 to ~$5,600
across this span, and the median daily range from **$15.3 (2010) to $90.3
(2026)** — a 5.9x change in dollars but only 1.21% -> 1.94%, a 1.6x change in
percentage terms. **Any threshold expressed in absolute points or dollars is not
comparable across the span**, and fitting one on the pooled history will be
dominated by the recent high-price years. Thresholds must be expressed in ATR or
percentage units before this data is used to fit them.

## Verdict — what to backtest on

**Trust 2016-01-01 onward without reservation.** That is 3,687,209 bars over
10.56 years, 3.43x the existing 3y file. Across it the modern trading calendar
holds (hour 17 empty, Saturday empty), minute completeness runs 96.7–100%, there
is not one unexplained multi-hour weekday hole, and structural integrity is
perfect. The single caveat inside it is the 2019-02 to 2020-02 tick-density
collapse; the honest handling is to run the primary test on the full span and
re-run excluding that thirteen-month window as a sensitivity check. Dropping it
still leaves 9.4 years.

**Treat 2010-01-03 to 2015-09-30 as higher-timeframe and regime evidence only,
not as primary M1 backtest data.** The reason is not that it is dirty in the
ordinary sense — it has no malformed bars, and 2013–2014 are respectably dense at
47–83 ticks per minute. The reason is that **the instrument traded a different
session schedule**, with no 17:00 daily break. A method built on session timing
will not fail on this data; it will quietly compute different objects, which is
worse. If this span is used, the session logic must be explicitly re-specified
for the 24-hour calendar and the result reported separately, never pooled with
post-2015 results as though it were the same experiment. 2010–2012 carries the
additional load of 2–3.5% flat bars, the 2011 Saturday leakage, and 15 of the 17
unexplained gaps in the whole dataset; 2013–2015 is materially cleaner than
2010–2012 and is the better half if only part is used.

**October 2015 to December 2015 is a transition quarter** and should be excluded
from either side rather than assigned to one.

This creates a genuine tension worth naming rather than burying: **the regime you
most need is in the data you least trust.** The only real bear market in the
entire 16.5 years is 2013–2015, which sits on the wrong side of the calendar
change. Within the trustworthy span the best available non-bull regimes are
2016–2018 (low-volatility range, and the cleanest data in the pre-2022 era) and
2021–2022 (two flat years). Those are adequate for a robustness check but they
are not a bear market, and no honest reading of this dataset can claim the method
has been tested against a sustained gold downtrend on trustworthy data.

### Effect on the conjunction test

The power problem is substantially but not completely solved. Scaling the
observed event rate — 454 events in 3.06 years — by span length, and noting that
minimum detectable effect scales as 1/sqrt(n):

| span | years | est. events | est. MDE |
|------|-------|-------------|----------|
| existing 3y | 3.06 | 454 | 7.2pp |
| 2016+ ex 2019-02..2020-02 | 9.42 | ~1,400 | ~4.1pp |
| **2016-01-01 onward** | **10.56** | **~1,570** | **~3.9pp** |
| full 2010+ (calendar caveat) | 16.55 | ~2,460 | ~3.1pp |

**The trustworthy span resolves a 5pp effect comfortably and leaves a 3pp effect
out of reach.** Reaching 3pp requires the pre-2015 data, and that data cannot be
pooled with the modern span without first re-specifying the session logic — so
3pp should be treated as currently unreachable rather than as one more fetch away.

These event counts are **extrapolated from the observed rate, not measured** — I
did not run the detector over the new history. The extrapolation assumes the
event rate per unit time is roughly stable, which the volatility spread across
the span (8.4% to 28.5% annualised) gives real reason to doubt in both
directions. Recount before relying on the MDE column.

## Reproducing

```bash
# from research/
python python/fetch_xau_history.py fetch        # resume-safe, ~10 min
python python/fetch_xau_history.py splice       # -> m3_scalper/xau_m1_full.parquet
python python/fetch_xau_history.py audit        # JSON behind the tables above
python python/fetch_xau_history.py status       # checkpoint state
python python/fetch_xau_history.py patch-holes  # opt-in, separate output file
```

The practice credential is imported from the repo-root `fetch_oanda_m1.py`
default (overridable with `OANDA_API_KEY`) rather than duplicated, and is never
printed or written to disk.
