# Build A Model — Intro to TTrades Fractal Model (TTFM), part 2 — study notes
`unit_id: build_a_model_intro_to_ttrades_fractal_model_02`

Channel: TTrades_edu. Playlist: "Build A Model - Intro to TTrades Fractal Model (TTFM)".
20 videos, all transcripts present and readable. Every video in this unit is also
cross-listed under "Education - ICT (Updated)"; `8BWkRGhuj1k` is additionally the
closing video of the "Phases Of Price Series".

**This is the primary teaching.** Everything the library previously recorded about
`fractal-model-c2/c3/c4`, `cisd`, `point-of-interest` and `phases-of-price` was
assembled from secondhand mentions inside Q&A streams and chart-lesson walkthroughs.
This playlist is the speaker's own dedicated, PDF-backed construction of the model,
one video per component. Where it disagrees with a Q&A stream, this is authoritative.
The disagreements are called out explicitly below.

## Transcript hygiene

- **`candle 2` → `candle to`.** The known corpus-wide artifact. In this unit the
  numeral is mostly transcribed correctly, but it appears as "candle to closure" in
  `m4k_1pF5zFI`, `TNybDCtwBnc` and `HrjYoxAUb3s` and is read as *candle 2 closure*
  throughout. Quotes are copied with the artifact intact where it falls inside them.
- **`reach` → `wretch`.** Systematic in `vn1RYjhJUnQ`, `IJcfC6wAPZU` and
  `NqSbvqDKML0` ("closing through the series of candles that wretch into that
  important level", "we have wretched into an important level"). Read as *reach*
  everywhere. The load-bearing CISD quote carries this misspelling verbatim and it has
  **not** been corrected inside the quote.
- **`5fnFOh5YuM0` (Candle 4) and `IJcfC6wAPZU` (Continuations) have no punctuation
  at all** — both are single run-on lowercase blocks from a different caption pass
  (`auto-en` rather than `yt-dlp-auto`). Sentence boundaries in the summaries below
  are mine; quotes are still exact substrings.
- **`dogee` = doji**, `Vshape` = V-shape, `RTP` = "our TP" (take profit), `TP`/`R`
  used normally. `GXT` appears once in `FAKWJ-1NlLE` and is expanded there by the
  speaker himself as "Garrett's 4-hour profiling with my fractal model".
- **No transcript in this unit carries timestamps.** Therefore **no `approx_time` is
  recorded anywhere in this unit's concept files.**

---

## TTrades Fractal Model - Trading Candle 2 (`m4k_1pF5zFI`, 1110s)

### What is actually taught

The dedicated candle 2 lesson, and it is really a lesson about *wick size*. He opens
with the classification the whole model rests on: an **expansion candle** has a small
wick each side and a large body, meaning price trended one way for the period; a
**reversal candle** opens, makes a large opposing run to form its wick, then returns
toward its opening price before closing. The argument for why this matters is a range
budget, not a shape preference — he is not willing to expect price to travel down to
form a large lower wick and then expand far beyond, because that is "too much time and
too much range". Small wick supports expansion; large wick does not.

The consequence is the trade/no-trade decision for candle 2 itself. A **reversal-to-
expansion candle** (small wick) is the one he wants: it can be traded inside candle 2
and it can target previous candles' extremes and standard deviation projections. A
large-wick reversal candle is *still tradeable* — he is explicit that it is not
forbidden — but **the targets must be swapped**: back toward the daily open (or the
higher-timeframe open when used fractally), the session lows, and the current candle's
low. This target-side rule is the sharpest thing in the video and is captured as its own
concept because the library did not have it in TTrades' own voice.

The procedure for actually taking a candle 2 is stated compactly: mark the previous
candle's high on the higher timeframe, wait for a sweep of that high, then a change in
the state of delivery forming a protected high, so the wick can be treated as formed;
then trade the reversal, or the continuation that follows. A separate and genuinely
useful passage gives the **session-dependent confirmation timeframe**: in Asia he will
use almost only the hourly or 30-minute; in London the hourly, 30-minute or 15-minute;
in New York he will take those if they appear, but notes a New York reversal is usually
very quick and waiting for hourly confirmation often means the target is already hit —
so he drops lower. He then applies his own rule against himself: on one oil/gasoline
example, the hourly CISD would land *at* the target, so the trade has no room.

The GBP example is the honest one. He takes the setup, gets stopped out, and then shows
that euro was the weaker asset (a shallower wick, no reach for its previous day high)
with an SMT at the extreme — the same framing on the correlated asset would have worked.

### Rules / conditions stated

- Expansion candle = small wick each side + large body. Reversal candle = opens, large
  opposing run, returns toward the opening price, closes.
- Small wick supports expansion; a large opposing run does not.
- Small-wick candle 2 → tradeable inside candle 2 (after the LTF CISD).
- Large-wick candle 2 → do not expect expansion; adjust targets to the daily open,
  session lows, current candle low. Or let the reversal day trade and check whether the
  *following* day has a small wick.
- Disqualifier on a large-wick day: if the overnight session highs/lows are already
  taken, there is no low-resistance liquidity left and the R is not there.
- Entry sequence: mark previous candle's extreme → wait for the sweep → require a CISD
  → protected swing → trade away.
- Only swing points are traded ("with my fractal model, I'm only looking to trade swing
  points"); after two swing lows with no new one, only downside is favoured.
- Confirmation timeframe by session: Asia = 1H/30m; London = 1H/30m/15m; New York =
  those if present, otherwise lower.
- In a range, wait for one side to be engaged before looking for anything.

### Concepts introduced

Expansion vs reversal candle; small/large wick; target adjustment on a large wick;
the sweep→CISD→protected-swing sequence; session-dependent confirmation timeframe;
failure swings and non-overlapping HTF candles as a range test; EQ of the previous day
as a target; correlated-asset re-framing after a stop-out.

### Open questions

- **No numeric threshold for "small" vs "large" wick anywhere.** The single most
  load-bearing classification in the model is entirely visual. This is the unit's
  biggest automation blocker.
- "Session lows" is used without naming the sessions here.
- Which daily open (18:00 / midnight / 09:30) is meant is never said.

---

## TTrades Fractal Model - Trading Candle 3 (`qdQYhePcvGE`, 2139s)

The longest video in the unit, dedicated entirely to candle 3.

### What is actually taught

**It does supply the missing direction input, but not in the form the library was
looking for.** This video never states a candle 3 *closure* test in price terms at all.
Instead it defines candle 3 relationally: candle 3 is the continuation traded away from
a **confirmed candle 2 reversal**, and the direction is inherited from that candle 2 —
"from this high, do I have a change in the state of delivery? I do. So, now this
confirms the reversal or that candle 2 has reversed. So then I can look for a
continuation in candle 3." The trend direction is therefore an *external input* after
all, supplied by (a) which side of candle 1 the candle 2 swept, and (b) the LTF CISD
that confirms it. That is decidable, and it is not degenerate.

The video adds two hard gates that the library did not have:

1. **Candle 2 must be a reversal candle, not an expansion candle.** "We're not really
   going to want to focus on trading candle 3 when we have a candle 2 expansion because
   that is when we can get caught in a new phase of price." A candle 2 that already
   expanded is a disqualifier.
2. **Exception to gate 1: drawn liquidity.** "If candle 2 would have expanded all the
   way to this low, that's something I'm not ever really going to trade. But with this
   drawn liquidity still open, this is where I can still look to trade that continuation
   in candle three because I have a spot for it to reach for." So the real test is not
   *did candle 2 expand* but *is there still a target left*.

The rest of the video is a long tour of the bias/confirmation trade-off, stated
explicitly and repeatedly: with a strong higher-timeframe bias he will take a **lower-
timeframe reversal** entry; with a weak one (candle 2 already expanded, or he is trading
a higher-timeframe candle 2 rather than a candle 3) he **demands a lower-timeframe
continuation**, sometimes plus SMT and a V-shape. His stated default is "a higher time
frame continuation with a lower time frame continuation", and his stated preference is
candle 3 over candle 4 because later continuations feel like chasing.

One genuinely new mechanical correction lands here on the half-wick question. On a
small-wick candle he **refuses** 0.5 of the wick and uses **0.5 of the whole candle's
range** instead, because a retracement to the midpoint of a small wick is not a shallow
move relative to that candle. This resolves what looked like an inconsistency across
the corpus into a clean rule keyed on wick size.

He also gives a clear no-trade heuristic: when the CISD level and the target sit at
almost the same price, "by the time we get our change in the state of delivery, we're
taking out targets" — skip it. And a timing heuristic for reversal quality: if the close
below takes a long time, read it as consolidation, not a reversal.

### Rules / conditions stated

- Trade candle 3 following **reversal** candles; a candle 2 that expanded disqualifies,
  unless short-term drawn liquidity is still intact.
- Confirm candle 2's reversal with the LTF CISD before looking for candle 3.
- Inside candle 3: let the wick form, trade the body, via a continuation order block.
- Strong HTF bias → LTF reversal entry permitted. Weak HTF bias → demand LTF
  continuation (+ SMT / V-shape).
- On a small-wick candle use 0.5 of the candle's **range**, not 0.5 of the wick.
- Skip the entry when the CISD level coincides with the target.
- If candle 3 does not expand, expect the candle 4 continuation instead.
- Closing frame: "candle 2, the reversal candle, candle 3, the continuation, or it can
  be a reversal candle, and candle 4, which is always a continuation within my model."

### Open questions

- **No price-level definition of a candle 3 closure appears in the candle 3 video.**
  That definition comes from `vn1RYjhJUnQ` and `SF61vCsBl1A` (below).
- "Candle 3 can be a reversal candle" is said once and never operationalised.
- The strong/weak bias classification that gates aggression is entirely discretionary
  and he says so.

---

## TTrades Fractal Model - Trading Candle 4 (`5fnFOh5YuM0`, 1030s)

### What is actually taught

Candle 4 has the cleanest preconditions of the three and the only genuinely numeric
filter in the sequence. It opens by restating the model's axiom — the market cannot
reverse without a swing high or a swing low — and then requires a **completed
three-candle swing point**: a low with a higher low on each side (bullish), a high with
a lower high on each side (bearish). If the far-side candle has not printed, that is a
candle 3 trade, not a candle 4 trade, and he waits a day. Given a confirmed swing plus a
strong candle 3 closure, he anticipates candle 4 expansion.

The filter: **the candle 4 wick must form in the upper half of candle 3's range** for a
bullish continuation, the lower half for a bearish one, "due to expansions not giving
those deep retracements". This is the one place in the unit where a specific level is
attached to a specific candle with a stated reason. He then works inside that half —
find a point of interest there, drop to the entry timeframe, and pair the entry with a
session driver (08:30 or 09:30 is named).

Two substitutions appear. A **daily** change in the state of delivery on the daily chart
itself can validate the swing without dropping down; and an **SMT** with ES means "I
don't need this low to get taken out anymore". He also demonstrates his own phases-of-
price reasoning live: expansion into a counter-move, is it met with expansion (reversal)
or is it a retracement/consolidation — and he refuses to call the low until the answer
is in.

The last example is a loss that he keeps: he places the stop above a fair value gap
specifically because price can reach back up and still respect 0.5 of the HTF candle,
and price does exactly that before continuing.

### Rules / conditions stated

- Precondition: a confirmed three-candle swing point (low with higher low each side).
- Plus a strong candle 3 closure in the swing direction.
- Candle 4's wick must form in the upper (bullish) / lower (bearish) half of candle 3's
  range.
- Find the PD array inside that half; enter on the LTF closure through the series that
  made the extreme.
- Pair the entry with a driver (08:30 / 09:30) where possible.
- A daily CISD, or SMT with a correlated asset, substitutes for the sweep.
- Expansion phases do not give deep retracements — a deep retracement means reversal.
- "Everything comes down to the daily chart; if I can frame a direction on the daily
  chart the lower time frames fall into line."

### Open questions

- "Strong closure" in candle 3 — the gate — is unquantified.
- The half is measured against candle 3's **range** here, but the same video also says
  "the upper half of this from body to body" in an example. No tie-break.
- No upper bound on continuations; candle 5 is named once in `9AL41xON3hA` with no
  definition.

---

## TTrades Playbook | Fractal Model Fundamentals (`TNybDCtwBnc`, 1194s)

### What is actually taught

The single highest-value video in the unit for automation, because it is a **written,
ordered, numbered checklist** (published as a TradeZella playbook) rather than a
narrative. It also supplies the two things the library most needed.

**First, the numbering is fixed and stated categorically:** "Candle 2 will always be the
swing low or swing high. Candle three will be the candle following candle 2. Candle four
following candle three and candle one will always be the candle before candle 2. So 1 2
3 forming a swing low and candle 4 is always a continuation if that trend is correct."

**Second, the daily bias rule is given mechanically and as a hard gate:** "I'm going to
use daily closures. So using this as the daily chart, if price closes below its previous
day low, I'm expecting a continuation lower. If price fails to close below its previous
day low, I'm expecting a reversal and for price to be bullish. And the same goes for
previous day high just opposite." And the gate: "If I do not have a daily bias I do not
drop down to the hourly time frame."

The checklist, in his order: (1) daily chart, one-sided bias from daily closures — no
bias, no hourly; (2) hourly, confirm a CISD inside the candle 2 reversal; (3) hourly, is
there a point of interest, located in the upper/lower half of the previous day's range;
(4) hourly, is there a candle closure at that point of interest; (5) entry timeframe
(5-minute), require a CISD there — "that's part of my checklist"; (6) enter, stop on a
protected swing, minimum 2R.

The CISD procedure is spelled out identically every time: find the extreme, find the
series of down-close (or up-close) candles that made it, wait for the close through.

Two numbers worth recording. He states his system requirement is **a minimum of 2R,
"because that allows me to understand that with a win rate over 34%, I'm going to be
break even or profitable"** — the first time the corpus attaches arithmetic to the 2R
rule. And the demonstrated sample was 5 trades, 80% win rate, 2.79R, which he himself
immediately discounts as too small.

He also gives the standing trick for larger R: "the best way to get high risk-to-reward
trades is to take a lower time frame entry and just use a higher time frame target" —
5.63R instead of 2R on the same setup.

The first sample trade is a **loss**, kept in, with the post-mortem: the point of
interest was not respected, short-term lows were taken before entry, and the expansion
candle opened in the wrong direction first.

### Rules / conditions stated

The six checklist steps above, plus: candle 1/2/3/4 labelling; the daily closure bias
rule; entries expected in the upper/lower half of the previous day's range at a point of
interest; the negative-one standard deviation from the manipulation leg as a target;
2R minimum; the 34% break-even figure; do not want price above 50% of the opposing
candles.

### Open questions

- "Closes below its previous day low" — wick low or body low is not specified.
- No rule ranks candidate points of interest when several sit in the half-range.
- A day that closes *inside* the previous day's range without sweeping it fits neither
  branch; by elimination it gives no bias, but this is never stated.

---

## Validating Swing Points Using Lower Timeframe Confirmation (CISD) (`vn1RYjhJUnQ`, 626s)

### What is actually taught

The dedicated CISD video, and the adjudicator for the library's three-way CISD split.
It gives **one** definition, in two parts, and repeats it a dozen times operationally:

> "What defines a change in the state of delivery is price reaching into an important
> level sweeping out a low or reaching into a fair value gap and then closing through
> the series of candles that wretch into that important level."

Plus the ontology: "The change in the state of delivery is the order block formation
that forms when trend changes." So: (a) reach an important level — a sweep of a low/high
**or** a tag of a fair value gap; (b) close through the series of same-direction candles
that reached into it. The procedure recited at every example is *find the high → find
the series of candles that made that high → have we closed below it?*

Scope is equally clear and is stated as a two-way lock. A closure without a CISD is not
a valid fractal model and he waits or ignores it. A CISD without a higher-timeframe
closure "does not mean anything to me unless it is paired with a higher time frame
candle closure". Both halves are required.

**This video also carries the candle 3 closure definition the candle 3 video omits:**

> "We have a candle 3 closure because we don't have a candle 2 and then candle 3 closes
> below the opening price in candle 2."

and its negation:

> "This is not a valid candle 3 closure because price never closes below the opening
> price in candle 2."

So a candle 3 closure (a) exists only when candle 2 failed to close, and (b) is measured
against **candle 2's opening price**. Not the EQ. That is one-sided and decidable.

He also gives a quality test that doubles as the consolidation detector: "not all lower
time frame structure is the same. Just because it does have a closure over, doesn't mean
it's a good closure over. If it consolidates for half of the candle and then closes over,
it's usually just a consolidation." And the named failure mode when no CISD forms:
"usually when we fail to form a change in the state of delivery, we're going to
consolidate, form a consolidation, and then take out one side of the range and trade to
the other."

He demonstrates the value negatively — a candle 2 closure with no CISD, which then takes
out the high: "by waiting for the closure through... I saved myself from taking losses
that look like this."

### Rules / conditions stated

- CISD = reach an important level (sweep a low/high **or** tag a fair value gap) **then**
  close through the series of candles that reached into it.
- Required inside a candle 2 **or** candle 3 closure on the timeframe above. Neither half
  alone counts.
- Candle 3 closure = candle 2 produced no closure **and** candle 3 closes beyond candle
  2's opening price.
- Fractal: demonstrated monthly→daily, daily→5m, and on intraday pairs.
- Quality: want a fast V-shape; half-a-candle to close over = consolidation.
- No CISD → expect consolidation, then a sweep of one side and a move to the other.

### Open questions

- "Series of candles" is unbounded; elsewhere he says he will ignore small candles and
  take the whole leg.
- "Close through that level" vs "close through the opening price of the series" are used
  interchangeably within the video.

---

## TTrades Ideal Formation - High Probability Swing Points (`SF61vCsBl1A`, 867s)

### What is actually taught

A genuinely new concept, and a correction aimed at a specific widespread error. An
**ideal formation** is a candle 2 **or** candle 3 closure that *simultaneously* creates a
protected swing — the same bar that sweeps candle 1 and closes back inside also closes
through the series of opposing candles that reached the point of interest. "It is a
candle closure paired with a protected swing."

He states the error he is correcting outright: "A lot of people think because it closes
over the body of candle one, that it is an ideal candle two closure." It is not. The
test is the close through the opposing-candle series, not the close over candle 1's body.

The payoff is that the next candle is immediately tradeable, and two levels come with it
to mark: **the opening price of the series of opposing candles**, and **the EQ of the
closure candle**. The next candle's wick should form in that band and should be shallow.

Several shapes are enumerated, and the useful one is the **late** ideal formation: a
candle 2 closure that is *not* ideal, followed by a candle 3 that does close through the
series — which makes it ideal for trading **candle 4**. So the formation can complete one
candle late, and the tradeable candle shifts accordingly.

This video also independently states the candle 3 closure test, in a second wording:
"we have a candle three closure because candle three is closing below the body of candle
two". Body, not EQ — consistent with `vn1RYjhJUnQ`'s "opening price" whenever candle 2
closed in the sweep direction.

He closes with the anti-pattern-trading caveat: an ideal formation still needs a point of
interest and cannot be traded on shape alone.

### Rules / conditions stated

- Ideal formation = candle 2 or candle 3 closure that also closes through the series of
  opposing candles that made the extreme, in the same bar.
- Closing over candle 1's body is **not** sufficient.
- Mark the opposing-candle series' opening price and the EQ of the closure candle; the
  next candle's wick should form there, shallowly.
- A late ideal formation (non-ideal C2, then C3 closes through) makes **candle 4** the
  tradeable candle.
- Still requires a point of interest. Not pattern-tradeable.

### Open questions

- Whether the close must be a body close through the series (all examples are).
- "Shallow wick" in the following candle is unquantified.

---

## Using PSP to Confirm Swing Points (TTFM) (`ZAEgtvsD-qQ`, 481s)

### What is actually taught

Short and unusually precise. **PSP is a divergence in the close colour of the same-period
candle across correlated assets** — the structure matches (both swept, both closed back
in) but one closes a different colour. He explicitly frames it as a smaller sibling of
SMT: SMT is a divergence in whether the level was taken, PSP is a divergence in the
closure.

Two named types, keyed on **where in the model the divergent candle sits**: a **candle
one PSP** (the candle before the swing point closes a different colour) and a **candle
two PSP** (the swing candle itself closes a different colour). Both can be combined with
SMT on the same structure.

The scope statement is the important part and he repeats it three times: "I'm only going
to look for a PSP within a valid fractal model... I'm not trying to use these concepts
alone to frame a trade... I'm not going to randomly look for PSP unless it is in an
existing model." PSP is confluence for an existing candle 2/candle 3 closure with its
CISD — never a trigger. Demonstrated on NQ vs ES and YM, and fractally down to monthly
vs daily.

### Rules / conditions stated

- Correlated markets should have the same structure; PSP is a difference in the closure
  colour on the same-period candle.
- Candle 1 PSP: candle 1 diverges. Candle 2 PSP: the swing candle diverges.
- Only look for PSP inside an already-valid fractal model (closure + CISD).
- May be stacked with SMT.
- For Nasdaq the correlated set is ES and YM ("I use all three personally").

### Open questions

- No ranking between candle 1 PSP and candle 2 PSP; nothing on both together.
- Nothing on what a *counter*-directional PSP means.

---

## The Only Points of Interest That Actually Matter (`NqSbvqDKML0`, 1220s)

### What is actually taught

**The live-stream claim that POI is a closed list is essentially confirmed, but with
three members, not two, and with a strict priority order.** He states it in the opening:
"I'm going to talk about the only three points of interest that I use... I use fair value
gaps, I use swing highs and lows, and then I also use a change in the state of delivery
level or an order block."

So the live-stream "all I know are highs, lows, and fair value" is correct about the
first two and their primacy, but omits a conditional third. The CISD level is explicitly
a last resort — "a CISD level is a point of interest that I rarely use" — admitted only
when neither a fair value gap nor a swing high/low exists in the range.

The search **domain** is as important as the list and was not previously recorded: measure
from the **point of reversal** (the protected swing being traded away from) to the far
edge of the range price has since created, and look only inside that. Then apply the
order: fair value gap first, swing high/low second, CISD level only if neither.

When the CISD level is used, an extra requirement attaches: **50% of the bodies** of that
opposing-candle series must hold, with no closures beyond it.

Two refinements. (1) When both a fair value gap and a swing point exist, he wants **both**
tagged before trading away — "I don't really want to trade a sweep of a low right here if
we have a fair value gap resting just under it. That's when price comes back, takes out my
stop loss, and then goes higher." (2) A candidate opposing candle that never reaches a
point of interest is rejected as a protected swing however clean it looks — he refuses
several "propulsion blocks" on exactly this basis. Where several fair value gaps stack, the
shallow-retracement principle picks the nearer one.

He does allow one discretionary override: a CISD retest that does not tag the level exactly
can still count "when I have the context".

### Rules / conditions stated

- Exactly three POIs: fair value gap, swing high/low, CISD level.
- Priority: FVG → swing high/low → CISD level (only if neither).
- Search range = point of reversal → the extreme price has since made.
- CISD level use additionally requires 50% of the bodies to hold.
- If both an FVG and a swing exist, require both tagged.
- No POI reached = not a protected swing, regardless of the closure.
- In a consolidation, repeat the process at the range edges.

### Open questions

- The "when I have the context" override is undefined.
- Stacked fair value gaps are disambiguated only by "we don't want a deep retracement".

---

## The Phases of Price Action: A Blueprint for Market Movement (`8BWkRGhuj1k`, 1685s)

### What is actually taught

The closing video of the phases series, and it supplies **a mechanical test for
consolidation** — the concept that currently blocks 23 others.

The flowchart first. It **always starts at expansion** and always returns there. Legal
transitions: expansion → retracement → expansion in the same direction (continuation);
expansion → consolidation → either a breakout (expansion same direction) or a
manipulation (expansion opposite, which when met with expansion back is a reversal);
expansion met with expansion = reversal, which forms a higher-timeframe wick and is
followed by a continuation. After any phase resolves, return to expansion.

**The consolidation test**, stated in passing inside an example rather than as a named
rule: "Is this a retracement? Yes. But does it form a protected swing? No. That means
it's then a consolidation." So a counter-move is a *retracement* only if it forms a
protected swing (reaches an important level, then closes through the opposing-candle
series); otherwise it is a *consolidation*. Three corroborating signatures are given
across the video: price remaining inside one prior candle's range ("we are stuck inside
this candle's range here"); an inside bar ("this next day stays inside bar. So, now this
is a consolidation"); and repeated failure to close over the level, with the timing
version from `vn1RYjhJUnQ` (half a candle) agreeing. The practical consequence is a mode
switch — with a retracement he waits for the continuation; with a consolidation he stops
waiting and demands a sweep of one side of the range.

The second theme is that **the phases alone do not give direction** — they must be blended
with the daily bias, because the phase says a consolidation will resolve but not which
side. He demonstrates the cost of ignoring this: a textbook reversal (high taken, CISD,
short-term high taken) that he refuses because the daily closure had not aligned, and he
shows the move it saved him from. Later he takes a day he is wrong on, and uses the daily
closure and the phases to realign rather than to predict.

Notably he also documents moves his system **cannot** catch: a grind higher that never
sweeps a low, so no protected swing forms. "This is something that my system prevents me
from catching, but that's fine cuz I can catch these clean, easy continuation moves."

### Rules / conditions stated

- Always start at expansion; four phases; the transition set above.
- Retracement iff a protected swing forms; otherwise consolidation.
- Inside bar / stuck inside one candle's range = consolidation.
- Expansion met with expansion = reversal = a higher-timeframe wick.
- Blend with the daily bias; the bias picks the branch out of a consolidation.
- Do not switch bias intraday because of one leg — wait for the daily closure.
- If the next phase is not decidable, let more candles print.
- Minimum 2R; targets extended to previous day lows where the daily supports it.

### Open questions

- "Expansion" itself has no size threshold — the flowchart is anchored on an undefined
  primitive.
- Slow/shallow (retracement) vs fast (reversal) is visual; only the protected-swing test
  is mechanical.
- `eywpZT3z6GQ` calls a consolidation a continuation signature outright, while the
  flowchart makes it a two-way branch. The reconciliation (the bias resolves it) is only
  stated here.

---

## The Best Timeframe for TTrades Fractal Model (`FgP2lc9nneM`, 1008s)

### What is actually taught

He names his favourite pairing outright: **daily for bias, 4-hour for the swing point and
the daily profile, 15-minute for entry.** The logic is recursive — let the daily wick form
and trade its body, then do the same thing one level down, so you are trading candle 3 on
the daily and candle 3 on the 4-hour simultaneously. "The easiest expansions occur when
you trade candle 3 on multiple different time frames."

**On the 4-hour grid, this confirms the resolved reading for futures.** After a 2:00
(London) candle 2 closure he says "we can anticipate 6 a.m. and 10:00 a.m. to expand
higher" — the 02/06/10 sequence, i.e. the 18/22/02/06/10/14 New York grid. Two
conditions attach: **"10 a.m. is dependent on 6 a.m. with a strong closure"**, and
"we'd only look to trade this third expansion candle if the drawn liquidity has yet to
be met". Nothing in this video contradicts the 10:00 multi-timeframe-open finding; it
simply does not address it.

The daily bias entry point is loosened slightly: "this doesn't have to be a candle to
closure, but this is specifically the easiest way to get that daily bias", with the POI
list restated as a low, a high, or a fair value gap.

He states his preference for continuation over reversal with the clearest reasoning in
the unit: "I would rather just wait for it to react or not react and save myself a loss
than to place a limit."

The third example is the advanced one and worth noting for its failure handling: a valid
positional entry gets stopped, the in-candle CISD never forms before the low is taken,
and he explicitly does **not** change the idea — "we're still bullish as we're respecting
the same area. We want to see if we can get a new candle to closure." He also flags a
recurring structure: after a target is taken, price often comes back and runs a low that
made the high before continuing.

Closes with a promotion for a paid mentorship ("the lens path") run with AM Trades.

### Rules / conditions stated

- Daily bias (ideally a candle 2 closure at a low/high/FVG) → 4-hour candle 2 or candle 3
  closure → 15-minute CISD → continuation entry.
- After a 02:00 candle 2 closure, anticipate 06:00 and then 10:00; 10:00 is conditional
  on a strong 06:00 close.
- Only trade the third expansion candle if the drawn liquidity is unmet.
- Respect the lower/upper half of the 4-hour candle by direction.
- Do not place limits into the level; wait for the reaction.
- Lower-timeframe invalidation + higher-timeframe target = 4R and 8R examples.

### Open questions

- "Strong closure" gating 10:00 is unquantified.
- The session times quoted are the futures grid; this video does not flag that forex
  differs (see `FAKWJ-1NlLE`).

---

## Trading The 4 Hour Power Of Three - OHLC / OLHC (`FAKWJ-1NlLE`, 1276s)

### What is actually taught

He opens by **rejecting the classic AMD diagram as unusable** — "this looks a bit
confusing and it's not very mechanical" — and redefines power-of-three onto the candle
numbering: **candle 1 is always accumulation; candle 2 is manipulation; candle 3 is
distribution.** One branch, keyed on wick size. If candle 2 has a large opposing run it is
manipulation only and distribution happens in candle 3, a separate higher-timeframe
candle. If candle 2 has a small shallow opposing run, "manipulation and the distribution
happens in the same higher time frame candle". The instruction he asks the viewer to
internalise: "I need to let the wick form and then look to trade the body. If you always
try to catch the wick, you're going to get continuously stopped out."

**The 4-hour grid finding.** The futures examples run on 02:00 / 06:00 / 10:00 / 14:00
(with 22:00 referenced), i.e. the 18/22/02/06/10/14 New York grid — **confirming the
library's resolved reading**. But the forex example is explicitly different: he introduces
it with "you can see how those timings are a bit different from futures" and then works
1700, 2100, a 01:00 candle and a 09:00 candle — implying a **17/21/01/05/09/13 grid for
forex, offset one hour from the futures grid.** This is a real, deliberate distinction the
library did not have, and it is not a transcript artifact — he flags it verbally.

The final examples are where the 10:00 alignment claim gets indirect support: "6 a.m.
reversal, 10:00 a.m. continuation aligning that with a fractal model on the lower time
frame", with the 4-hour and hourly both showing shallow wicks at 10:00. He also does not
fight an expansion candle: "does it make sense to fight this expansion candle? No. It
makes more sense to wait for this expansion candle to close, which would be at 1,400 and
then look for a reversal candle."

`GXT` is expanded here by the speaker: "what people refer to as GXT, which is using
Garrett's 4hour profiling with my fractal model."

### Rules / conditions stated

- C1 = accumulation always; C2 = manipulation; C3 = distribution.
- Large opposing run in C2 → distribution in C3. Small shallow run → both in C2.
- Confirm the distribution candle's wick with an LTF protected swing / CISD.
- Let the wick form; trade the body; never chase the wick.
- Futures 4-hour opens: 02/06/10/14 NY. Forex 4-hour opens: 17/21/01/09 NY.
- A shallow opposing run should appear **early** in the higher-timeframe candle; "when
  price goes up first, that usually means it's going to come down".
- Do not hold beyond the expansion candle's close; wait for the new candle for a new
  continuation.
- Do not fight an expansion candle; wait for its close and a reversal candle.

### Open questions

- No reason is given for the one-hour offset between the forex and futures grids.
- The timezone is never named in this video (New York assumed from the corpus).
- The large/small opposing-run branch is again unquantified.

---

## TTrades Scalping Model (`eywpZT3z6GQ`, 884s)

### What is actually taught

A complete named strategy. The higher-timeframe anchor stays the daily, but the operative
bias candle is the **hourly**: an hourly candle 2 or candle 3 closure lets him anticipate
an hourly expansion candle. He then finds the **15-minute** swing point that forms that
hourly candle's wick, requires a 15-minute candle 2 closure with its CISD, and uses a
**15-minute / 1-minute** fractal model to time the entry. The stated object: "we are
trading the body of the hourly candle using a 15-minute and 1 minute fractal model."

The clearest statement of his consolidation stance sits here: "a consolidation is a
continuation signature to me. So, I'd be more interested in a sweep of the low to go
higher versus a sweep of a high to go lower."

He is disciplined about skipping. When price does not tag the entry point of interest
before leaving, "this is something that I would miss here. And could I trade it below the
lows? Sure. But it's just not something I prefer to do." He is also candid about entry
quality — he shows what the A+ entry would have looked like versus what he got.

The final example is flagged as advanced and he tells most viewers to ignore it: trading
the hourly **reversal** candle rather than the continuation, "which is more advanced. It's
harder to trade but everything is aligned."

### Rules / conditions stated

- Hourly candle 2 / candle 3 closure with internal (FVG) and external liquidity → expect
  an hourly expansion candle.
- 15-minute swing point that forms the hourly wick, with a candle 2 closure.
- 15m/1m fractal model for the entry; let the wick form, trade the body.
- Consolidation = continuation signature; prefer the sweep that agrees with bias.
- Skip when the POI is not tagged before price leaves.
- Positional entry allowed at the new hourly open when a protected swing already exists
  before the open and sits below the EQ.
- 2R, or the other side of the consolidation.

### Open questions

- The advanced reversal variant is named but its extra conditions are not given.
- How the daily context interacts with the hourly bias (veto or confluence) is unstated.

---

## TTrades Swing Trading Model (`9BY-MQRNy-Y`, 1081s)

### What is actually taught

The other complete named strategy. **Step one is always a weekly bias** — will the week
reach for the previous week's high or low — built from liquidity, highs/lows, fair value
gaps and candle closures. Step two is a **daily** candle 2 or candle 3 closure that forms
the daily wick, checked for its CISD; no daily swing point means no trade, stated plainly
("do I have a swing point on the daily to trade away from? No, I do not. Right. So, I'm
not going to be able to take a trade here"). Step three is an **hourly** entry, held
through Wednesday and Thursday into the weekly draw.

He gives the fractal variants explicitly: monthly / weekly / 4-hour for higher-timeframe
swing trading, and a shortcut of weekly straight to a 4-hour fractal model with no
intermediate daily alignment.

Two things worth extracting. First, a **messiness override**: "You don't have to use this
defined time frame alignment. If things are a bit messy, you can move up one time frame."
He demonstrates moving hourly → 4-hour, and 30-minute → hourly. Second, honest loss
accounting — a first entry wins 3.74R, a second identical-looking entry stops out, and he
keeps both: "It has the context, it has the bias, and it has the structure. It just comes
and stops us back out."

He also gives an expansion-integrity rule for swing holds: if price retraces all the way
back into the fair value gap below the reference range, "this is when price becomes
bearish, and it might as well just take out this low" — so he wants price held in the
upper half.

Closes by pushing the choice of timeframes onto the trader: "you have to figure out what
type of trader you are... no one else is going to be able to tell you that."

### Rules / conditions stated

- Weekly bias from liquidity / highs-lows / FVGs / closures; a weekly C2 closure implies
  expansion in weekly candle 3.
- Daily candle 2 or candle 3 closure + CISD; no daily swing point = no trade.
- Hourly entry; hold through following days to the weekly draw.
- Keep price in the upper half (bullish) of the reference range during the expansion.
- If a timeframe is messy, move up one.
- Variants: monthly/weekly/4H; weekly straight to 4H.
- 2R minimum; examples at 3R and 3.74R.

### Open questions

- Four bias ingredients with no priority or tie-break.
- "A bit messy" is purely visual.
- Whether the weekly→4H shortcut carries the same expectancy is not addressed.

---

## Stop Overcomplicating Trading (`q3nauvjT3q0`, 824s)

### What is actually taught

The deliberately reduced model: **drop candle 2 and candle 4, trade only candle 3, but on
several timeframes at once.** "We are only going to focus on trading candle three on all
time frames."

It carries one asymmetry that is easy to miss and is stated only here: on the **4-hour** a
point of interest is **not** required, on the **hourly** it **is**. "With the 4-hour chart,
you're going to be looking for a candle two closure. You do not need a point of interest
here. Now, with an hourly chart, you do need a point of interest and you do need a candle
two closure."

It also supplies a **separation test** for trading away from equal highs/lows, which the
library has flagged as underspecified: "If you're trading price in this area here, I
wouldn't really want to trade that because price is pretty close and could just sweep it
out before going. But, because price displays so far away... there's a lot of separation
between the opening price and this low. So, it doesn't really bother me." Distance from the
equal lows is what makes them safe to trade away from — still unquantified, but the
variable is now named.

And the two-sided candle 2 case is resolved cleanly: "you might say it's a candle to
closure to the upside and the downside. Yes, it is, but this is where our higher time
frame bias comes into play. We are only looking bearish in this bearish candle three."

He deliberately includes a **mechanically perfect setup that loses**: "everything is
mechanical and valid. And I'm doing this to show you price can meet all of your
expectations and still stop you out." The idea is not discarded after the stop; he waits
for a new 4-hour candle 2 closure and the re-entry wins.

### Rules / conditions stated

- Daily C2 closure + hourly CISD → trade candle 3.
- Structure timeframe: 4H (C2 closure, no POI needed) or 1H (C2 closure **and** POI).
- Entry timeframe by pairing (4H→15m, 1H→5m), CISD required.
- Enter on a continuation; let the wick form.
- Two-sided C2: the HTF bias picks the side.
- Separation test before trading away from equal highs/lows.
- Widen the stop slightly when the reach into the POI was very shallow.
- 2R minimum.

### Open questions

- Why the 4-hour is exempt from the POI requirement is asserted, never justified.
- "A lot of separation" is unquantified.

---

## The Only Trading Strategy You Need For 2026 (`9AL41xON3hA`, 874s)

### What is actually taught

The compact restatement of the whole system, and it duplicates the daily-bias rule from
the playbook in cleaner language: a **continuation closure** is price closing outside the
previous day's range (over the previous day high → look higher; below the previous day low
→ look lower); a **reversal closure** is price sweeping the previous day's extreme and
closing back inside. Both give a bias for the *next* day.

It restates the POI list in a two-member form — "points of interest are always going to be
either a fair value gap or a low in a bullish scenario or a fair value gap and a high in a
bearish scenario" — which is the same list `NqSbvqDKML0` gives minus the conditional third
member. Worth noting as a minor internal inconsistency: the dedicated POI video adds the
CISD level as a last resort; this summary video omits it.

It also states the entry doctrine most explicitly: "we're not going to enter on that change
in the state of delivery. We're going to wait for another continuation" — i.e. the CISD
confirms, the **continuation order block** is the entry.

The last example is a deliberate non-trade. Repeated failures to form a continuation are
diagnosed as a range: "when we fail to form a continuation multiple times, this is just
becoming a range... I want to avoid it until one side of the range is taken." He then
declines the setup entirely: "this is not an example of something that I want to trade...
Don't try to force yourself on the market."

Timeframe pairing is restated as 1H→5m, 30m→3m, and the monthly/daily/hourly stack is
demonstrated on USDJPY, with the note that he sometimes deliberately does not refine
further.

### Rules / conditions stated

- Continuation closure vs reversal closure on the daily → bias for the next day.
- POI = fair value gap or a low (bullish) / high (bearish), located in the previous day's
  range.
- Wait for a candle 2 or candle 3 closure at the POI, then drop timeframes.
- Do **not** enter on the CISD; wait for the continuation order block.
- Repeated continuation failures = range; wait for one side to be taken, or stand aside.
- 2R, or a higher-timeframe target (previous day low, daily FVG) for more R.

### Open questions

- The POI list here is two members; the dedicated POI video says three.

---

## Trade Continuations Using Order Blocks (`IJcfC6wAPZU`, 1037s)

### What is actually taught

The dedicated entry video, and it is admirably mechanical. Missing the reversal entry is
not a problem — "that just means the reversal is confirmed and then I can look for
continuation entries." He names **exactly two** qualifying triggers and **one** waiver:

1. Price **retraces into a fair value gap**; then the close through the series of
   opposing candles into it forms the order block.
2. Price **sweeps a low** (or high); then the close through the series that swept it
   forms the order block.
3. Waiver: "the only time price does not need to sweep out a low or reach into a fair
   value gap is if we are using correlated assets and have an SMT with that."

The enforcement is strict and he demonstrates it by *not trading*: a candidate that falls
just shy of the fair value gap is rejected — "some will consider this a continuation
candle if we get closure below this. Now I do not because I needed to reach into a fair
value gap or sweep out a high and it fell short." And a whole move is skipped: "mechanically
speaking there is nothing here for me... this is just a move that I am going to miss."

Two practical refinements. When the displacement is very aggressive, a market entry does
not give the required R, so he takes the **retest** instead. And he does not need to know
*which* stacked fair value gap will hold — "I'm not looking to trade the high. I'm going
to let the high form and then trade the continuation off of it."

He frames the whole approach in distribution terms: "I'm not trying to get the low-risk
sell but instead the first or second stage of distribution." Volume imbalances get a single
passing mention as another acceptable important level. Demonstrated fractally down to
5-minute and up to daily/monthly.

### Rules / conditions stated

- Two triggers only: retrace into a fair value gap, or sweep a low/high.
- Then require the close through the series of opposing candles into that level.
- SMT waives the sweep/gap requirement, not the closure.
- Neither trigger → no entry; the move is missed.
- Retest entry when the displacement was too aggressive for the R.
- Track successive protected swings up/down the trend.

### Open questions

- Preference for the first continuation over later ones ("I feel like I'm chasing") has
  no rule attached.
- Fair value gap tagging tolerance is "that's fine if it digs a little bit deeper".
- Volume imbalances are named once with no definition.

---

## Stop Losses in Trading (`JHVaSKtE1Ys`, 996s)

### What is actually taught

The stop **is** the protected swing — the video is explicit that the protected-swing video
is a prerequisite and restates the definition: "a protected swing must reach into an
important level, which is sweeping out a low or reaching into a fair value gap. And then
when price closes over the series of down-close candles that swept out that low or into the
fair value gap."

One documented modification is permitted when R is insufficient: move the stop to the
**body** extreme (the mean threshold / 50% logic), with the cost stated up front — "I do
have to accept the fact that sometimes it will come sweep me out and then go and hit my TP
with this type of stop-loss placement." The alternative to widening is to improve the entry
instead: take a limit or wait for a retest.

Instrument-specific slack is acknowledged: on oil he deliberately gives more room "because
with oil likes to have these equal highs sometimes... sometimes it will come back, sweep
out, and then go."

The video also documents cases where the model gives a reversal entry but **no** valid
continuation entry — "there are no continuations within my model for a proper framework.
And that is going to happen. You are going to miss setups, you are going to miss trades even
if you know where it is going."

The re-anchoring rule is stated cleanly: when price fails to close through and makes a new
extreme, abandon the old series and track the new one. When the structure is messy he will
"ignore those small candles" and take the whole leg as the series — the one openly
discretionary part of an otherwise mechanical definition.

Closes with the scoping caveat: this invalidation logic is built off a CISD/order-block
model; users of breakers, fair value gaps or inversions must define their own.

### Rules / conditions stated

- Default stop: beyond the protected swing.
- If R fails: move to the body extreme (accepting sweep risk), or improve the entry via a
  limit / retest.
- Where no POI exists in the range, use 0.5 of the opposing-candle series (the T-spot).
- Give sweep-prone instruments extra room.
- Re-anchor on a new extreme when the close-through fails.
- Do not seek entries after the objective is hit — a new phase of price is due.

### Open questions

- "A little bit more room than normal" is unquantified.
- No rule chooses between the body stop and the retest entry for the same problem.

---

## Targets Using Projections (`upHS7SDL9kg`, 679s)

### What is actually taught

The most numerically specific video in the unit and fully mechanical. Set a Fibonacci tool
to **1, 0, -1, -2, -2.5, -4, -4.5**. Anchor it **inside candle 2 at the reversal point**:
find the low, find the high that made that low — the **manipulation leg** — anchor at the
low and drag to that high, then project.

Target selection is governed by the **size of the manipulation leg**, and this is the rule
that makes it usable:

- Normal-sized leg → look for **-2 to -2.5**; on continued expansion, **-4 to -4.5**.
- **Large** leg → "I'm not looking for price to reach for that -2 to -2.5. That is just too
  much range. I'm then going to use the -1 as my target."

He states the epistemics plainly: projections are used as **confluence to existing
liquidity targets** ("they are mechanical targets and I personally use them as a confluence
to existing liquidity targets"), and alone only where no liquidity rests — at all-time highs
or in empty territory.

One profit-taking rule is attached: when the -2/-2.5 sits just **beyond** a liquidity pool,
take profit at the pool rather than holding, "because a lot of times price will take out
this low and then if it's consolidating, go back into the range."

The YM example is the useful negative one: a large manipulation leg would project 500–600
points late in the New York session, which he dismisses as unreasonable and replaces with
the -1.

He notes the levels are a personal default: "You can always add levels that you find work
for you."

### Rules / conditions stated

- Fib levels 1, 0, -1, -2, -2.5, -4, -4.5.
- Always anchor inside candle 2 at the reversal; low → the high that made it.
- Normal leg → -2/-2.5, extending to -4/-4.5. Large leg → -1 only.
- Prefer levels that coincide with resting liquidity.
- Take profit at a liquidity pool sitting just inside a projection level.

### Open questions

- "Large manipulation leg" is judged by eye; the closest to a threshold is one example
  where the leg is "almost half" the distance to the target.
- Wick or body anchoring is not specified.

---

## Trading the Invalidation of Daily Bias (`jKuXaC84Qx4`, 874s)

### What is actually taught

A tightly scoped video with a genuinely restrictive rule. He will trade **against** his own
daily bias in exactly **two** situations and no others: "I only approach invalidations of my
bias in two ways. That would be an opposing setup that forms or the invalidation of the EQ.
Any other way that a invalidation forms, I'm not interested in trading the other way."

1. **Opposing setup**: a candle 2 forms in the other direction, typically off the previous
   day high/low, confirmed on the lower timeframe — preferably paired with SMT or a
   continuation.
2. **EQ invalidation**: price closes beyond the equilibrium of the previous candle on the
   aligned timeframe, having formed no continuation in the original direction.

Everything else — consolidation, drift, simply not working — invalidates the *idea* but
creates no trade the other way. And the precondition is absolute: "you need to have a valid
fractal model to then have an invalidation. You can't just trade an invalidation without a
model forming. So, don't try to just pattern trade this."

Even when trading the invalidation, the entry rules do not relax: "even if I'm trading a
reversal or an invalidation, I'm still looking for a continuation."

Targets are enumerated: the EQ of the previous candle, then the previous day low/high; and
on a failed candle 2, the candle 2's own extreme becomes the draw on liquidity. Wick size
governs which — small wick supports expansion to the current extreme, large wick means
targeting only back to the opening price / EQ.

He is careful about over-claiming, twice: "it doesn't mean that price can't reverse here and
then trade higher. It's just once price reaches beyond that EQ, it's not a small wick
anymore mechanically. It's less likely to expand." And on a counter-example: "just because
you see a closure through the EQ or an invalidation trade occurring, doesn't mean it's always
going to go hit the targets... You have to have that discernment."

### Rules / conditions stated

- Only two tradeable invalidations: opposing setup, or EQ invalidation.
- A valid fractal model must have existed first.
- Still require a candle 2 / candle 3 closure and a continuation in the new direction.
- Targets: EQ of the previous candle, previous day extreme, the failed candle 2's extreme.
- Wick size picks the target set.
- Fractal — demonstrated monthly → daily.

### Open questions

- Which candle counts as "previous" for the EQ test depends on an unspecified aligned
  timeframe.
- No filter separates EQ breaks that reach the target from those that do not.

---

## Using Currency Futures to Choose the Right Forex Pair (`HrjYoxAUb3s`, 912s)

### What is actually taught

An asset-selection video, taught literally as fractions. A pair is
numerator/denominator; raising the numerator or lowering the denominator makes it bullish,
doing both makes it strongly bullish. The actionable content is the **avoidance list**:
pairing strong with strong, or weak with weak, moves both sides the same way and leaves a
**consolidation**, not a trend. Pairing anything with a consolidating currency gives a
trend, but a weak one. The target state is strongest against weakest.

The **dollar gate** is the decision procedure:

- Dollar **trending** → pair against the dollar. Dollar bullish → find the weakest currency
  future. Dollar bearish → find the strongest.
- Dollar **consolidating** → do **not** pair against the dollar. Find the strongest and
  weakest non-dollar currency futures and trade that cross ("exotic pairing").
- Futures-only traders: trade the single most extreme currency future opposing the dollar,
  or long one and short another to synthesise the cross.

Anticipating the consolidating case has a rule: "Generally, after a large expansion or
hitting a higher time frame key level."

He is honest about resolution: "there's not always going to be just one best currency to
trade. A lot of times there are multiple different options for a single day, but there are
certainly ones that you want to avoid... really what you want to do is really focus or hone
in on the ones you don't want to trade." So the procedure is better at exclusion than
selection — worth recording, because a detector should be scored on exclusions.

He also skips CHF in one example specifically because it "has just taken out a pretty big
target", which is the `dont-trade-after-expansion` logic applied to asset selection.

### Rules / conditions stated

- Avoid strong+strong and weak+weak (result: consolidation).
- Trending + consolidating = a trend, but weak.
- Target strongest vs weakest.
- Dollar trending → pair against the dollar, opposite extreme.
- Dollar consolidating → exotic pairing between two non-dollar futures.
- Expect dollar consolidation after a large expansion or at a HTF key level.
- If dollar consolidates/retraces, expect euro and pound to do the same in the other
  direction.
- Skip a currency that has just taken a large target.

### Open questions

- The five strength grades are icons on a slide; no derivation, no lookback window.
- Ranking is eyeballed from daily candles.

---

## Cross-video observations

1. **The two-part gate is the spine of the entire unit.** A higher-timeframe candle 2 or
   candle 3 closure, AND a change in the state of delivery inside that candle on the paired
   lower timeframe. Neither half alone. It appears in 14 of the 20 videos and is stated as a
   two-way lock in `vn1RYjhJUnQ`. Any detector should implement this pair first; everything
   else is a filter on top of it.

2. **Almost every remaining gap in the model reduces to one unquantified variable:
   wick size.** Small vs large wick decides whether candle 2 is tradeable, which half level
   to use (0.5 of the wick vs 0.5 of the range), which target set applies, and whether
   manipulation and distribution share a candle. Five videos use it; none defines it. If one
   number were to be recovered by fitting, this is the one.

3. **The model is deliberately exclusionary and he demonstrates it repeatedly.** Moves that
   cannot be caught (`8BWkRGhuj1k`, `IJcfC6wAPZU`), setups that are mechanically valid and
   still lose (`q3nauvjT3q0`, `TNybDCtwBnc`, `9BY-MQRNy-Y`), and setups he refuses on R or on
   a missing point of interest (`m4k_1pF5zFI`, `NqSbvqDKML0`, `9AL41xON3hA`). A backtest that
   only measures hit rate on taken trades will misread this system; the skip rate is part of
   the design.

4. **Everything is one recursive operation.** Let the higher-timeframe wick form, confirm it
   on the paired lower timeframe, trade the body — applied at monthly→daily→hourly,
   weekly→daily→hourly, daily→4H→15m, daily→1H→5m, 1H→15m→1m. The four named strategies in
   this unit differ only in which rungs of that ladder they occupy.

5. **Two contradictions surfaced against material already in the library.**
   - **C3 closure reference.** This unit says candle 2's *opening price* / *body*
     (`vn1RYjhJUnQ`, `SF61vCsBl1A`). The sibling unit `..._01`, drafted from the first half
     of the same playlist, records candle 2's *extreme* (high/low). Both are recorded;
     `fractal-model-c3` is filed `contested`. The library's older EQ-based reading — the
     degenerate one — is supported by **nothing** in this unit.
   - **POI list length.** `NqSbvqDKML0` (dedicated) says three: fair value gap, swing
     high/low, and the CISD level as a rarely-used last resort. `9AL41xON3hA` (summary) says
     two, omitting the CISD level. The dedicated video wins.

6. **The 4-hour grid is not one grid.** Futures 02/06/10/14 NY (confirming the library's
   resolved reading), forex 17/21/01/09 NY — a one-hour offset that the speaker flags
   verbally and never explains. Any 4-hour power-of-three detector must branch on asset class.

7. **Numbers that actually appear**, and they are few: 2R minimum and the 34% break-even win
   rate (`TNybDCtwBnc`); the projection level set 1/0/-1/-2/-2.5/-4/-4.5 with the
   large-leg→-1 rule (`upHS7SDL9kg`); 0.5 of candle 3's range for candle 4 (`5fnFOh5YuM0`);
   50% of the bodies for the CISD-level POI (`NqSbvqDKML0`); "half of the candle" as the
   consolidation timing cut-off (`vn1RYjhJUnQ`). Everything else is qualitative.

8. **Terms used but never defined in this unit** (inherited from elsewhere): T-spot,
   failure swing, fair value gap, inversion, breaker, mean threshold, SMT, propulsion block,
   high/low resistance liquidity, volume imbalance, average daily range. Only the CISD and
   protected-swing procedures are spelled out step by step here.
