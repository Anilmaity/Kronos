# Study notes — `shorts_04`

**Unit:** 49 YouTube Shorts, 22–61 seconds each (~39 minutes of speech total).
**Transcripts available:** 49 / 49. **None missing.**
**Concept drafts produced:** 29 — **0 new ids, 29 reusing existing ids.**
**Shorts that contributed a rule, count or definition the library did not already hold:** 20 of 49.
**Shorts that were pure corroboration (cited only as an extra evidence line):** 28.
**Shorts that contributed nothing at all and are uncited:** 1 (see the explicit list at the end).

---

## What this genre is, and what it is worth

Batch 4 of the Shorts is the tail of the alphabet — every title from "Using…" through "You Want…"
— and it is the most repetitive slice of the corpus studied so far. Essentially every clip is a
single annotated chart replay of the fractal model: a candle 2 closure at a point of interest, a
lower-timeframe change in the state of delivery, a continuation entry off an opposing candle,
2R. The concepts are already in the library, several of them with thirty-plus source lines.

So the honest output of this unit is **zero new concept ids**. That is not a failure of reading;
it is the correct result, and it is worth stating plainly because it is evidence about the
library's coverage: 383 concepts drawn from the long-form videos absorbed all 49 of these Shorts
without a gap. Every candidate that looked new on first pass turned out to be already present —
the "no candle 2, wait for candle 3" branch is already in `fractal-model-c3`; the
large-manipulation-leg → −1 target is already a detection rule in `standard-deviation-projection`
with the same "judged by eye" caveat; separation as a relative-strength tool is already step 2 of
`relative-strength-asset-selection`; the stacked-fair-value-gaps-as-one rule is already in
`fair-value-gap` citing the identical sentence from the long-form original; and the candle-count
threshold for "swift" is already in `v-shape-reversal-speed`.

What the 30-second format *does* buy is compression. Twenty of the 49 state as a flat declarative
sentence a rule the hour-long version only demonstrates, and those one-liners are the yield.
Six of them are worth quoting up front.

**On low- vs high-resistance liquidity — the library previously had only a market-conditions
reading; this is the mechanical one, in seven words:**

> "Low resistance liquidity is just a failure swing." — `L9Gd5p14uBE`

**On expansion, defined in one breath using both blocking adjectives:**

> "An expansion is a one-sided aggressive move that has very shallow retracements" — `46VIOAlxmEE`

**On retracement, its exact complement:**

> "A retracement is a slow shallow move opposing the higher time frame trend." — `RdQdorNCezI`

**On the continuation-vs-consolidation boundary, with an actual candle count:**

> "It takes 1 2 3 candles and we're struggling to close below this level" — `7v9Y2GHNqCg`

**On the whole doctrine, in eight words:**

> "Trading continuations is far easier than trading reversals." — `yZVevl-tMHA`

**And the higher-timeframe wick, stated causally rather than descriptively:**

> "We have expansion up met with expansion down forming a reversal." — `yku6idnLqSo`

None of these is a number. See the "what is still missing" section — the answer on wick size is
disappointing in a specific and informative way.

---

## Theme 1 — Wick size: the Short that asks the question and does not answer it

`U1NJUh1RqMw` is titled *Why You Need a Small Wick to Confirm a C2 Reversal*, opens with "looking
to trade a reversal in candle 2, I need a small wick", and then asks, in his own words, "What does
that look like?" — which is precisely the question the library has been unable to answer from five
long videos.

The answer he gives is **a procedure, not a ratio.** Price sweeps candle 1's low, displaces back
into the range, and closes over the series of down-closed candles; that lower-timeframe change in
the state of delivery is what licenses the claim "this allows me to anticipate that this higher
time frame wick has formed". The wick is never measured. It is *confirmed* — declared finished by
the lower-timeframe closure.

This is worth recording (it is in `shorts_04__small-wick-expansion-rule.yaml`) but it must be
recorded honestly, because for a detector it is **circular**: you learn the wick was small only
after the lower-timeframe closure you were going to trade anyway. It converts an unquantified
filter into a confirmation step, which is progress in usability and zero progress in
quantification. The ambiguity block on that draft says so explicitly.

The rest of the wick cluster is the half-wick rule, and here the Shorts are genuinely good, because
`KGw0lLST3pU` and `UFejYNnDCuA` are a deliberately matched pair — *respected* and *not respected* —
which turns the rule into a clean if-then. Mark 50% of the higher-timeframe reversal candle's wick;
the next period's low should form in the upper half; a **close through** 0.5 flips the read and the
extreme is expected to be taken out. `WLFThXBRk0I` and `OuyHuNe-IP0` restate the same thing. One
asymmetry is worth flagging and is recorded as an ambiguity: the failure case is stated as a
*close* through the level, while the success case is shown as a *wick low* in the upper half, so
the two branches are not tested the same way.

`Nbs0gsth2jw` supplies a variant construction — mark the **entire range of the candle 3** rather
than the reversal wick, and require the upper half of that. Which reference is canonical is not
resolved anywhere, and that is now noted on `upper-half-eq-expansion-filter`.

Finally `yku6idnLqSo`, at 22 seconds the shortest clip in the unit, states the mechanism that makes
a large wick possible at all: expansion up met with expansion down on the lower timeframe *is* the
higher-timeframe wick. That is a causal claim, and it is falsifiable — drop inside any large wick
and check whether the structure is two expansion legs or a consolidation.

---

## Theme 2 — The two-part validity gate, and using it to *prune*

Nine Shorts (`p1xrHuEHpQY`, `jo2D1AOuxHM`, `OjSyhPw1WIw`, `La4MlftJc14`, `I8_O-4ZifrM`,
`0fhZ_jpespw`, `0st2qhpQ5QE`, `Nbs0gsth2jw`, `Oio_QeRPVQQ`) are all one lesson seen from different
angles, and taken together they reframe the model in a way the long videos do not: the candle
closure rules are **a filter applied to swings you have already marked**, not a generator of
setups. `p1xrHuEHpQY` literally marks six swing highs and lows and then deletes them one at a time
— this one has no valid closure, this one has a valid closure but no point of interest, this one is
mechanically valid but sits too close to another swing — until two survive. The stated summary is
"if we do not have a point of interest or a valid closure" he will not choose random swing points.

The third deletion is the interesting one, because it is openly discretionary ("does it make sense
to leave this high right here so close? Probably not"), which is the separation rule doing work
inside the C2 gate. It is recorded on `fractal-model-c2` as a discretionary step with the
ambiguity that no distance threshold exists.

`OjSyhPw1WIw` is the best single clip in the unit for teaching value: it is entirely a *negative*
case. Most people call a candle 2 ideal because it closes over candle 1's body — wrong. Ideal
requires that the same bar simultaneously create a protected swing, i.e. close over the series of
down-close candles **into the point of interest**, and he walks to the exact two candles that
define the level price would have needed to clear. This matches `ideal-formation` exactly and gives
it a second, independent source.

`I8_O-4ZifrM` gives the framing that makes the whole thing memorable — "both parts of the fractal
model, the candle closure and the swing point confirmation" — and states the payoff negatively:
waiting for part two is what avoids the loss shown on screen.

`Nbs0gsth2jw` and `Oio_QeRPVQQ` are the two branches of the missing-C2 case. If the candle at the
point of interest did not close back inside its previous candle, let **one** more candle print and
test for a candle 3 closure (defined as closing over the body of candle 2). If neither appears,
`Oio_QeRPVQQ` gives the stand-aside rule in the cleanest phrasing in the corpus: "my model would
not align with it as I do not have a candle two" — anticipation is allowed, participation is not.

---

## Theme 3 — Continuation quality, and the one place a number appears

`7v9Y2GHNqCg` is the single most useful Short in the unit for a backtest, because it is a
**failure-mode** clip and it narrates a count. At a point of interest with a V-shaped wick, the
continuation is expected to close through the level quickly. In the rejected example it does not:
"It takes 1 2 3 candles and we're struggling to close below this level. On the fourth candle, we
take out this low." Verdict: "it just takes too long to form this continuation… Once we do get the
closure, this is now just a consolidation" — and it is no longer tradeable as a continuation.
`ZEK8fDzxClA` supplies the accepted counterpart, "a pretty swift closure over. It only takes a
couple candles."

That is a genuinely decidable rule, but the draft records it carefully: three is *described*, not
legislated, the count is narrated over a single example, and the timeframe the candles are counted
on is never named. It also corroborates rather than establishes — `v-shape-reversal-speed` already
carries "one, two, maybe three" from a long-form video. What is new here is the explicit
**reclassification** consequence: failing the speed test does not merely weaken the setup, it
converts the structure into a consolidation and voids the eventual closure.

`ZEK8fDzxClA` also contributes a stand-aside that is easy to miss: a continuation that does not
reach into a point of interest is not one he would consider, "now, if you use correlated assets and
we have an SMT here, sure you can use that, but I would not consider that" — SMT is explicitly not
accepted as a substitute for the point of interest here, which is a slightly harder line than
`smt-swing-point-substitute` takes elsewhere.

The continuation-entry recipe itself (`vBAYmH7XCks`, `iwGyMV0BDSY`, `OFfjyo4-s6U`, `46VIOAlxmEE`)
is unvarying across four clips: retrace into an important level, generally a fair value gap →
opposing candle prints into it → close over that series → the close creates the new protected
swing, which is the invalidation → enter on the retest, target 2R or the drawn liquidity.
`46VIOAlxmEE` states the dependency in the right order: "close over the series of down closed
candles, and after that occurs, I then have an invalidation, and I can take an entry" — no
protected swing, no stop, no trade.

---

## Theme 4 — Phases of price, stated as definitions rather than demonstrated

`46VIOAlxmEE` (39 seconds) is unusually complete: it defines expansion, says when to expect it, and
says how to interact with it. The definition uses both of the corpus's blocking adjectives at once
— "one-sided aggressive move that has very shallow retracements, if any at all" — and the timing
rule is given as a cycle: expansion follows a consolidation or a retracement, because "small ranges
lead to large ranges, and large ranges lead to small ranges." `RdQdorNCezI` is its mirror image for
retracement, and `eKbZYMn3_bU` supplies the operational contrast that makes the pair decidable:
"Do we want to see expansion back lower? No, that is a reversal. We want to see a slow shallow
move." The classifier is therefore three-way and exclusive — after an expansion leg the next
structure is a consolidation, a retracement, or an opposing expansion, and only the first two are
compatible with a continuation.

`Uzl3zYzr90Y` and `HVPIhbOxnls` run that classifier live and give it teeth as an **invalidator**:
"if we have expansion met with expansion, then this low gets taken out." `HVPIhbOxnls` also shows
the observation discipline — "we let two candles print here" before classifying — and the trio of
agreeing reversal signals (daily closure + CISD + expansion-met-with-expansion). No rule is given
for what to do when those three disagree, which is now an ambiguity on
`expansion-sequence-quality`.

`MtczT00fhJI` is the stand-aside case and contains the most disciplined sentence in the unit:
"Even if this was to work out, price is just consolidating here… it is not meeting the requirements
for my model." He also states that a run out of such a consolidation is usually just the
consolidation highs being taken before price goes lower — a specific, testable prediction attached
to a no-trade decision.

---

## Theme 5 — Relative strength, as an ordered fallback

`1eL9Edk1FrI`, `B1tTNDOtFaw` and `nNfhTDkyhtw` are consecutive lessons and they are best read as a
priority list, which is how they are recorded on `relative-strength-asset-selection`. The
precondition is stated flatly and is easy to skip: "you can only do this with correlated assets",
which "should have the same structure, but sometimes they do not." Tool 1 is SMT. Tool 2 is
invoked explicitly when tool 1 is unavailable — "there's not really a very obvious SMT in here…
This is where we can use separation" — and measures how far each asset has travelled from the
shared reference low. Tool 3 is the candle closure itself: "This is a doji candle, while this is an
engulfing bearish candle."

The ordering is implied by the narration, never stated as a rule, and none of the three tools has a
threshold. That is now the headline ambiguity on the draft.

`25V-sGyMj_M` and `_VquvUgdQmA` are the currency version and are unusually clean as a two-step
decision: dollar direction first, then read EURGBP to find the weaker foreign leg (bullish EURGBP →
pound is weaker → GBPUSD is the pair), then cross-check on the individual closures. Both Shorts are
careful to call the cross-check "an extra confluence", not the signal.

---

## Theme 6 — Small clusters worth one line each

**Stops** (`T1F4aT_7ppg`). The cleanest binary in the unit. The stop always goes on a protected
low, but either at the very low (*full invalidation* — safer, 2R further away) or at the bodies of
the opposing candles (smaller stop, faster 2R, and "price could come stop me out before actually
invalidating my idea", a cost he says you have to accept). No rule is offered for choosing.

**Breakers** (`8FtjVWZcZN8`). Restates the continuation-breaker recipe and — new for this concept —
gives its market-structure justification: short-term low, sweep of it, then "anticipating another
short-term low, which forms an intermediate-term low." Also the messy-wick fallback: "with these
wicks kind of everywhere, I will focus on the bodies."

**Entries at the open** (`VtFC9SCnlYM`). Supplies a crisp gate the library lacked a formulation
for: an at-open entry is permitted "when I have an invalidation very close to the opening price",
because the low is already expected to hold before the candle opens. Unquantified, but it is at
least the right variable — proximity of the *invalidation*, not of the entry.

**The full recipe** (`gLul2OZQe9Q`). Forty-six seconds containing the whole model end to end: HTF
bias → candle 2 closure → 5-minute CISD → point of interest in the T-spot → 1-minute inversion →
entry → 2R. `Hi8faa5u2uw` gives the T-spot's purpose in one line: it is where all entries are
looked for, "which is where I'm anticipating the higher time frame wick to form."

**London vs New York** (`2ctrcNs4tFo`). The discriminator in one sentence: "London never reached a
relevant PD array." This is exactly `relevant-htf-pd-array-test` and it confirms it — while also
demonstrating the problem, since it uses "London" and "New York" as hard gates and attaches no
clock times to either.

**Weekly profile** (`oBkh-__IL-I`, `_VquvUgdQmA`). Two live runs of the Thursday Counter, which
previously had a single source. Setup: three consecutive expansion days into a relevant level →
new phase of price due → Thursday counters, confirmed on the hourly by the previous day's extreme
taken with an SMT plus a CISD → trade Thursday's continuation or wait for Friday.

**Minimalism** (`__E1fj1n4xg`). A deliberate over-marking demo: he points out the turtle soup, the
inversion, the CISD, a breaker and several fair value gaps — all real — then asks whether it helps
or whether it will "cluster my chart and make things more confusing", and answers that he needs
only the sweep plus the closure through the series that made the extreme.

---

## What this unit did *not* find (the blocking terms)

- **Wick size.** No ratio, percentage, fraction or bar count anywhere in 49 Shorts. `U1NJUh1RqMw`
  asks the question directly and answers with a confirmation procedure. **Still open.**
- **Session / kill-zone hours.** **Nothing.** Not one clock time appears in the unit except a
  passing "we have 10:00 a.m." in `HVPIhbOxnls`. `2ctrcNs4tFo` uses London and New York as hard
  gates with no hours attached, which is the failure mode in its purest form. **Still open.**
- **"Aggressive."** Used inside the definition of expansion (`46VIOAlxmEE`) and as narration
  ("a pretty aggressive move", "an aggressive displacement lower"). Never quantified. **Still open.**
- **"Strong."** Used only comparatively across correlated assets (`nNfhTDkyhtw` contrasts a doji
  against an engulfing candle). No absolute test. **Still open.**
- **"Shallow."** Now has a clean qualitative definition on both sides — expansion has "very shallow
  retracements", a retracement is "a slow shallow move" — and an explicit failure test (an
  expansion back the other way is a reversal, not a retracement). No number. **Partially advanced.**
- **Which price of the opposing-candle series a CISD closes through.** **Not resolved.** The unit
  says "closed through the series of down closed candles" roughly twenty times and never names a
  price. `OjSyhPw1WIw` comes closest — it identifies the two down-close candles and says price
  "would have needed to close over this level" — but the level is pointed at on the chart, not
  named. The only adjacent evidence is that *bodies* are the reference for stop placement
  (`T1F4aT_7ppg`) and for a messy breaker (`8FtjVWZcZN8`).

---

## Transcript hygiene

All 49 transcripts are yt-dlp auto-captions, plain prose with **no timestamps**, so every draft in
this unit omits `approx_time` entirely.

Known artifacts, verified in this unit:

- **"candle 2" → "candle to".** Rampant: 17 occurrences of "candle to closure" against 13 of
  "candle two closure", sometimes both inside the same clip. Every quote in this unit was
  copy-pasted with the artifact left intact rather than corrected — e.g. `OjSyhPw1WIw`'s
  "price has to make a candle to closure while simultaneously creating a protected swing".
- **"reach" → "wretch"** does occur elsewhere in the corpus but **not once in these 49 files**;
  "reach" is captioned correctly throughout.
- **"2R" → "two hour".** `yZVevl-tMHA` renders the target as "looking for two hour" and "we hit two
  hour there". Noted on `continuation-over-reversal`. Elsewhere it survives as "2 R" (`gLul2OZQe9Q`)
  or "2 R" / "two R" inconsistently.
- **"gap" → "cap" / "up".** `Hi8faa5u2uw` has "we reach down into a fair value cap";
  `46VIOAlxmEE` has "generally a fair value up". Both plainly mean *gap*; both are quoted as-is or
  avoided.
- **"below" → "blow".** `7v9Y2GHNqCg`: "a nice quick move lower closing blow here".
- **"0.5" → "five".** `UFejYNnDCuA`: "falls through five of that wick" — meaning 0.5. The same clip
  gets it right two sentences later ("the closure through 0.5 of the wick"), which is how it is
  disambiguated.
- **Missing spaces / mangled words.** "5minut" (`gLul2OZQe9Q`), "downlosed candles"
  (`Hi8faa5u2uw`), "one 1 minute time frame" spacing.
- **HTML entities.** `&amp;` appears for "&" in `nNfhTDkyhtw` and `1eL9Edk1FrI` ("S&amp;P").
  Harmless to quoting because the validator strips punctuation, but do not quote across it.
- **Non-UTF8 title bytes.** Three titles carry a replacement character where a curly apostrophe
  was (`UFejYNnDCuA`, `WLFThXBRk0I`) — in the transcript header line only, not the body.

No quote in this unit spans an artifact boundary or was retyped from memory; all were extracted as
literal substrings and machine-checked against the transcript before the draft was written.

---

## Explicit list — Shorts that contained nothing new

**Contributed nothing at all, uncited (1):**

- `wpQWLgZqS88` — *Using Equilibrium to Invalidate Daily Bias.* A reversal off a previous day low
  targets the EQ; closing over and disrespecting the EQ opens the swing high. Both directions of
  this are already detection rules on `equilibrium-eq` ("Disrespecting the EQ is read as the swing
  point being likely to fail…"). Nothing to add, so nothing was written.

**Cited only as corroboration — an extra evidence line on a rule the library already held, adding
no detection rule (28):**

`25V-sGyMj_M`, `nNfhTDkyhtw`, `Oio_QeRPVQQ`, `iwGyMV0BDSY`, `Uzl3zYzr90Y`, `_VquvUgdQmA`,
`0st2qhpQ5QE`, `p1xrHuEHpQY`, `HVPIhbOxnls`, `WC6yqIli3iU`, `82M87plzCho`, `yVgn2rBhysQ`,
`vBAYmH7XCks`, `1eL9Edk1FrI`, `Hi8faa5u2uw`, `jo2D1AOuxHM`, `0fhZ_jpespw`, `OFfjyo4-s6U`,
`La4MlftJc14`, `GxJP4JWuX54`, `_w0AXMw04Sk`, `UFejYNnDCuA`, `KGw0lLST3pU`, `ZEK8fDzxClA`,
`28_luJwwVbw`, `WLFThXBRk0I`, `OuyHuNe-IP0`, `oBkh-__IL-I`.

Of these, the ones closest to the line — where the clip is a good teaching artefact but genuinely
adds no rule — are `0fhZ_jpespw` (28 seconds asserting that swing validation is fractal, which the
library already encodes as `fractal: true`), `yVgn2rBhysQ` / `82M87plzCho` / `WC6yqIli3iU` (three
projection walk-throughs of rules already in `standard-deviation-projection`, including the
large-leg → −1 branch and its "judged by eye" caveat), and `Hi8faa5u2uw` (a full T-spot entry
replay whose only novel line is the T-spot's stated purpose).

**Contributed at least one rule, count, definition or mechanism the library lacked (20):**

`MtczT00fhJI`, `VtFC9SCnlYM`, `B1tTNDOtFaw`, `gLul2OZQe9Q`, `I8_O-4ZifrM`, `L9Gd5p14uBE`,
`RdQdorNCezI`, `T1F4aT_7ppg`, `OjSyhPw1WIw`, `yMUyTAmD1NE`, `8FtjVWZcZN8`, `2ctrcNs4tFo`,
`yku6idnLqSo`, `7v9Y2GHNqCg`, `46VIOAlxmEE`, `yZVevl-tMHA`, `U1NJUh1RqMw`, `Nbs0gsth2jw`,
`__E1fj1n4xg`, `eKbZYMn3_bU`.

---

## Drafts produced (29, all reusing existing ids)

`ideal-formation`, `fractal-model-c2`, `fractal-model-c3`, `indicator-print-conditions`,
`continuation-timing`, `continuation-over-reversal`, `continuation-order-block`,
`high-vs-low-resistance-liquidity`, `small-wick-expansion-rule`, `half-wick-respect`,
`htf-wick-formation`, `expansion-sequence-quality`, `expansion-signature`, `retracement-phase`,
`standard-deviation-projection`, `stop-loss-placement`, `ltf-inversion-entry-in-tspot`, `t-spot`,
`breaker-continuation`, `relevant-htf-pd-array-test`, `relevant-swing-separation`,
`relative-strength-asset-selection`, `eurgbp-relative-strength-cross`, `thursday-counter-week`,
`single-pd-array-mastery`, `v-shape-reversal-speed`, `upper-half-eq-expansion-filter`,
`positional-entry`, `expansion-exhaustion-avoid-price`.
