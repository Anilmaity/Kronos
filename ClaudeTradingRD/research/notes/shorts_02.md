# shorts_02 — study notes

**Unit**: `shorts_02` (batch 2 of 4 of the Shorts playlist), 60 videos, 2914 s of runtime.
**Transcripts available**: 57 of 60. Three are empty files on disk and were skipped:
`0c5_pRJTTnU` ("NASDAQ ICT Setup"), `EwlWJnZjfrY` ("NY Open ICT Setup"), `yiJOHXbov3Q` ("OLHC").
All three are short, generically-titled clips that are probably silent chart replays.
**Output**: 34 YAMLs in `concepts/_inbox/shorts_02__*.yaml`, carrying 111 verified source
entries across 51 distinct videos. **One new concept id; 33 reuse existing ids.**
No duplicate uploads were found in this batch (every transcript hashes distinctly).

---

## The genre, and what fraction was substantive

The format is uniform: a marked-up chart, a few bars replayed, and the decision narrated in
one breath. 51 of the 57 readable Shorts are teaching clips with at least one rule in them.
Of the six that are not, one is pure promotion (`zShHFTM2MiI`, a Lucid Trading discount code)
and one is a platform-UI tutorial with no market content (`PFKSridKK-8`, the TradingView
reverse-position button). The remaining four are competent chart walks that restate concepts
already recorded, with no sentence worth a new `sources` entry.

What almost none of them are is **new**. This batch is a compression of material already
studied at length: 56 of 57 restate something already among the 383 concepts in `INDEX.md`,
and the right action for those was to reuse the id and attach the Short as one more `sources`
entry. Exactly **one** claim in the whole batch could not be placed anywhere in the library —
and it happens to be the single most valuable number the library was missing (below).

The genre's advantage did hold. Because 30 seconds has no room for both a worked example and
a hedge, he repeatedly states as a bare sentence what the hour-long version leaves implicit.
Four of those one-liners are worth more than everything else in the batch:

- **"the wick is larger than the body"** (`TND1aTpnq5c`) — the wick-size threshold.
- **"A higher time frame wick is a lower time frame reversal"** (`rTnu3ZEb2ZE`).
- **"A propulsion block is an order block off of another order block"** (`W2ZilDoBnWU`).
- **"A New York reversal daily profile is when London doesn't form a reversal"** (`RZsgWeMBWGI`).

---

## Transcript hygiene

All 57 are `yt-dlp-auto` captions with no timestamps, so **every YAML in this unit omits
`approx_time`**. The recurring artifacts, each confirmed by reading around it:

- **"candle 2" → "candle to"**, without exception in this batch. `8fseTcJMiBo`, `WksB2zmI3n8`,
  `5Y-8G9eA35o`, `BmTJEWru_9U` and `zYDn5B3UNBw` all read "a candle to closure". Quotes are
  preserved verbatim including the artifact — do not "fix" them; the validator compares against
  the caption text, and a tidied quote fails.
- **"reach" → "wretch"**: `MewB_Ero8vo` opens "we have wretched above previous day high".
  It is the only instance in this batch, but it is load-bearing (the whole clip is about what
  happens after price *reaches* the previous day high).
- **"Judas" → "Judith"** in `JZDI--Jm0bA` ("with Judith swing or an order block"). The same
  clip's sibling `QRxG7a_JB08` says "Judah swing", so the two spellings are the captioner
  guessing at the same word twice.
- **18:00 is never rendered as 18:00.** `RsPf6aNXtNw` says "with 18,800, midnight, 10, and 2"
  and then "for the 188 and 0, that will be the daily candle". The reading is fixed by the
  surrounding 4-hour grid (10:00 and 14:00), not by the digits.
- **Minute timeframes are mangled everywhere**: "15-minut", "5minut", "3inut", "30-inut",
  "60-minute" survives intact. `nwbHvFCh0bo` — the timeframe-pairing table — is the worst
  affected, so its quotes were chosen to avoid the mangled tokens.
- **Order-block candles**: "upclose" appears as "upcloed", "uplose", "downcloed" and "downlo"
  in `W2ZilDoBnWU` and `QqvT4HoQ_ds`.
- **Two transcripts are truncated mid-sentence** by the caption fetch, and in both cases the
  cut lands on the rule: `F5jfz-2JlRw` ends at "I will be using the negative one as a", and
  `W2ZilDoBnWU` ends at "break the mean threshold of a propulsion". Both cuts are recorded in
  the relevant `ambiguities`.
- **Disfluencies are transcribed**: `MR7cu2oQvck` carries "[clears throat]" and `f6Ca0EY95Sw`
  carries "[snorts]" mid-sentence. I avoided quoting across them.

---

## The one genuinely new thing: a wick-size threshold

`TND1aTpnq5c` ("How OHLC Plays Out in Reversal Candles") is a 52-second clip enumerating a
candle-type taxonomy. Describing a reversal candle he asks, of the chart, *"what do you notice
about this wick relative to the body?"* and answers: **"the wick is larger than the body"**.

This is the first explicit wick-size comparison found anywhere in the corpus. Both existing
library entries that depend on it say so in their own `ambiguities` — `reversal-candle-quality`
records that "wick size thresholds are relative and unquantified", and `daily-ohlc-candle-shape`
records that "no body-to-range or close-location threshold is given". So it is a real gap-fill,
not a restatement, and it earns the one new id in this unit:

> `candle-type-wick-to-body` — **Candle Types Classified By Wick Size Relative To Body**

Its companion is `Vh_iZkhAzAI` ("Indecision Candles"), the *last* member of the same
taxonomy: **"a longer wick on each side, and the body is fairly small"**, with the open and
close "very close to each other". Note the two clips say "the *next* candle type" and "the
*last* candle type", which means at least one earlier member — almost certainly the
directional/expansion candle — was published as a Short that is **not in this unit**. That is
recorded in `ambiguities` so nobody assumes the expansion threshold is simply the mirror.

Three caveats are written into the concept rather than smoothed over, because they decide
whether a detector can be built:

1. It is a **comparison, not a ratio**. `wick > body`. No percentage, no multiple, no tolerance
   band for the near-equal case.
2. **Which** wick is not stated. He points at a chart with one dominant wick, so single-wick is
   the likely reading, but a candle with two medium wicks is uncovered.
3. He narrates the *order* of the extremes ("we open, we're making a move higher... then price
   reversed"), which is not recoverable from OHLC alone. The wick/body comparison itself is.

I also attached the same quote to `small-wick-expansion-rule` — the 42-rule, 30-source gate
that this number actually unblocks — paired with `jjmRp8oTfPo`'s **"They have a small wick and
a large body"** for expansion days. The contrapositive (small wick ⇔ wick < body) is flagged
in that file as *my inference*, not his words. Neither Short states it.

---

## Answers found for the other blocking terms

The brief named four blockers. Honest scorecard:

**Kill-zone / session HOURS — partially answered, and it does not add to the library.**
`A_mURVLMD-k` puts a clock on London twice: *"We will drop down during London or 2:5"* and
*"we open we put in a high during London or 2 to 5"*. That is 02:00–05:00, matching the
`daily-profile-session-windows` entry the library already holds (London 2–5). It is
independent corroboration from a second video, not new information, and **no timezone and no
a.m./p.m. marker appear anywhere in the clip** — the EST reading is still inference from the
surrounding corpus. New York is never given hours in this batch; the only clock attached to it
is via the important-time-levels grid (08:30 / 09:30 / 10:00 / 14:00). So the 49 concepts
gated on "kill zone" remain gated.

**"Aggressive" — the closest thing yet to an operational test.** `Ix8l6yDRpp8` defines a fair
value gap as a three-candle pattern where the wick of the first and the wick of the third do
not overlap, *"showing aggressive price action through this area"*. That makes non-overlapping
wicks the **evidence** of aggression. It is not a threshold — it says a gap *shows* aggression,
not how much — and it does not license rewriting "aggressive" as "there is an FVG" everywhere
else. Recorded in `fair-value-gap` with exactly that hedge.

**"Strong" and "shallow" — nothing.** `Of244GeO2Ro` says a trend has "expansion, shallow
retracements" and moves on. No quantification anywhere in 57 clips.

**Which price of the opposing-candle series a CISD closes through — not answered, but the
adjacent C3 question is.** Two Shorts state the candle-3 test identically and crisply:
*"price is going to close over the body of candle two"* (`O4YAMIey-JQ`) and *"we close back
above the body of candle two"* (`8HBZ-jlK18I`). That is the **body of C2**, not the
opposing-*series* price the brief asked about, and neither clip says which body edge (open,
close, or the further of the two) — recorded as an ambiguity in `fractal-model-c3`.

One unlooked-for bonus: `high-vs-low-resistance-liquidity` carried the note that "the
dedicated High Resistance vs Low Resistance Liquidity video has no transcript on disk, so the
definitive statement is still missing". `go3ae4yzKDY` supplies the operational half of it:
*"I want to be targeting low resistance liquidity"* and *"having high resistance liquidity for
my stop loss"*, with low-resistance liquidity identified structurally as *"a high with a lower
high next to it"*.

---

## Thematic groupings

### 1. The candle-classification cluster (the taxonomy Shorts)
`TND1aTpnq5c`, `Vh_iZkhAzAI`, `rTnu3ZEb2ZE`, `ldCvD6iAbdM`, `_CjuP__edac`, `ZzHzsDepC2Y`,
`AArNO58yBiw`

These read as a single mini-course cut into pieces. Reversal candle (wick > body), indecision
candle (small body, wicks both sides), the identity that a higher-timeframe wick *is* a
lower-timeframe reversal, and then the three-outcome decision table: close outside the previous
range → continuation; close back inside after taking one side → reversal; take both sides and
close back in → consolidation. `AArNO58yBiw` runs it forward over a week of daily candles as a
drill, including the "three days of expansion, expect a new phase" count.
→ `candle-type-wick-to-body` (new), `htf-wick-formation`, `next-day-model`, `phases-of-price`.

### 2. Market structure labelling
`d0x29IO1CQQ`, `A8SneEwpQrc`, `Rpu0iLIfaSw`, `w-lr4VlpCMs`, `XCYmGJWnsAg`, `9jvWodPJgVI`

The short-term / intermediate-term / long-term ladder, built forward on a live 5-minute chart.
Two findings worth keeping. First, `d0x29IO1CQQ` names the second construction — *"there's
also a **rebalanced** intermediate term high and low"*, formed when price trades into a fair
value gap and away — which the library described but did not have a name for. Second,
`A8SneEwpQrc` defines the long-term extreme by **cause**, not by nesting: it is the low formed
off the *reaction of the higher-timeframe level*. `w-lr4VlpCMs` supplies the discipline that
makes the whole ladder usable: a lower-timeframe structure shift *"is actually just a
retracement to a higher time frame PD array"* and will fail if it opposes it.
→ `intermediate-term-swing-formation`, `advanced-market-structure-labeling`,
`structure-requires-htf-context`, `relevant-swing-separation`, `swing-forming-candle-selection`.

### 3. Daily profiles, by session
`A_mURVLMD-k`, `cS8942LZ5Uw`, `f6Ca0EY95Sw`, `RZsgWeMBWGI`, `j65mUdS9npQ`, `jjmRp8oTfPo`

Each profile is defined by what **London** did, which is the cleanest framing of the set:
London reversal = London puts in the wick between 2 and 5, New York continues off it
("basically a classic expansion candle"). New York reversal = London *doesn't* form a
reversal, so the reversal happens later and the higher-timeframe wick is larger. New York
manipulation = London consolidates *or fails to reach a higher-timeframe PD array*, then New
York manipulates London's range. `j65mUdS9npQ` adds the failure branch — a first touch that
fails to change the state of delivery is the instruction that a new low comes first.
→ `london-reversal-profile`, `new-york-reversal-profile`, `new-york-manipulation-profile`.

### 4. Time levels and the clock
`JZDI--Jm0bA`, `RsPf6aNXtNw`, `QRxG7a_JB08`, `8fseTcJMiBo`, `MewB_Ero8vo`

The function split is stated twice, independently, and the two accounts agree: 18:00 and
midnight frame the **daily** OHLC; 10:00 and 14:00 frame the **4-hour** OHLC; 08:30 and
midnight double as premium/discount and support/resistance; midnight, 08:30 and 09:30 are
where the Judas swing / order block is looked for. `8fseTcJMiBo` adds a sequence anchored at
**08:00**, not 08:30 — an hourly candle-2 closure at 8 a.m. licenses anticipating the 9-to-10
hourly candle (or the 09:30 open) to expand, with the entry taken on the pre-09:30 continuation.
→ `important-time-levels`, `new-york-intraday-time-levels`, `midnight-open-directional-filter`.

### 5. Entries: order blocks, breakers, propulsion blocks
`VyOsUgZjmzY`, `DUIhKL5v1uQ`, `W2ZilDoBnWU`, `QqvT4HoQ_ds`, `wfkLTu96Dh8`, `v7gxt39p1NU`

The definitional Shorts in this batch are unusually tight. Continuation order block: *"an order
block that is not formed at the reversal but rather within a continuation"* — and the reason to
prefer it is stated as a choice, since taking the reversal order block "is trading a reversal".
Breaker: the strict four-point sequence low → high → lower low → higher high, then mark the
up-close series between the low and the high. Propulsion block: *"an order block off of another
order block"*, whose distinguishing property is that the opening price is very sensitive and
the mean threshold must not break. `v7gxt39p1NU` numbers the reversal ladder out loud —
step one turtle soup, step two inversion, step three CISD/order block — which is the same
ladder `order-of-reversal` already holds, now with the speaker's own step numbers.
→ `continuation-order-block`, `breaker-block`, `propulsion-block`, `order-of-reversal`.

### 6. Bias, EQ and profile confirmation
`BmTJEWru_9U`, `CRaMFN6di6U`, `f_yfS7JNR60`, `08MZAXZ5WAM`, `Us6Qsl6Tu9E`, `LwC6OF_eRdQ`,
`O4YAMIey-JQ`, `8HBZ-jlK18I`, `zYDn5B3UNBw`

`BmTJEWru_9U` is the sharpest statement in the corpus of the EQ as a **bias invalidator**:
the previous day high is never taken, but price disrespects the EQ and never forms a bullish
continuation, and that alone flips the framework bearish toward the previous day low. Set
against it, `08MZAXZ5WAM` insists a single failed continuation signature is *not* grounds to
switch — *"I'm still bullish as I determined earlier in the day"* — and `f_yfS7JNR60` resolves
the tension only by deferral: *"let the daily profile confirm or invalidate my thought
process"*. That is exactly why `daily-profile-confirmation` stays `underspecified`: one clip
shows confirmation, the other shows the bias held through a failure and the day going the
other way, and no test separates them. `zYDn5B3UNBw` supplies the hard gate that does exist —
no lower-timeframe CISD, no valid setup, and the indicator will not print one.
→ `equilibrium-eq`, `daily-profile-confirmation`, `fractal-model-c3`, `indicator-print-conditions`,
`structure-requires-htf-context`.

### 7. Targets, projections and liquidity
`F5jfz-2JlRw`, `fsxbkMiHcEw`, `GobnfnJmIBA`, `go3ae4yzKDY`, `Ix8l6yDRpp8`

Two Shorts state symmetric halves of one target-selection rule. If the manipulation leg is very
large, the projections land beyond the logical liquidity, so target the -1 or the liquidity.
If the liquidity is beyond the projections, take profit at the projections, because a
retracement can come first. Together they imply "take whichever comes first" — an inference,
flagged as such, since neither clip generalises. `GobnfnJmIBA` gives the ideal: the projection
and the liquidity coinciding. Both cases were already in `standard-deviation-projection`; the
Shorts are corroboration, not new rules. `Ix8l6yDRpp8` states the internal/external rotation in
about forty words: internal liquidity *is* a fair value gap, external *is* highs and lows, and
a sweep that fails to displace rotates price back to the internal.
→ `standard-deviation-projection`, `high-vs-low-resistance-liquidity`,
`internal-external-rotation`, `fair-value-gap`.

### 8. Execution, sizing and the weekly profile
`5Y-8G9eA35o`, `sAh3ZMkzzpQ`, `JPB273sQJsk`, `nwbHvFCh0bo`, `_-aPdmLe6zw`, `f1DtFWzdrIA`,
`1vSentM2RnI`

`nwbHvFCh0bo` recites the whole pairing table and adds the row the library lacked at the top —
**weekly pairs with the 4-hour** — plus the bottom-up selection procedure for a three-timeframe
stack (choose the entry timeframe, take its partner, take that partner's partner). `5Y-8G9eA35o`
is his favourite setup end to end: daily C2 + 4-hour C2 + 15-minute CISD, entry *at market on
the new open*, stop at the protected low, 2R or the failure swings at roughly 4R. `JPB273sQJsk`
shows fixed-dollar sizing with a concrete number ($300) and the practical escape when the stop
is too tight for a full-size contract: switch to micros. `_-aPdmLe6zw` deliberately shows an
*imperfect* TGIF — Thursday is the reversal day, Friday the continuation — opening with
"you will notice not everyone is picture perfect".
→ `timeframe-alignment-pairs`, `ttfm-favorite-daily-4h-15m`, `protected-swing`,
`position-sizing-fixed-risk`, `tgif-setup`, `level-to-trade-away-from`, `phases-of-price`.

---

## Shorts that contributed nothing new

Nine of the 60, explicitly:

| video_id | title | why |
|---|---|---|
| `0c5_pRJTTnU` | NASDAQ ICT Setup | no transcript (empty file on disk) |
| `EwlWJnZjfrY` | NY Open ICT Setup | no transcript (empty file on disk) |
| `yiJOHXbov3Q` | OLHC | no transcript (empty file on disk) |
| `zShHFTM2MiI` | Lucid Trading … Use Code TT | pure promotion — prop-firm discount code, account sizes, expiry date. No market content of any kind. |
| `PFKSridKK-8` | How to Reverse Positions in TradingView + NinjaTrader | platform-UI tutorial. Explains what the reverse button does. No rule about when to reverse, so nothing decidable. |
| `MR7cu2oQvck` | Find Your Invalidation → Place Your Stop Loss | competent oil walkthrough, but its only distinctive line — giving oil "a little bit more room than normal" because it sweeps equal highs — is already a verbatim rule in `stop-loss-placement` ("for instruments that habitually sweep (he names oil), deliberately allow extra room"). |
| `WksB2zmI3n8` | How the Fractal Model Set Up This ES Short | ES example of daily C2 + CISD + T-spot hold + consolidation-then-manipulation. Every element is already recorded in `t-spot`, `fractal-model-c2` and `consolidation-open-whipsaw`; the clip adds no rule the worked example does not already illustrate elsewhere. |
| `rYZIdeegGx8` | How to Approach Reversals Within the Fractal Model | restates expansion→reversal→continuation-signature and the relevant-low choice. Fully covered by `phases-of-price` and `relevant-swing-separation`; the one distinctive remark (preferring the candle that *created* the swing low) is `swing-forming-candle-selection`, better stated in `9jvWodPJgVI`. |
| `Of244GeO2Ro` | Manipulate the High → Trend Continues Lower | manipulation-then-continuation walk. Its only general statement — trends have "expansion, shallow retracements" — is one clause with no quantification, and `shallow-retracement` already holds it with three sources. |

The four judgement calls there (`MR7cu2oQvck`, `WksB2zmI3n8`, `rYZIdeegGx8`, `Of244GeO2Ro`)
are all *corroboration-only*: real teaching, but attaching them would have added source count
without adding evidence about anything contested. If a later pass wants maximum witness counts
rather than maximum signal, those four are the ones to revisit.

---

## Files produced

34 YAMLs at `concepts/_inbox/shorts_02__<id>.yaml`. All pass `python/validate_concepts.py`
(111 source entries, all 111 carrying a quote; every quote ≤15 words and verbatim in the cited
transcript).

**NEW id (1)**

- `candle-type-wick-to-body` — Candle Types Classified By Wick Size Relative To Body

**EXISTING ids reused (33)**

`advanced-market-structure-labeling`, `breaker-block`, `continuation-order-block`,
`daily-profile-confirmation`, `equilibrium-eq`, `fair-value-gap`, `fractal-model-c3`,
`high-vs-low-resistance-liquidity`, `htf-wick-formation`, `important-time-levels`,
`indicator-print-conditions`, `intermediate-term-swing-formation`,
`internal-external-rotation`, `level-to-trade-away-from`, `london-reversal-profile`,
`midnight-open-directional-filter`, `new-york-intraday-time-levels`,
`new-york-manipulation-profile`, `new-york-reversal-profile`, `next-day-model`,
`order-of-reversal`, `phases-of-price`, `position-sizing-fixed-risk`, `propulsion-block`,
`protected-swing`, `relevant-swing-separation`, `small-wick-expansion-rule`,
`standard-deviation-projection`, `structure-requires-htf-context`,
`swing-forming-candle-selection`, `tgif-setup`, `timeframe-alignment-pairs`,
`ttfm-favorite-daily-4h-15m`.

One of these — `relevant-swing-separation` — is filed `underspecified` along with
`daily-profile-confirmation`; every other file is `specified`, because the Shorts format tends
to produce either a decidable rule or nothing at all.
