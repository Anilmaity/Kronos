# Bias and POI — the missing detector layer

**Phase 3, workstream A.** Built 2026-08-25 against
`m3_scalper/xau_m1_3y.parquet` (1,074,472 XAUUSD M1 bars, 2023-07-02 → 2026-07-23)
and a newly fetched correlated asset.

Phase 2 ended with one instruction: *test the model, not the primitive.* Every
primitive measured in isolation sits near its base rate — sweeps at 40-44%, FVGs in
61-77% of break windows, the C2 wick effect at ~0 where the data has power — and the
corpus's own claim is that the edge lives in the **conjunction**: higher-timeframe
bias, then a point of interest, then a CISD, then timing. Two of those four layers
did not exist as code. They do now.

| file | what it is |
|---|---|
| `python/fetch_correlated.py` | pulls the correlated asset the SMT layer needs |
| `python/detectors/bias.py` | §2.1 / §2.2 / §2.3 / §2.4 / §2.5 / §2.6 — the bias layer |
| `python/detectors/poi.py` | §4.1 — the point-of-interest gate, as a **switch** |
| `python/detectors/test_bias.py` | 49 tests |
| `python/detectors/test_poi.py` | 32 tests |

Suite: **175 passing** (94 before, 81 added).

---

## The headline: what the conjunction costs in sample size

**This is the most important number in the document.** Over **788 trading days**
(18:00-NY anchored, 2023-07-02 → 2026-07-22):

### Standalone

| gate | days | rate | what it tests |
|---|--:|--:|---|
| `gate_bias` | 212 | **26.9%** | daily C2/C3 closure **and** an aligned hourly CISD (§2.4) |
| `gate_profile` | 94 | **11.9%** | the day's profile *supports* the bias (§2.1 step 2, §2.5) |
| `gate_alignment` | 86 | **10.9%** | daily / 4H / hourly at the same objective, ≥2 layers (§3.5) |
| `gate_no_fade` | 788 | **100%** | the daily candle is not being faded (§2.1) |
| `gate_poi` | 202 | **25.6%** | a POI at the day's bias-side hourly extreme (§4.1) |
| `gate_smt` | 56 | **7.1%** | model-gated SMT against silver agreeing with the bias (§2.6) |

### Stacked, in the spec's own order

| stack | days | rate | **marginal keep** |
|---|--:|--:|--:|
| bias | 212 | 26.9% | 26.9% |
| + profile | 94 | 11.9% | **44.3%** |
| + alignment | 31 | 3.9% | **33.0%** |
| + no-fade | 31 | 3.9% | 100% |
| + POI | 31 | 3.9% | 100% |
| + SMT | **9** | **1.1%** | **29.0%** |

**Read that bottom row before designing anything downstream.** The full conjunction
as the spec states it fires on **9 days in three years**. That is ~3 trades a year.
No outcome measured on it is decidable — phase 2's own minimum-detectable-effect
work needed thousands of events to resolve a 4pp win-rate difference, and this is
nine. The four-layer conjunction without SMT gives 31 days, ~10 a year, which is
still far below anything testable.

**The practical conclusion: the conjunction must be tested one timeframe down.** The
daily bias layer is a *per-day* filter and there are only 788 days in the sample; the
same ladder evaluated on 4H or hourly candidate events has 1,046 and 3,679 CISD
events respectively to work with. The daily gates here should be used as **context
columns on those events**, not as the event generator. `bias_report` is built to be
joined that way — every row carries `gates_available_at`.

### Where the cost actually comes from

Three of the six gates do essentially nothing, and two do almost all the work.

- **`gate_no_fade` is free — it never fires against anything (100%).** That is not a
  bug: as constructed, a confirmed bias requires a daily closure in that direction,
  and a daily candle that closes in a direction cannot simultaneously oppose it. The
  gate is real in the spec and inert in this implementation. **Do not count it as
  independent confirmation.**
- **`gate_poi` is free *at the daily layer*** — 202 of the 212 biased days pass it
  (95.3%), and it removes exactly 0 days from the stack. A whole trading day's worth
  of hourly bars almost always contains an FVG or a sweepable swing near its extreme.
  The POI gate is a frequency lever **at the event layer, not the day layer** (see
  the table below).
- **`gate_profile` and `gate_alignment` are where the sample goes.** Profile keeps
  44%, alignment then keeps 33% of what is left. Both are dominated by a single
  design choice each, documented under "parameters that move the answer".

---

## The POI gate on CISD events — where it does bite

Run against `cisd.cisd_events` on each timeframe, gate on and off:

| tf | bars | CISD events | POI *required*? | pass **strict** | pass **loose** | pass **off** | continuation |
|---|--:|--:|---|--:|--:|--:|--:|
| 1D | 949 | 185 | no (density) | 100% *(would find one 82.2%)* | — | 100% | 100% |
| 4h | 4,863 | 1,046 | no (density) | 100% *(would find one 79.7%)* | — | 100% | 100% |
| 1h | 17,981 | 3,679 | **yes** | **80.3%** | 92.2% | 100% | 100% |
| 15m | 71,873 | 15,255 | **yes** | **82.8%** | 92.9% | 100% | 100% |

"strict" = §4.1 as written (both an FVG and a swing must be tagged when both exist);
"loose" = `require_both_when_both_exist=False`; "off" = `enabled=False`; the
continuation column is §4.1's own waiver.

**So the POI switch costs ~17-20pp of CISD events on the timeframes where it is
required — 3,679 → 2,953 on hourly, 15,255 → 12,635 on 15m — and the
both-must-be-tagged clause is roughly half of that** (strict 80.3% vs loose 92.2% on
hourly; 82.8% vs 92.9% on 15m). The cost is notably **stable across timeframes**,
which is itself a finding: the gate is not more selective on faster charts.
That is the honest size of the "single biggest frequency lever" — material, but an
order of magnitude smaller than the phrase suggests, because the corpus's own
enumeration (an FVG **or** a swept high **or** a swept low) is satisfied by most bars
on a liquid instrument.

Which branch supplies the POI, on hourly CISD events:

| branch | share |
|---|--:|
| FVG alone | 40.5% |
| CISD level (the last-resort branch, + the 50%-body test) | 23.0% |
| nothing found | 19.7% |
| FVG **and** swing (both required) | 13.3% |
| swing alone | 3.4% |

The density rule behaves exactly as §4.1 says: on 1D and 4H a POI is *not required*,
so those rows pass unconditionally — but the parenthetical is the informative number,
because it says the search would have succeeded ~80% of the time anyway.

---

## Task 1 — the correlated asset

`python/fetch_correlated.py` fetched from OANDA practice, reusing the key already
carried by the repo's own `fetch_oanda_m1.py` default. H1 and D only: SMT is a bias-layer
tool, and M1 silver would have been ~215 paginated requests for data no rule reads.
Written to `m3_scalper/` (untracked — large data must not enter git).

| file | instrument | bars | coverage | shared bars with gold | **return correlation** |
|---|---|--:|---|--:|--:|
| `xag_h1.parquet` | XAG_USD H1 | 18,107 | 2023-07-02 22:00 → 2026-07-23 23:00 | 17,979 (99.99% of gold H1) | **0.766** |
| `xag_d1.parquet` | XAG_USD D | 953 | 2023-07-02 → 2026-07-23 | 948 (99.89% of gold D) | **0.796** |
| `eur_h1.parquet` | EUR_USD H1 | 19,035 | 2023-07-02 21:00 → 2026-07-23 23:00 | 17,981 (100% of gold H1) | 0.347 |
| `eur_d1.parquet` | EUR_USD D | 957 | 2023-07-02 → 2026-07-23 | 949 (100% of gold D) | 0.397 |

Gap profile is clean and entirely weekend-shaped: silver H1 has 791 gaps > 1.5 bars,
max 3d02h, only 5 over three days; silver D has 159 gaps, max 3d, none over three
days. Daily candles were requested with `alignmentTimezone=UTC, dailyAlignment=0` so
they share bar edges with the gold series rather than OANDA's default 17:00-NY.

### SMT is testable. Silver is a real correlate.

**Verdict: not blocked.** 0.766 on hourly returns and 0.796 on daily is comfortably
strong enough for a divergence test, and the two feeds share 99.99% of gold's hourly
bars. `smt_events(h1, xag)` produces **2,112 raw divergences on 17,981 hourly bars
(117.5 per 1,000)**, of which **209 (9.9%)** survive §2.6's ordering doctrine —
"you find the model and *then* check for SMT". On daily bars: 101 divergences over
949. PSP (opposite closes on the same candle) runs at **22.9%** of hourly bars.

### DXY is NOT available, and what was fetched instead is a proxy

The OANDA practice account exposes **123 instruments and none of them is a dollar
index** — checked directly against `/v3/accounts/{id}/instruments`, zero matches for
DX / IDX / INDEX / TWI. `USB10Y_USD` is a ten-year bond yield, not the dollar. What
`fetch_correlated.py` pulls instead is **EUR_USD, to be used inverted as a dollar
proxy** (EURUSD is ~57% of the DXY basket by weight). **Say "EURUSD-inverted proxy",
never "DXY"** — it carries euro-specific risk the index averages away, and its
correlation with gold (0.35 hourly / 0.40 daily) is less than half silver's.

Worth recording: §2.6 says outright that TTrades does **not** use cross-asset-class
correlation — no DXY-vs-gold — on the claim that it broke down
(`intermarket-correlation-not-used`). Silver is the correlate his own method
sanctions for gold. The dollar proxy is here so the claim can be checked, not because
any rule depends on it.

---

## Look-ahead and availability — the discipline this layer needs

**Every OHLC frame in this project is left-labelled**, so a bar's index timestamp is
its **start** and its information does not exist until `index + freq`. The off-by-one
is silent in both directions: replaying a signal candle drives a book to a ~3% win
rate, and letting a gate peek at the bar it fires on manufactures a fake edge that
looks like success.

So every gate reports an `*_available_at` timestamp, and `bias_report` reduces them
to a single `gates_available_at`:

| gate | information used | available from |
|---|---|---|
| `previous_candle_state` | candle i and i-1; `implied_bias` is for candle **i+1** | close of candle i |
| `draw_on_liquidity` | 3-day extremes shifted back one, plus today's **open** | the day's open |
| `daily_closures` | the candle's own close vs the previous candle | close of that candle |
| `hourly_cisd_in_candle` | LTF bars inside the HTF candle | close of the confirming LTF bar |
| `daily_bias` | both of the above | max(day's last bar close, CISD bar close) |
| `daily_profile` | Asia/London/NY-am ranges; `outside_day` needs the daily close | day's close (NY-am end if `require_outside_day=False`) |
| `alignment_frame` | the last **closed** 4H and hourly candle of the day | that candle's close |
| `poi_gate` | bars to the extreme, **plus** `body_hold_bars` forward on the CISD branch | `detail["last_bar_used"] + freq` |
| `smt_events` | both series at the **same left label** = the same close window | `time + freq` |

Two consequences that downstream code must respect:

1. **A daily bias is not tradeable inside its own day.** `daily_bias` answers *"is
   today's daily candle confirmed"*, which by construction resolves at the day's
   close (~17:00 NY). `next_day_view()` shifts the frame forward one session, which
   is what §2.3 means by *"anticipate the same direction on the next candle"*.
2. **The POI gate's CISD branch waits by design.** §4.1's "50% of the bodies of that
   opposing series must hold" is a forward test; `last_bar_used` records exactly how
   far forward it looked. The FVG and swing branches never look past the extreme,
   and there is a test asserting it.

The enforcement is mechanical, not by inspection:
`test_bias.py::test_no_gate_reads_past_its_availability` perturbs **every bar after a
day's claimed availability by 50%** and asserts that day's `bias`, `branch`,
`profile`, `profile_direction` and all five gate booleans are unchanged.
`test_poi.py::test_bars_after_the_extreme_cannot_change_an_fvg_or_swing_verdict` does
the same for the POI branches that must not wait. `smt_events` additionally **raises**
rather than silently misaligning if the two series' bar widths differ, and a real-data
test confirms silver and gold share hourly labels on >95% of bars, all on the hour.

---

## Parameters — every [GAP] and [P], with its default

### `bias.py`

**Settled in phase 2 — constants, not knobs.** `TZ = "America/New_York"` (DST-aware)
and `DEFAULT_GRID = "forex"` (17/21/01/09 NY). Both are overridable only so a test can
pin the alternative. Do not sweep them; `meta/session_window_fit.md` closed both.

| parameter | default | source | note |
|---|---|---|---|
| `DAILY_OPEN_HOUR` | `18` | §1.4 **[P]** | 18:00 NY is canon; `0` (midnight open) is the earlier reading, preserved |
| `draw_rule` | `"proximity"` | §2.2 **[GAP]** | no ranking among draw candidates is ever given. `"proximity"` is the only fully mechanical reading (`proximity-bias-nearest-extreme`); `"bias"` and `"displacement"` are the other two the corpus states |
| `draw_lookback` | `3` | §2.2 | attested: `previous-day-lookback-three-days` |
| `c3_reference` | `"c2_open"` | §3.3 **[P]** | Reading A (body/opening price of C2). `"c2_extreme"` is Reading B, strictly stronger |
| `cisd_scope` | `"range"` | §2.4 **[P]** | whether the hourly CISD must sit inside the *wick* or anywhere in the daily range is stated **both ways**. `"wick"` is the strict reading |
| `cisd_level_rule` | `"series_open"` | §4.2 **[P]** | first-candle-open, the spec's "sensible default"; `"series_extreme"` and `"series_close"` are the alternates |
| `cisd_max_bars_waited` | `None` (off) | §4.2 | *"I prefer 1, 2, maybe three"* — a stated **preference**, not a rule, so off by default |
| `require_closure` / `require_hourly_cisd` | `True` / `True` | §2.4 | *"either alone → no bias"*. Exposed so their cost is measurable |
| `wick_measure` / `wick_cut` | `"body"` / `1.0` | `threshold_fits.md` grade **A** | the one cut three independent videos state. `"range"` / `0.30` is the grade-C parameterisation |
| `eq_respect` | `True` | §2.4 | the continuation branch's negative test: no LTF closures beyond the previous day's EQ |
| `direction_ref` | `"bias"` | — | measuring "counter to the daily direction" against the realised close is look-ahead; `"realized"` exists for post-hoc classification only |
| `london_counter_ref` | `"asia"` | §2.5 **[GAP]** | the spec never says what London "runs counter" *to*. Asia's range is the local reading; `"day_open"` is the alternative |
| `relevant_levels` | previous day + previous 5-session extremes | §4.1/§2.7 **[GAP]** | *"relevant" / "key level" is never defined.* The one attested default is *"previous day and previous week extremes always qualify"* (`relevant-level`) |
| `require_outside_day` | `True` | §2.5 | faithful to Seek & Destroy's second clause, but only checkable at the daily close. `seek_destroy_asia_both` is returned separately as the intraday-safe form |
| `require_cisd_for_london_reversal` | `True` | §2.5 | *"changes the state of delivery there"* |
| `ny_manip_requires_london_quiet` | `True` | §2.5 | *"London consolidated or produced nothing usable"*, read with the corpus's own consolidation test (London inside Asia's range) |
| `unclassified_supports` | `False` | §2.5 **[GAP]** | what would invalidate a profile is never given, so an unnamed day is treated as unconfirmed, not as permission |
| `min_aligned` | `2` | §3.5 | *"minimum two aligned expansion candles; three preferred"* |
| `no_fade_daily` | `True` | §2.1 | `no-fading-the-daily-candle` |
| `smt` `lookback` / `window` | `20` / `3` bars | **[GAP]** | no horizon is stated for either the shared level or the model-to-SMT gap |
| `standalone_allowed` | `False` | §2.6 **[P]** | two videos disagree on whether SMT can trigger alone; the later canon says no |

### `poi.py`

| parameter | default | source | note |
|---|---|---|---|
| `enabled` | `True` | §4.2 / `external_crossref.md` §1c | **the master switch.** The POI requirement is *this channel's* tightening, not the general CISD definition — outside opinion is genuinely split. Report every statistic both ways |
| `setup_type` / `waive_for_continuation` | `"reversal"` / `True` | §4.1 | mandatory for a reversal, **waived for a continuation** |
| `density_cut` | `12.0` candles/day | §4.1 **[GAP]-derived** | the spec names exactly two points — 4H (6/day, optional) and hourly (24/day, required) — so any cut must sit between them; 12 is the midpoint |
| `require_both_when_both_exist` | `True` | §4.1 | *"If both an FVG and a swing exist, require both to be tagged."* `False` is the looser either-one reading |
| `polarity` | `"any"` | §4.1 **[GAP]** | the corpus says "a fair value gap", full stop. `"aligned"` / `"opposing"` exist for a caller who wants to commit |
| `level_rule` | `"series_open"` | §4.2 **[P]** | mirrors `cisd.LEVEL_RULES` |
| `require_body_half_hold` / `body_hold_bars` | `True` / `5` | §4.1 / **[GAP]** | the 50%-body test is stated; the *window* over which it must hold is not |
| `lookback` (search range) | `40` bars | §4.1 **[GAP]** | the "reversal point" that opens the range is never defined. Implemented as the most recent **opposing** swing before the extreme, with this as the fallback |
| `left` / `right` | `2` / `2` | — | matches `primitives.swing_points` throughout the project |

### Parameters that move the answer — measured, not asserted

Days with a confirmed bias, out of 788, varying one parameter at a time:

| variant | days | vs default (212) |
|---|--:|---|
| **default** | **212** | — |
| `cisd_scope="wick"` | **66** | **−69%** — the single biggest lever in the bias layer, and it is a **[P]** the corpus states both ways |
| `cisd_max_bars_waited=3` | 147 | −31% |
| `c3_reference="c2_extreme"` | 195 | −8% |
| `cisd_level_rule="series_extreme"` | 207 | −2% |
| `cisd_level_rule="series_close"` | 226 | +7% |
| `require_hourly_cisd=False` | 265 | +25% (the closure alone) |
| `require_closure=False` | 573 | **+170%** (the hourly CISD alone) |
| both requirements off | 626 | +195% |

That last block is the quantitative form of §2.4's *"either alone → no bias"*: the
**closure is the expensive leg** (33.6% of days) and the hourly CISD is nearly
permissive on its own (72.7%). Conditional on a closure existing, the hourly CISD
confirms it **80.0%** of the time.

Profile classification, same treatment (`classified` = not `unclassified`;
`supports` = passes §2.1 step 2):

| variant | classified | supports |
|---|--:|--:|
| **default** | **104** | **94** |
| `london_counter_ref="day_open"` | 152 | 143 |
| `ny_manip_requires_london_quiet=False` | 152 | 119 |
| `require_outside_day=False` | 144 | 84 |
| `require_cisd_for_london_reversal=False` | 104 | 94 |

The last row is worth reading carefully: switching the London CISD requirement off
changes *which* profile a day is called (`london_reversal` ↔ `new_york_reversal`) but
not the support verdict, because both profiles imply the same direction. It is a
labelling knob, not a filter.

Alignment:

| variant | days passing |
|---|--:|
| `min_aligned=1` | 164 |
| **`min_aligned=2` (default, the corpus's stated minimum)** | **86** |
| `min_aligned=3` ("preferred for sub-5-minute execution") | 21 |
| `wick_measure="range"` (cut 0.30) | 61 |

Draw rule, over 788 days: proximity 464 buyside / 324 sellside; displacement 431 /
356 / 1 none; bias 374 / 329 / 85 none.

### Distribution of the intermediate objects

- Daily closures: **265** (33.6%) — 196 C2, 69 C3.
- Branch, among biased days: **158 reversal**, **54 continuation**.
- `tradeable_same_day` (§2.4 step 4, the small-wick gate on a reversal day):
  **55.2%** of biased days. The other 45% are the *"large wick → do not trade the
  reversal candle, trade the following one"* case.
- Profiles over 788 days: `unclassified` 684, `new_york_reversal` 66,
  `london_reversal` 18, `new_york_manipulation` 13, `seek_and_destroy` 7.
  **87% of days have no nameable profile**, which is the single largest reason
  `gate_profile` is restrictive. That is a real property of the classification as
  §2.5 states it, not a detector failure — three of the four profiles are defined
  relative to a *daily direction*, so a day with no confirmed bias cannot be any of
  them by construction.

---

## What I could not implement, and why

Ordered by how much it matters.

1. **The OHLC/OLHC candle-shape rule (§2.5) is unrecoverable from OHLC.** The spec
   flags it itself: the rule is about the **order** in which the extremes printed
   (open → low → high → close), and *"on a closed candle it is not recoverable from
   OHLC alone"* **[GAP]**. It is computable from M1 within a daily candle, but that
   is a different object from the rule as stated, so it is absent rather than
   approximated.

2. **"Relevant level" has no definition, and it propagates.** §4.1 says outright that
   *"relevant level" / "key level" / "higher-timeframe objective" / "drawn liquidity"
   are used interchangeably and none is defined* **[GAP]**. It is the discriminator
   between `london_reversal` and `new_york_reversal`, so that whole distinction rests
   on a caller-supplied level set. `relevant_level_frame()` implements the one
   attested default (previous day + previous week extremes) and nothing more. The two
   *decay* rules that are given — a level already traded through stops being relevant,
   and reaching a level not being sufficient without an actual V-shaped reversal — are
   **not implemented**; the second needs a reaction-speed test the corpus quantifies
   only as "roughly half the candle".

3. **The session-dependent confirmation-timeframe map is encoded as data, not
   applied.** §2.4's table (Asia → 1h, London → 15/30m, New York → 5/15m) lives in
   `CONFIRMATION_TF_BY_SESSION`, but `daily_bias` confirms on the hourly for every
   session. Two reasons: §2.4 also says the hourly CISD is *"the single confirmation
   gate used in every video of the weekly-profile series"* and that the map is *"a
   floor, not a ceiling"*; and applying it properly means running the confirmation on
   a different timeframe depending on where in the day the extreme printed, which
   changes what "the day's extreme" even means. The profile layer *does* drop to 15m,
   which is the stated London timeframe.

4. **Weekly profiles (§2.5, second half) are not built.** They are a classification
   of the week by which weekday made the confirmed extreme, chained from the daily
   layer — buildable on top of what is here, but out of scope for this workstream and
   sample-starved anyway (~156 weeks).

5. **Seek & Destroy has no stop and no entry.** §2.5 gives the outside-in target
   ladder but *"no stop is ever given for it"* **[GAP]**, and the stated default is to
   avoid the profile entirely. It is classified and then treated as stand-aside, which
   is what the corpus does.

6. **Profile invalidation is undefined.** *"A single failed continuation signature is
   not grounds to switch the bias"*, and what **would** count is never given
   **[GAP]**. So a profile, once classified, is never revoked intraday.

7. **SMT's "must coincide with a liquidity grab or a POI, not open space" is
   satisfied definitionally rather than tested.** `smt_events` anchors every
   divergence on a *swept prior swing extreme*, which is a liquidity grab by
   construction — so the condition cannot fail as implemented. A stricter reading
   would additionally run `poi_gate` at the sweeping bar; the hook exists but is not
   wired, because it would double-count the same swing.

8. **`framework_transfer`, `relative_strength_asset_selection` and the FX dollar gate
   (§2.6) are absent.** They are multi-asset ranking rules for an index triad or an
   FX basket; with one instrument and one correlate there is nothing to rank, and
   §2.6 gives **no condition for when transfer is legitimate versus when the asset
   should simply be skipped** **[GAP]**.

9. **`gate_no_fade` is inert** — see above. It is implemented faithfully and it
   never fires against anything, because a confirmed bias already implies a daily
   candle closing that way. Kept as a column so the redundancy is visible rather
   than assumed away.

---

## What the next stage should do with this

1. **Do not run the day-level conjunction as an event generator.** 9 days (or 31
   without SMT) is not a sample. Generate events on 4H/hourly CISDs and **join** the
   daily gates on as context columns, using `gates_available_at` to respect
   availability.
2. **Sweep `cisd_scope` first.** It is a genuine **[P]**, it is stated both ways in
   the corpus, and it changes the biased-day count by 69%. Nothing else in the bias
   layer comes close.
3. **Report every POI statistic both ways.** The switch is one keyword and the
   difference on hourly CISD events is 3,679 vs 2,953 — enough to matter, not enough
   to explain an edge on its own.
4. **Pair anything measured here with a matched random-entry control**, per phase 2's
   trap #2, and resolve exits on M1. A gate that keeps 44% of days will look like it
   selects for something purely by shrinking the sample.
