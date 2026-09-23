# concept_lab — the shared harness for the 471-concept XAUUSD campaign

This harness is **read-only for campaign agents**. You write one script per concept that
builds events, calls one test and calls `write_result`. You never edit this package. If
it looks wrong, stop and report it. Do not work around it.

```python
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl          # python: /Users/anil/Projects/Kronos/ClaudeTradingRD/.venv/bin/python
```

## 1. Pick the test type

| the concept claims… | test | statistic (what the verdict reads) |
|---|---|---|
| "enter here, stop there, target that" | `trade_test(events, max_hold=…)` | mean net R − mean R of a **matched random-entry control** |
| "only take X when Y" / "avoid X at Z" | `gate_test(events, mask, mask_available_at=…)` | control-adjusted R, gated − complement |
| "this level gets swept", "the high forms in window W", "the FVG fills" | `rate_test(observed, times, available_at=…, null_fn=…)` | hit rate − **matched null** rate |
| paywalled, psychology, needs data we lack | `write_untestable(id, reason, script=…)` | UNTESTABLE(reason) |

Events are a DataFrame with **UTC** timestamps:

| column | meaning |
|---|---|
| `decision_time` | when the rule has decided. Must be ≥ the close of **every** bar it read. |
| `available_at` | the latest `close_time` / `available_at` of anything the rule read. **Asserted ≤ decision_time on every row.** NaT raises. |
| `direction` | +1 / −1 (or bullish/bearish/long/short). **0, NaN and booleans raise**: drop no-signal rows yourself. |
| `stop_px` or `stop_dist` | the stop level, or its distance from entry |
| `target_px` or `rr` or `target_dist` | a NaN row means no target (stop or time exit) |
| `max_hold` (column or param) | **no default**, so you must declare it. It is wall clock from the decision (`hold_basis="bars"` = trading time). A NaT row raises. |

Entry is the **open of the first M1 bar starting at or after `decision_time`**, never inside
the signal bar. Exits resolve on M1. When stop and target fall in the same M1 bar, the
**stop** wins. A gap through the stop fills at the bar's open. Because that convention can
decide a verdict on its own (see the tie rule in §3), every result reports `ties`.

**Your detector emits every column you score.** Write `detect(m1) -> events` so that the
frame you pass to the test is exactly `detect(cl.load_m1())`: all filtering, and any gate
column, happens inside `detect`. `probe_lookahead` compares its output on truncated data
with that frame, column by column, and `write_result` checks that the probed frame and the
tested frame are the same (fingerprint `events_fp`).

## 2. Worked examples (all three run in `python -m concept_lab.examples`)

**trade_test: bare 1h CISD** (`examples.example_trade`, ~2.5 s):
```python
from detectors.cisd import cisd_events
def detect(m1):                                   # pure: M1 in -> events out
    b = cl.build_bars(m1, "1h")                   # build FROM THE INPUT (probe needs it)
    ev = cisd_events(b[["open","high","low","close"]], max_wait=3)
    close = pd.DatetimeIndex(b.loc[ev.confirm_time, "close_time"])
    return pd.DataFrame({"decision_time": close, "available_at": close,
        "direction": np.where(ev.direction == "bullish", 1, -1),
        "stop_px": ev.protected_swing.to_numpy(), "rr": 2.0})
ev    = cl.cache_frame("cisd_1h_mw3", lambda: detect(cl.load_m1()))
probe = cl.probe_lookahead(detect, ev, lookback="20D")   # raises if it peeks (~5 s)
res   = cl.trade_test(ev, max_hold="10h")
cl.write_result("cisd", "rung0_1h", res, operationalization={"rules": [...], "params": {...}},
                params_source={...}, script=__file__, probe=probe)
# -> n=7,995  diff +0.011R [-0.015, +0.037] (day_block)  NULL (powered: MDE 0.037 <= 0.10)
```

**gate_test: does the forex NY-AM killzone (07:00–10:00 NY) improve 15m CISD?**
```python
def detect(m1):                                   # the gate is a COLUMN the detector emits
    ev = detect_cisd(m1, "15min")
    ev["in_kz"] = cl.in_window(ev["decision_time"], *cl.KILLZONES["fx_ny_am"])
    return ev
ev15  = cl.cache_frame("cisd_15m_kz", lambda: detect(cl.load_m1()))
probe = cl.probe_lookahead(detect, ev15, lookback="10D")          # checks in_kz too
res   = cl.gate_test(ev15, "in_kz", mask_available_at="decision_time", max_hold="150min")
# -> gated n=5,044, diff +0.000R [-0.038, +0.039]  NULL
```
`mask_available_at` is the time when the gate's verdict was knowable, **pass or fail**.
For a pure clock gate it is the decision time. For "PDH was swept before entry" it is
the sweep bar's close. That stamp is only a declaration. The behavioural check is the
probe, which only sees the mask if it is a column of the probed frame, so `write_result`
refuses a gate passed as a bare array (unless the whole rule is declared `no_detector`).

**rate_test: is the prior day's high taken during the next session?**
```python
d = cl.bars("1D"); t = pd.DatetimeIndex(d.close_time[:-1]); pdh = d.high[:-1].to_numpy()
nxt = d.n_m1[1:].to_numpy()                                  # horizon in TRADING minutes
obs = cl.touch(t, pdh, "above", horizon_bars=nxt)["hit"]
dist = pdh - first_open_after(t)                              # geometry to preserve
rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)            # matched random moments
def null_fn(rng, k):                                          # same distance, same bars
    ...touch(rt[:, k], px_k + dist, "above", horizon_bars=nxt)...
res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn)
# -> 51.0% vs null 52.9%, diff -0.019 [-0.039, +0.001]  NULL
cl.write_result(..., no_detector="pure level rule: prior day high from bars('1D') close_time")
```
When the predictor comes from a detector, pass its frame as `predictors=` (decision_time ==
`times`, row for row) and probe that frame. When many rows share one outcome (a per-day fact
asked at every bar), the day-block CI handles it. For outcomes spanning days pass
`outcome_horizon="5D"` or `cluster=<level id>`.
With `horizon="23h"` the same example returns **NEGATIVE, p=1e-16**. That result is false:
a wall-clock window from a Friday close holds zero tradable minutes. See trap 7.

## 3. The locked verdict (`rules.py`, pinned by `tests/test_rules_locked.py`)

`RULES_VERSION = "concept_lab-rules-2 (2026-09-23)"`. Version 1 was written before any
concept was tested. Version 2 (the same day, still before any result was written) adds the
review fixes marked **(r2)**. The rules apply in this order to the CI on `diff`, oriented by
`claim` (`"+"` means the concept says better/higher, `"-"` means worse/lower):

1. **UNTESTABLE(reason)**: the concept is declared untestable, or n < 30, or the harness
   **sanity floor** trips on a CI that excludes 0. The floor trips on win rate outside
   10–90%, |avg R| > 1, PF > 3 or a win-rate differential > 15pp. A suspected fault is not a finding.
2. **NEGATIVE**: the CI excludes 0 **against** the claim.
3. **EDGE**: the CI excludes 0 **in** the claimed direction, **and** H1 (2016–2020) and
   H2 (2021–end) both have the claimed sign, **and** the test is powered: MDE ≤ threshold,
   n ≥ 200 and **effective n ≥ 200 (r2)**. For gate tests, both arms count.
4. **NULL**: the CI contains 0 **and** the test is powered. An effect as big as the threshold
   would have been seen. **(r2)** If more than 20% of control draws *are* the concept's own
   trades (same entry bar, same direction: `ctrl_overlap`), the differential is attenuated
   toward 0 and a NULL becomes UNDERPOWERED. Attenuation can fake a NULL but not an EDGE.
5. **UNDERPOWERED**: everything else. `verdict_detail` says whether the halves disagreed or the power was short.
6. **Tie rule (r2)**: when the real and control arms differ in their share of ambiguous
   same-bar stop+target exits by more than 2pp (`ties`), the book is re-scored with every
   ambiguous bar as a 50/50 coin flip in both arms. If that changes the label, the verdict
   is UNTESTABLE ("M1 tie convention decides the verdict"). Concepts that enter into
   volatility (displacement, sweeps, news, killzone opens) hit this. Without the rule, a
   random-direction book entered after a 99th-percentile M1 bar came back NEGATIVE at
   −0.12 to −0.29R, and EDGE under `claim="-"`, purely from stop-first ties.

**CI (r2)** = the **widest** of: the phase-3 CI (the wider of an i.i.d. and a paired
stationary block bootstrap, mean block 20 *events*, `diff_with_ci`); a stationary
bootstrap over **trading-day buckets** whose mean block (in days) is the book's own
dependence length (max_hold plus the 90th percentile of the same-direction
overlapping-run length, at least 1); and, when you pass `cluster=`, a bootstrap over whole
clusters. 2,000 draws. `ci_components` lists every component and `ci_method` names the
winner. The 20-event block alone was far too narrow for setups that fire on many
consecutive bars in one direction ("long while in the zone", "trade with the daily bias")
and for rate tests whose rows share one outcome: noise books came back EDGE or NEGATIVE
2.5 to 5 times too often. **Effective n** is the number of trading days (or clusters, if
fewer) and is reported in `dependence`. MDE = 2.80 × SE. p is two-sided, from the CI.
The thresholds are 0.10 R for trade and gate tests, and min(5pp, 25% of the null rate)
for rate tests. You may **tighten** a threshold (`mde_threshold=`) but never loosen it.
Loosening raises an error.

**A per-concept EDGE is only a candidate.** The split-half requirement barely filters
noise: the halves are subsets of the same data, so nearly every noise book whose CI clears
0 also has same-sign halves. **Expect about 2.5–3% false EDGEs per reading** (the one-sided
2.5% tail), not the ~2% an earlier draft claimed. Measured on this harness (r2) over
530 pure-noise books on real gold in five shapes (unclustered, 120-minute setups,
daily bias, clustered gate, per-day rate outcomes): **11 EDGE, 2.1%**
(unclustered 5/200, 120-minute setups 3/90, daily bias 1/60, clustered gate 0/80, per-day rate 2/100; two-sided rejection 4.3%, z sd 0.97. Before r2 the clustered shapes ran 5–11% EDGE). Across 471 concepts, each with several readings, that is **dozens** of false
EDGEs. Every test call is appended to the **run ledger** (`concept_campaign/ledger.jsonl`,
`run_id`). `cl.adjust_campaign()` applies Holm and BH across every written result **and
every hypothesis that was run but never written** (distinct `hyp_key`: test, claim, frame
fingerprints, settings except seed and n_boot). A reading you tried and dropped therefore
still costs multiplicity. **Only a Holm/BH survivor is labelled EDGE by the coordinator.**
Calibration example: the phase-3 coordinator's zero-cost `max_wait=40` 1h CISD book has a
phase-3 CI low end of +0.0001. Under r2 its day-block CI is [−0.002, +0.048], so it is
NULL, not EDGE.

## 4. Traps (each one was hit in this project; see the vault's *Backtest Methodology Traps*)

1. **The in-progress HTF bar is the future.** Read a higher-timeframe bar only through
   `cl.asof(bars, t)`, `prior_hilo`, `open_at` or `running_hilo`, which return bars with
   `close_time ≤ t` (and NaN for a NaT time). A decision stamped at 14:30 with the 14:00
   1h bar as an input raises. Stamps are declarations, though: a detector can still read
   the in-progress bar and stamp only the lower-timeframe close. Used as a **filter**
   ("keep it if the 4h bar closes up"), that leak keeps every surviving event, so a
   survival-only probe cannot see it. `probe_lookahead` is therefore **symmetric** (r2):
   on data cut at T, the events in (T − 1D, T] must *equal* the scored ones, both ways and
   on every column. An extra event means a future filter. A missing or different one
   (a stop at the next bars' low) means a future input.
2. **`label="left"`.** A bar's index is its **start**. Decide at `close_time`, never at
   the index.
3. **Never read a raw win rate.** A selector that picks larger-R setups raises the win
   rate without predicting anything. The matched control shares direction, stop distance,
   target distance and ±30-day regime, so geometry cancels. Report `avg_R` because cost
   cancels in `diff`.
4. **Geometric confounds.** "Closed beyond its own open" measures candle shape. If your
   hit metric has a built-in cushion, the null must have the same cushion (same distance,
   same bars).
5. **"Never evaluated" must not look like "passed."** Masks with NaN raise. Joins by
   last-resolved timestamp inherit `True` forever (that bug once turned 2% into 99%), so
   report the gate's firing rate. `gate_test` does. A direction of 0 raises (it used to
   be traded as SHORT). So does a NaT `max_hold` (it used to hold to the end of the data).
6. **Pre-2016 data is disqualified.** `load_m1()` returns the certified span only. Use
   thresholds in ATR or % units, never raw dollars (the median daily range went from $15
   to $90). Data holes leave a few **stub sessions**: 2025-12-08 has 56 M1 bars. For
   PDH/PDL-type levels, `prior_hilo` reports `n_m1` and `coverage`, and
   `min_coverage=0.5` skips to the last real session. Record the choice in params.
7. **Wall-clock horizons across halts and weekends.** The venue halts 17:00–18:00 NY daily
   and all weekend. Compare `exposure_bars` (real vs control) in a trade result. If the two
   differ by more than about 10%, rerun with `hold_basis="bars"`. For `touch`, use
   `horizon_bars=`.
8. **The 4H grid is a knob.** The default is forex, 17/21/01/05/09/13 NY. Phase 3's outcome
   book flipped between grids, so record `grid4h` in `operationalization.params`. The time
   zone is New York with DST (settled). The day rolls at 18:00 NY. There is no 18:00 kill
   zone: the reopen hour is a gap artefact.
9. **Time-of-day buys opportunity, not accuracy, on gold.** If a concept is *not* about
   timing but its events cluster in hours, add `ctrl_tod_tol_min=30` so the control holds
   the NY clock fixed. If the concept *is* about timing, test it as a `gate_test`.
10. **Implausible = harness fault.** A 90% win rate or a +0.4R edge is debugged, not reported.
    The sanity floor enforces this.
11. **Many rows, few facts (r2).** A setup that fires on 60 consecutive minutes is one
    observation, not 60. The same goes for a daily bias traded at every 15m mark, or a
    per-day outcome asked at every bar. The day-block CI and the effective-n floor handle
    this. If your rows share something longer than a day, pass `cluster=` (setup id, level
    id) or `outcome_horizon=`.
12. **Shared frames (r2).** `bars()`, `build_bars()` and `window_hilo()` return copies, so
    editing yours never changes what the harness's own lookups read. `load_m1()` is still
    shared: never modify it.

## 5. Writing results

`write_result(concept_id, reading, result, operationalization={"rules": [...], "params":
{...}}, params_source={param: "corpus: <video_id> '<quote>'" | "threshold_fits: …" |
"session_window_fit: …" | "method_spec: …" | "phase3: …" | "declared-before-run: …"},
script=__file__, notes=…, probe=probe | no_detector="<why>")` writes
`research/concept_campaign/results/<concept_id>[__<reading>].json`. It refuses to write
when:

- a param has no source, the id is not in `batches.json`, the script does not exist, or a
  tested result has no p;
- **(r2)** there is no passing probe of the *same* frame the test used (`events_fp` must
  match), with at least 100 random cuts and 20 sampled decision times. The only
  alternative is `no_detector="…"`, a declaration that the rule is a pure clock or level
  rule with no detector. A probe that says `passed=False` is refused always;
- **(r2)** a gate's mask was passed as an array instead of a probed column, or a rate
  test's detector frame was not passed as `predictors=`;
- **(r2)** a locked knob was changed: `seed`, `n_boot`, `reps`, `window_days` or
  `entry_mode`. Re-rolling the control draw until a borderline book flips is a forking
  path. A **declarable** knob (`ctrl_grid`, `ctrl_tod_tol_min`, `hold_basis`, `cost`,
  `mde_threshold`) may differ from its default only with its own `params_source` entry,
  declared before the run. `cluster` and `outcome_horizon` need none: they only widen the CI;
- **(r2)** the run is not in the ledger (`run_id` missing), or the result was computed
  under an older `RULES_VERSION`.

The full schema is in `results.py`. For contested concepts, write one file per reading.
Every reading you *run* is counted anyway (§3).

## 6. API summary

- **Data:** `load_m1()`, `bars(tf, grid4h="forex", day_open_hour=18)` (1min…2h, 4h, 1D, 1W, 1M,
  each with `close_time`; a copy), `build_bars(m1, tf)` (pure, use it in detectors), `asof`,
  `cache_frame(key, fn)` (file name carries a fingerprint of `fn`'s code and the calling
  script; `build_fingerprint(fn)`), `close_time_of(starts, tf)`.
- **Time:** `to_ny`, `ny_minute_of_day`, `in_window`, `trading_day`, `session_date`,
  `KILLZONES`, `SESSION_WINDOWS`, `window_hilo`, `prior_hilo(times, "1D"|"1W"|"4h"|"ny_am"…,
  min_coverage=None)` (adds `n_m1`, `coverage`),
  `open_at(times, "00:00")`, `running_hilo(times, "1D")`.
- **Engine:** `touch(times, level, side, horizon=|horizon_bars=|until=)`,
  `sample_times(times, reps, window_days, seed, align="auto", tod_tol_min=None, grid_times=None)`,
  `get_market()`, `resolve_trades(...)`.
- **Tests:** `trade_test(events, max_hold=, cluster=None, …)`, `gate_test(events, mask_col_or_array,
  mask_available_at=, cluster=None, …)`, `rate_test(obs, times, available_at=, predictors=None,
  cluster=None, outcome_horizon=None, …)`. Each returns a dict with the result schema plus
  `ci_components`, `dependence`, `ties`, `ctrl_overlap`, `events_fp`, `run_id`.
  Pass `keep_trades=True` to get the per-trade frame in `_trades`, which is not written.
- **Lookahead:** `assert_no_lookahead(decision, available_at)`, `probe_lookahead(detect_fn, events,
  n_sample=20, n_cuts=200, lookback="45D", recent="1D", ignore_cols=())` (symmetric; compares
  every column; `lookback − recent` must exceed the detector's warm-up), `frame_fingerprint(df)`.
- **Results:** `write_result`, `write_untestable`, `load_results`, `load_ledger`,
  `adjust_campaign(ledger=True)`.

Controls: `ctrl_grid="auto"` (the default) draws M1 minutes on the events' minute-of-hour
grid. `"m1"` draws any minute. `"1h"` and similar draw that series' bar closes. `reps=5`
and `window_days=30` are the locked phase-3 values.

## 7. Runtime

A typical test takes seconds. On certified data, 8k trades take 0.6 s and 33k trades take
2 s, and M1 resolution is vectorised. Detectors are the slow part: `cisd_events` on 5-minute
bars is a Python loop. Wrap detector output in `cl.cache_frame(key, build)` and put every
parameter in `key`. The file name also carries a fingerprint of `build` (its code, the code
of the functions it calls, closure values and simple globals) and your script's path. Two
concepts that pick the same key therefore never share a frame, and fixing a detector
rebuilds it. Bar frames are cached on disk under `concept_campaign/.cache/`. Writes are
atomic, so parallel agents can share the cache safely. The probe re-runs your detector
about 220 times on short slices, which takes about 1 s for a bar-rule detector and about
5 s for 1h CISD. Pass `n_boot=500` while iterating, but only the default of 2,000 can be
written. Iteration runs are ledgered too.

## 8. Verification

- Tests: `cd research/python && ../../.venv/bin/python -m pytest concept_lab/tests -q`
- Calibration: `python -m concept_lab.calibrate`, which writes `concept_campaign/calibration.json`.
  The width and sign checks read the **phase-3 CI component**, because that is what the
  published figures measured. Rung-0 1h reproduces n=7,995 and diff +0.0093 with phase-3 CI
  [−0.0153, +0.0342], against the published +0.009 [−0.015, +0.034]; its r2 CI is
  [−0.0158, +0.0364] (day-block). All three faithful targets pass.
- False-EDGE rate: 530 noise books, 11 EDGE = 2.1% (§3), measured by `review_statistics/rules2_false_edge.py` (per-book CSV beside it). The 2026-09-23
  review scripts are in `concept_campaign/review_lookahead/` and `review_statistics/`.
