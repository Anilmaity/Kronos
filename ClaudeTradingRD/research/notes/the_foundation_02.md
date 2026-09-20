# Study notes — unit `the_foundation_02` ("The Foundation", batch 2 of 2)

Channel: TTrades_edu. Playlist: **The Foundation** — his own core curriculum, not Q&A.
Three videos in this batch, all three transcripts present and readable (auto-en). Each is
also cross-listed under "Education - ICT (Updated)" and "Education - ICT".

| video_id | title | duration |
|---|---|---:|
| `iEaMbuFZb24` | Trade Like TTrades - Top Down Analysis | 1224s |
| `ZVUDpCyvxfQ` | Understanding Fair Value Gaps (FVG) - ICT Concepts | 596s |
| `sgAnVR6RSDg` | Understanding Market Structure For Trading | 847s |

**Why this batch matters disproportionately.** These are polished lesson videos, not live
commentary, so they are where he states definitions rather than uses them. Two of the three
are the *dedicated* videos for terms the rest of the corpus treats as assumed knowledge
(fair value gap, market structure), and the third is the dedicated statement of the top-down
procedure that every Chart Lesson and live stream silently runs. Where this unit disagrees
with the live streams, `the_foundation_02` should be treated as the reference reading and
the live-stream entry as the working practice — I have marked those cases `contested` rather
than overwriting either side.

`the_foundation_01` covered the other 14 videos of this playlist; this note deliberately does
not restate its material. Overlaps are handled by adding evidence to the same concept `id`,
not by re-describing the concept.

---

## Transcript hygiene

All three transcripts are auto-generated and carry **no timestamps**, so **no `approx_time`
appears anywhere in this unit's concept files** — inventing one would be a fabrication.

Auto-caption artifacts that had to be decoded before the transcripts made sense. Every quote
in the YAML files is reproduced **exactly as transcribed**, garbles included, because the
validator matches quotes verbatim against the transcript:

- The known corpus-wide artifact — **"candle 2" rendered as "candle to"** — does **not**
  occur in these three transcripts. None of the three uses fractal-model candle numbering at
  all; the top-down video builds the same stack out of "bias / structure / entry" instead.
- `ZVUDpCyvxfQ` mangles the ICT acronyms throughout: **SIBI → "city" / "sibi"** and
  **BISI → "busy" / "bissy" / "bissy"**. The definition sentences come through as
  *"a city is a sell side imbalance thy side inefficiency"* (thy = buy) and *"a busy is a buy
  side inbounds sell side inefficiency"* (inbounds = imbalance). Also **"pair value gap"** for
  fair value gap in the opening line, **"the 50 of the fair value Gap"** for *the 50% of*, and
  **"volume in bonds hand cap"** for *volume imbalance and gap*.
- `ZVUDpCyvxfQ` renders *"when a fair value gap fails"* as **"winning fair value Gap fails"**,
  and *"a complete absence of trading"* as **"a complete absence of greeting"** in the final
  sentence (it is correct the first time, three sentences earlier).
- `iEaMbuFZb24` renders **mean threshold → "main threshold"**, **down-close candles → "down
  Clos candles"**, **0.5 → "05"**, and *"an area to support"* → **"an area for A2 support"**.
  It also renders *"I can* **not** *go lower"* as **"I cannot go lower"**, which inverts the
  sense of a load-bearing sentence: the surrounding clause is *"if I was just wanting to
  execute on the hourly time frame which I can do I don't need three time frames I cannot go
  lower if I can manage my risk"* — he is saying going lower is **optional**, not impossible.
  This is flagged inside `invalidation-first-timeframe-selection`.
- `iEaMbuFZb24` also has **"we WR back into a point of Interest"** (we *wrap/retrace* back)
  and **"price has wretch into it"** / **"as it wretch into a fair value Gap"** (*reached*).
- `sgAnVR6RSDg` renders **"low-risk buy" → "lowrisk buy"**, **"shift in structure" → "shift
  inst structure"**, **"5-minute chart" → "F minute chart"**, and **"bearish" → "beish"** once.

---

## Trade Like TTrades - Top Down Analysis (`iEaMbuFZb24`, https://youtu.be/iEaMbuFZb24, 1224s)

### What is actually taught

This is the video the rest of the channel assumes you have watched. It opens not with a
procedure but with a **loss**, drawn in a PDF. A textbook bullish order block forms — price
takes out a low and closes through the series (or single) candle that made it — and the
retest is taken long with the stop on the low. The stop is run. He says he sees many people
doing this and wondering why it happens, and gives a one-line diagnosis: the higher-timeframe
analysis was not considered. On the higher timeframe a high had just been swept and a bearish
engulfing candle had closed below the low, so the next candle was expected to continue lower.
The correction is stated as a counterfactual — if he were not trading it like a pattern, he
would look **only** for bearish setups inside that bearish expansion candle — and the
mirror-image bearish order block sits at the same price, formed the same way. So the entry
mechanics were never the problem; the directional filter was.

He then states the procedure as **three named slots with three different jobs**, and this is
the cleanest statement of it in the corpus:

1. **Bias** — the highest timeframe supplies direction only. In the worked case: a swing
   point has formed and price has closed below the previous day low, so he anticipates
   expansion lower.
2. **Structure** (he calls it the *intermediate* or *supporting* timeframe) — this chart does
   **two** jobs, and he enumerates them: look for a change in the state of delivery to confirm
   the higher-timeframe wick has formed, *and* use the same chart to find the point of
   interest to trade off of.
3. **Entry** — at that point of interest, look for opposing candles or order blocks.

The instances shown are daily→hourly→5-minute (twice), and weekly→4-hour→15-minute for
silver. Crucially, **the third slot is optional**: mid-example he executes on the hourly and
says he does not need three timeframes and can not go lower, provided he can manage his risk;
the choice is "just personal preference", and the stated reason for going lower is to enter
into the *same* higher-timeframe objective with better risk-to-reward. Targets always come
from the higher timeframes, never from the entry chart.

The video's thesis is stated as an equation rather than a filter: **expansion *is* timeframe
alignment**. He asks "when does expansion occur" and answers that it is when you align all
the timeframes together — and in the silver example he points at the exact bar where the
15-minute turned bearish under an already-bearish 4-hour and weekly.

Two secondary mechanics get real airtime. First, the **wick doctrine**, stated more crisply
here than anywhere: if we are going to have an expansion candle it will have small wicks and
a larger body, so what he is focused on is letting the wick form in the higher-timeframe
candle, and once it has formed he trades the body — after the high forms, from the high to
the low and then the close. What licenses calling the wick "formed" is named mechanically:
the change in the state of delivery is what confirms it. Second, the **continuation
preference**: having shown a valid first entry on the 5-minute closure, he says he prefers
continuation entries, waits for price to sweep a low and close over the down-close candles
that made it, calls the result a valid order block "or in this case a propulsion block", and
puts the stop on that new low "because it is now protected".

The gold example closes the video and contains the most decidable rule in it. After continued
expansion into a fair value gap he says he is looking for a **new phase of price delivery** —
consolidation, retracement, or reversal — and that he uses the daily candles to tell him
which, so he lets a further daily candle print rather than classifying off the expansion.
That candle is not consolidating (it forms a strong bearish closure), so the next close
decides: **close lower → reversal, trade to the lows; close back inside the range →
retracement, trade higher.**

### Concepts introduced (his terminology)

Higher-timeframe bias; intermediate / supporting timeframe; structure; point of interest;
opposing candles; order block; propulsion block; mean ("main") threshold; change in the state
of delivery; high resistance liquidity; 0.5 of the wick; new week opening gap; expansion
candle (small wicks, larger body); letting the wick form; open-low-high-close; failure swings;
protected low; two points of interest overlapping; standard deviations (from his indicator);
new phase of price delivery (consolidation / retracement / reversal); discount of the range;
continuation entries; runners.

### Rules / conditions stated

- Read the higher timeframe first; inside a bearish higher-timeframe expansion candle, look
  only for bearish lower-timeframe setups.
- Bias timeframe → direction only. Structure timeframe → CISD confirming the HTF wick **and**
  the point of interest. Entry timeframe → opposing candle / order block at that POI.
- A CISD is demanded at *every* level of the stack he uses — hourly under the daily, then
  again on the 5-minute; weekly closure, then again on the 15-minute.
- Where a swing low has already been swept it is **high resistance liquidity**; do not use the
  low itself, mark **0.5 of that wick** and require it to be respected.
- On the structure chart, if the leg contains no fair value gap or point of interest, fall
  back on a sweep of the previous low as the point of interest.
- Preferred entry is the **continuation**: sweep a low, close over the down-close candles that
  made it, enter at market, stop on the now-protected low, look for 2R.
- Do not take a setup whose path immediately runs into nearby lows — "so close to these lows I
  would anticipate the lows to get taken out"; require a close over the level first, then
  trade the following candle as a reversal candle.
- Missing an entry is not disqualifying while the objective is unreached; go back to the
  structure timeframe and wait for a **new** setup rather than entering late.
- The third timeframe is optional; the gate is whether risk can be managed where you are.
- Targets are taken from the higher timeframe (previous highs, the objective, standard
  deviation projections); 2R is the near target and runners go to the HTF objective.
- After expansion into a fair value gap, let a daily candle print, then classify:
  close lower → reversal; close back inside the range → retracement.

### Examples walked through

1. **PDF** — the losing bullish-order-block retest and its bearish mirror at the same price.
2. **Daily → 1H → 5m (instrument unnamed).** Daily: swept swing low = high resistance
   liquidity; 0.5 of the wick reached, swept and closed back inside; the new week opening gap
   above is the objective. Hourly: 0.5 of the wick to be respected, then a CISD (close through
   the down-close candles that made the low) confirms the wick; no FVG in the leg, so a sweep
   of the previous low is the POI. 5m: CISD → first entry (stop on the low, 2R); then the
   preferred continuation — sweep, close over, propulsion block, stop on the new protected
   low, 2R. Reaches the short-term high and the new week opening gap.
3. **Silver, weekly → 4H → 15m.** Weekly: previous high taken, close back into range,
   continuation lower, then a closure through the up-close candle that made the high; failure
   swings below, an FVG as the target. 4H: let the wick form (expansion candle = small wicks,
   larger body); price sweeps a high *and* reaches an opposing candle — two POIs overlapping —
   then closes back inside the previous bar; equal lows and a previous low are the targets.
   15m: retrace into an FVG, closure through the up-close candles → CISD + order block; enter
   on the close (his preference) or the retest, stop on the high. **3R**, and the target
   coincides with his indicator's standard deviations.
4. **USDJPY, daily → 1H → 5m.** Daily: trade back into an FVG sweeping previous day low forms
   a protected low; an FVG inside the range; price reaches in and closes back inside the
   previous bar → bias higher next day. Hourly: CISD confirms the wick; previous day high is
   the target; next-day shape wanted is open-low-high-close with a shallow opposing run.
   Sweep of a consolidation low, then the closure over → hourly execution possible (4R to the
   high, or take 2R). Then displacement leaves an FVG; a later reach-and-close-back-inside
   drops him to the 5m, first setup in **London**. Missed-entry handling; a second hourly
   setup (retrace into the order block, sweep, closure) and a second 5m entry; a setup
   declined for being too close to the lows.
5. **Gold, daily → 1H → 5m.** Bullish structure (HH/HL) expands into an FVG → new phase of
   price due. Bearish closure → not consolidation; next close decides retracement vs reversal;
   it closes back inside → retracement, target the highs. Hourly: sweep + CISD, want
   open-low-high-close; a new **propulsion block** marks the floor and no close below its mean
   threshold is wanted; price retests an opposing candle back in the discount of the range and
   closes strongly. 5m: closure through the down-close candles into the POI, refined to a new
   order block formed as price reached into an FVG; ~2R to the local highs, runners to the
   hourly standard-deviation projections and previous highs.

### Quotes

- "when does expansion occur it is when you align all the time frames together"
- "the first thing I want to do is have a higher time frame bias"
- "once that Wick forms I can then look to trade the body"
- "I don't need three time frames"

### Open questions / ambiguities

- The slot ratios are inconsistent: daily→hourly is 24:1, weekly→4-hour is 42:1, and no rule
  picks the pairing or the starting timeframe.
- "If I can manage my risk" — the gate for skipping the entry timeframe — is never turned into
  a test (no max stop in points, % of ADR, or R).
- **Propulsion block** is used twice and defined neither time; the only observable difference
  from an order block is that it forms inside an existing leg.
- The **new week opening gap** is used as the daily objective and never defined.
- "So close to these lows" (the proximity veto) has no distance threshold.
- The **T-spot**, standard deviations and the CISD markings all come from his own indicator in
  three of the examples, so several "observations" are really indicator output.
- The instrument is named in only two of the four examples (silver, USDJPY, gold — the first
  is unnamed).

---

## Understanding Fair Value Gaps (FVG) - ICT Concepts (`ZVUDpCyvxfQ`, https://youtu.be/ZVUDpCyvxfQ, 596s)

### What is actually taught

The canonical definition video, and it is unusually disciplined: definition, then three
negative examples, then naming, then behaviour, then two look-alike objects it must not be
confused with.

**The definition**: a fair value gap is a three-candlestick pattern where the first candle's
**low** does not overlap with the third candle's **high**, or where the first candle's
**high** does not overlap with the third candle's **low**. He then demonstrates it physically —
drag the first candle's low out, drag the third candle's high out, look for space between the
lines — and does the same three times with candle triples where the lines *do* overlap, to
show what is **not** a fair value gap. Because the construction is stated and demonstrated in
terms of the candles' high and low, **the test is on wicks, not bodies**. That resolves an
open question `the_foundation_01` had to leave hanging.

**Naming**: SIBI is *sell side imbalance, buy side inefficiency* — sell side was offered but
buy side was not — which he then flattens to "simply put, a bearish fair value gap". BISI is
the mirror and is simply a bullish fair value gap. The economics are a gloss on the same
object, not an additional condition.

**Three levels, three behaviours.** He says there are three things he looks for *within* a
fair value gap: the **start** of the gap, the **consequent encroachment** (50%), and the point
where price **completely fills** it. Three return behaviours are accepted: reach in, close
back out, continue; reach the CE, where he would like a candle to close outside but is
"pretty flexible" as long as the CE is respected; or fill the gap entirely, where he prefers
the close to come back outside the CE — and adds that he would also like price to reach the
discount of the range.

**And here the video contradicts itself, which matters more than anything else in it.** In
the invalidation section he says the one thing he looks for when invalidating a fair value gap
is *this close* — when price starts to close **over the consequent encroachment or outside of
the fair value gap**, price is not respecting it and often will not reverse back. Twelve
sentences later, walking an inversion, he calls the close below the consequent encroachment
"our first clue", notes that price then cannot displace back out, and waits for a **close
below the whole fair value gap** before treating the gap as inverted. The library's existing
position (recorded by `the_foundation_01` from the IFVG video) is the second reading: a CE
close is "explicitly NOT sufficient". Both readings are now sourced to the *same* video, so
this cannot be resolved by preferring one source. The likely reconciliation — that the CE
close kills the gap as a level to trade *from*, while the full-gap close is what licenses
trading it as the opposite polarity — is recorded as an **inference, not as his words**.

**Inversion** gets one genuinely new detail: the inversion and its retest do **not** need to
occur back to back, the two gaps do not have to overlap, and the return may come after an
intervening period of consolidation. Any detector built from the IFVG video alone would have
missed that and thrown away valid retests.

**The closing section** distinguishes three objects that all look like holes in a chart: a
fair value gap is the three-candle non-overlap; a **volume imbalance** is a gap between the
closing price of one candle and the opening price of the next where price nonetheless traded
through the area (the candles' highs and lows overlap); a **gap** is the same construction
with a complete absence of trading between the two candles. He shows price returning to a
volume imbalance and reacting from it, so it is a usable level, not a curiosity.

### Concepts introduced

Fair value gap (3-candle, wick-based); SIBI ("city") and BISI ("busy") with their imbalance /
inefficiency expansions; the three levels within a gap (start, CE, complete fill); consequent
encroachment; respecting vs invalidating a gap; inversion fair value gap and its non-adjacency;
failure to displace back out of a gap; discount of the range as a refinement; volume imbalance;
gap (true, no-trade).

### Rules / conditions stated

- FVG = three candles; candle 1's low does not overlap candle 3's high (bearish), or candle
  1's high does not overlap candle 3's low (bullish). Overlap ⇒ no gap.
- SIBI = bearish FVG. BISI = bullish FVG.
- Mark three levels in every gap: the start, the CE (50%), and complete fill.
- Acceptable reactions: close back out at the near edge; respect of the CE (close outside
  preferred, but flexible); or full fill followed by a close back outside the CE.
- On a full fill he would also like price to reach the discount of the range.
- Invalidation (reading A): a close over the CE *or* outside the gap.
- Inversion (reading B): the CE close is a clue; a close beyond the whole gap is what inverts.
- An inverted gap is used as support/resistance on return; the return need not be immediate,
  the gaps need not overlap, and consolidation may intervene.
- Volume imbalance = close-to-open space **with** high/low overlap. Gap = complete absence of
  trading between the two candles.

### Examples walked through

No instrument is ever named. Six chart segments: two FVG identifications plus a third after an
aggressive opposite move; a SIBI and a BISI labelled side by side; a CE respected and a CE
closed straight through (the invalidation case); a BISI worked with a discount refinement; the
non-adjacent inversion (close below CE → cannot displace back out → close below the gap →
much later, the old BISI used as resistance); a SIBI that holds through two sell-side raids
and is then closed over, after which its CE is used as support twice; and finally one volume
imbalance that reacts and one true gap.

### Quotes

- "the first candle low does not overlap with the third candle's high"
- "there are three things that I look for within a fair value Gap"
- "a volume imbalance is a gap between the closing and opening price"
- "this doesn't need to occur back to back"

### Open questions / ambiguities

- Whether exactly equal prices (touching, not overlapping) count as a gap is still not stated.
- No minimum gap size, and no expiry for an unfilled gap.
- "Respecting the consequent encroachment" is explicitly a flexible judgement, not a threshold —
  he says so in those words.
- The CE invalidation contradiction above is internal to this one video.
- Which of the three levels an *order* should sit at is never said; they are described as
  things he looks for, not entries.
- Volume imbalance has no CE analogue, no invalidation rule, and no minimum size; the
  price test for "complete absence of trading" is described in words but never written out.
- No ranking rule for a volume imbalance and a fair value gap sitting at the same price.

---

## Understanding Market Structure For Trading (`sgAnVR6RSDg`, https://youtu.be/sgAnVR6RSDg, 847s)

### What is actually taught

He explicitly defers the swing high / swing low definition to the liquidity video and starts
one level up. **Trend** is higher highs *and* higher lows (up) or lower highs *and* lower lows
(down), each measured relative to the immediately preceding opposite-side point, and he drills
it as a running expectation: after a higher high I want a higher low; after a higher low I
want a higher high.

**The change in trend** is where the mechanics live. Bearish-to-bullish: while making lower
highs and lower lows, price puts in a lower low and then **cannot displace lower**; it then
**displaces and closes over the previous high**, creating a higher high; the pullback is what
he calls the low-risk buy (the higher low); a further higher high confirms. Bullish-to-bearish
mirrors it, and he names the moment: *that is where our market structure shift or market
structure break would be*.

**This video is the corpus's best source on `displacement`, and that is its most valuable
contribution.** Every single time he adjudicates whether a break happened, he resolves it as a
**close beyond the reference level**, in his own words: "now we get some displacement a close
over this previous high"; "once we displace and close below this low"; "we can't displace
lower". He also uses the *absence* of displacement as a classifier — price makes a higher high
and a higher low and he refuses to call it a trend, because "is there any displacement here
no, it's really just kind of consolidation, we don't know where price is wanting to go". He
summarises the whole lesson as focusing on swing highs and swing lows **and the displacement,
or lack of displacement, around them**.

**Which pivot counts** is stated precisely, and it is the definition the library has been
missing: reviewing a messy stretch he rejects one candidate ("we do form a higher high but we
don't have a swing we break") and identifies the right one — *this is the low that made the
new high before price came and broke it*. That is the same object the corpus elsewhere calls
the protected swing, arrived at from the structure side rather than the entry side.

Two quality filters appear in passing. Swings that will serve as the continuation point are
preferred in **discount** (bullish) or **premium** (bearish) — "ideally I like to see
discount", and he declines interest in a lower high "because of premium and discount… I'd like
to see a premium array". And a new extreme may be registered **before** its swing confirms:
"you have a higher high even if we have not formed a swing High yet", while he narrates "let's
see if a swing forms" bar by bar. He also filters interior highs and lows that get swept
before price continues.

The video ends where the top-down video begins. On a 5-minute oil chart a structure shift
forms correctly — displacement and close below the low, then a lower high — and then fails:
price never closes below the low again and takes the first high instead. Zooming to the hourly
shows why: the whole "shift" was a retracement into an **hourly fair value gap** in an uptrend.
He generalises it — a lower-timeframe shift against the higher timeframe is a retracement, not
a reversal, and it is a lot easier to frame a continuation with the trend than to catch every
top or bottom. He closes by saying this is the foundation and that advanced market structure
is the next video (not in this unit).

### Concepts introduced

Basic market structure; trend as HH/HL and LH/LL; market structure shift / market structure
break; displacement and lack of displacement; "low-risk buy"; the low that made the new high;
consolidation (as the absence of displacement); swing confirmation timing; premium / discount
as a filter on structure points; higher-timeframe PD array; hourly fair value gap; the
lower-timeframe-shift-is-a-retracement failure mode.

### Rules / conditions stated

- Uptrend = higher highs and higher lows; downtrend = lower highs and lower lows, each
  relative to the preceding opposite point.
- The trend is intact while no opposing swing has been broken.
- Bullish shift: lower low → fails to displace lower → displaces and closes over the previous
  high (higher high) → higher low ("low-risk buy") → higher high confirms.
- Bearish shift: higher high/higher low → lower low → lower high → displaces and closes below
  that low (another lower low) → lower high completes it.
- The pivot that must break is **the low that made the new high** (mirrored for highs).
- A higher high with no swing broken is **not** a shift.
- Displacement is adjudicated as a **close beyond** the level, every time.
- Structure advancing with no displacement around it = consolidation; direction unknown.
- A new extreme may be registered before its swing confirms; the swing itself needs the
  right-hand bar.
- Ignore interior highs/lows that get swept before price continues.
- Prefer the continuation swing in discount (bullish) / premium (bearish) — stated as
  "ideally", not as a filter.
- Always read the higher timeframe first; a counter-trend lower-timeframe shift is a
  retracement into a higher-timeframe PD array and is expected to fail.

### Examples walked through

PDF diagrams of an uptrend, a downtrend, a bullish shift and a bearish shift, plus the
lower-timeframe trap diagram. Then a clean bullish trend walked bar by bar ("let's see if a
swing forms"); a clean bearish trend including swept interior swings; a deliberately messy
stretch (bearish micro-structure, a higher low with no displacement = consolidation, then
displacement and a close over the previous high, a retracement with no direction, then the
low that made the new high being broken → short to old lows); and finally the **oil 5-minute**
failure, resolved on the hourly as a retracement to an hourly fair value gap.

### Quotes

- "we're going to have to make higher highs and higher lows"
- "that is where our Market structure shift or Market structure break would be"
- "now we get some displacement a close over this previous high"
- "the low that made the new high before price came and broke it"

### Open questions / ambiguities

- Displacement still has **no magnitude**. Under his own stated test a close one tick beyond
  the pivot qualifies. The close proxy is decidable; it is not calibrated.
- He both registers a higher high before a swing confirms *and* rejects a shift because there
  is no swing to break — used in the same walkthrough, never reconciled.
- Which swings are eligible for comparison remains visual; an unfiltered 3-bar fractal will
  label far more structure than he does, and he gives no separation, range or lookback filter.
- Premium/discount on the continuation swing is a preference, not a filter — he follows
  structure points that fail it.
- Consolidation is defined only as the absence of displacement, and displacement is
  unquantified: the pair is circular for automation purposes.
- Nothing is said about running the read when the higher timeframe is itself consolidating.
- "Advanced market structure" is deferred to a video not in this unit.

---

## Cross-video observations

- **The unit is one argument, told three times.** Every video ends at the same place: a
  lower-timeframe object read without higher-timeframe context is a trap. The market structure
  video's oil failure, the top-down video's opening stop-run, and the FVG video's insistence
  on where the gap sits relative to premium/discount are the same lesson at three
  magnifications.
- **The confirmation gate is fractal, not hourly.** `the_foundation_01` and the weekly-profile
  unit both recorded the CISD gate as "hourly confirms the daily wick". The top-down video
  demands it on the hourly to confirm the daily **and again on the 5-minute** at the entry,
  and reads a weekly candle's own closure through the up-close candle as the same event before
  demanding it again on the 15-minute. Whether it is *required* at every level or only at the
  confirming level is never said — flagged in `hourly-cisd-confirmation`.
- **Definitions here are wick-based.** The FVG overlap test is stated on candle highs and lows;
  the 0.5 levels are drawn on wicks; swing comparison uses wicks in every chart segment. Where
  the corpus is silent on wick-vs-body, this unit consistently points to wicks.
- **Terms used but never defined in this unit** (recorded so a later pass does not mistake a
  mention for coverage): propulsion block, new week opening gap, T-spot, standard deviations /
  projections, failure swings, equal lows, killzone/London (named once, no times), bearish
  engulfing, mean threshold (used, not constructed), "high resistance liquidity" (used in a
  *different* sense from the live streams — see below).

### Against the context supplied for this reading

- **New York / EST clock and the 18/22/02/06/10/14 4-hour grid — not addressed at all.** None
  of the three videos states a timezone, a session time, or a candle-open time. The only
  temporal reference in the whole unit is "in London that is where we get our first setup", with
  no clock. So this unit **neither confirms nor contradicts** the live-stream clock findings —
  it is silent, and `est-timezone-anchor` / `ten-am-candle-alignment` gain nothing here.
- **EQ rule — the large-wick branch is CONFIRMED, the expansion-candle branch is absent.** The
  top-down video uses 50%-of-the-wick twice, both times on a large opposing wick: on the daily
  he marks 0.5 of the swept low's wick as the support area, and on the hourly he requires 0.5
  of that wick to be respected to trade higher. He defers the derivation to a dedicated "Wicks
  video" outside this unit. The *expansion candle → 50% high-to-low* branch does not appear
  anywhere in these three transcripts.
- **`session` (41 concepts) — no help.** Not defined, not timed, barely mentioned.
- **`consolidation` (23 concepts) — a partial, negative definition, and it is the only one the
  corpus has.** Structure advancing with no displacement around it is consolidation; a candle
  that forms a strong directional closure is *not* consolidating. No width, duration or bar
  count. Recorded as a new `consolidation` concept with `status: underspecified` and the
  circularity flagged explicitly.
- **`displacement` (15 concepts) — a genuine, speaker-stated, decidable proxy. This is the
  highest-value extraction in the unit.** In `sgAnVR6RSDg` he does not leave displacement to
  the viewer's eye: he resolves it as *a close beyond the reference structural level*, in
  those words, every time he adjudicates a break, and the top-down video corroborates the
  secondary proxy (the displacing leg leaves a fair value gap). It still has no magnitude, so
  the concept stays `underspecified` — but a v1 detector can now be written from his own
  wording rather than from an assumption, and every downstream detector (market structure
  shift, order block validation, consolidation classification) inherits it.

### Where this unit contradicts what the live streams / other units say

Recorded as `contested` in the YAML, with both readings preserved:

| concept | this unit (canonical lesson) | the library's existing reading |
|---|---|---|
| `high-vs-low-resistance-liquidity` | a **property of a swept swing** — an already-swept low *is* high resistance liquidity, so use 0.5 of its wick instead of the low | a **market-wide condition** set by the daily setup and by news, deciding whether price slices through levels or stalls |
| `point-of-interest` | on the entry timeframe, POIs are **opposing candles and order blocks**; a sweep of a previous low is a valid fallback POI | a closed enumeration — "fair value gaps, highs and lows, that's it", with order blocks excluded |
| `phases-of-price` | close **back inside** the range → **retracement** | failing to close over the opposing series and falling back inside → **consolidation** |
| `consequent-encroachment` | a close over the CE **invalidates** the gap (reading A, this video) | a close over the CE is a **clue only**; a close beyond the whole gap is required (reading B — also in this video) |

Everything else in the unit **agrees** with the Q&A streams. Specifically: the top-down slot
structure matches `timeframe-pairing` and `top-down-analysis-procedure`; the CISD confirmation
gate matches `hourly-cisd-confirmation` and extends it fractally; `wick-trust-test`
("let the wick form, trade the body") is confirmed almost verbatim; `small-wick-expansion-rule`
gets its cleanest single-sentence statement; `protected-swing` is confirmed from the entry side
and given its structural definition; `pattern-trading-error` and `structure-requires-htf-context`
are confirmed with worked losses; and `missed-move-no-chase` is refined rather than
contradicted (missing an entry is not fatal while the objective is unreached — but the remedy
is a new higher-timeframe setup, never a late market entry).
