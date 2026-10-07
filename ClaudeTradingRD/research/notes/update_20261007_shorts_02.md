# Study notes — unit `update_20261007_shorts_02` (Shorts, update pass)

Seven Shorts (28–59 s each, ~6 min total), all TTrades' own voice. All transcripts are
auto-captions with **no timestamps**, so no `approx_time` is recorded. Every transcript was
read in full (each is a single paragraph of 100–250 words). None of these seven video ids
appeared anywhere in the library before this pass. Charts are not visible, so no price
levels are stated in any transcript — worked examples are recorded by weekday sequence only.

---

## Macros Are Fake, Let the New Candle Open (4gmcuekSnjU, 28 s)

**Taught.** Macros are "fake... my opinion". They are arbitrary ranges drawn around the opens
of new higher-timeframe candles (new 4-hour, hourly, 30-minute). Execution rule: he would not
enter at 9:50, near the end of a 15-minute candle; he waits for the new candle open.

**Example.** No instrument or level; only the 9:50 time.

**Hygiene.** "Cuz" = because. Clean otherwise.

**Library.** Pure repeat of `macros-are-htf-opens` (the 9:50 example is already there from a
stream). Draft adds the source only.

## Consolidation Reversal → Expansion (BJL66W1m-c4, 45 s)

**Taught.** After a large-range move the next candles are a consolidation or a retracement
("a large range to a small range") → look for continuation into the other side of the range /
the range high. Zoom in, find the series of candles that made the low, check for a close over
it — yes, so a continuation is looked for on Friday. Price must not take out that low; it should
form its lower wick there and trade higher.

**Example.** Friday continuation. Price dips "a little bit lower" than the low with an SMT on
the low, then expands through the other side of the range. Neither the instrument, the SMT pair
nor the levels are named.

**Hygiene.** Clean. The clip never says which weekdays formed the consolidation.

**Library.** Repeats `consolidation-reversal-week` (including the existing "SMT marginal
break" ambiguity) and `continuation-signature` (large range → small range). Source added
under `consolidation-reversal-week`.

## Midweek Reversal Breakdown (HkYIaPT8cms, 59 s)

**Taught.** Monday expands higher, Tuesday forms a reversal candle. Wednesday is expected to go
back lower into one of two fair value gaps and form a swing point to trade higher. Wednesday
reverses the bearish expansion out of a point of interest = candle 2 closure. Go to the hourly:
there is a change in the state of delivery → "on this next day, it is okay to be bullish". Thursday
expands, strong close → Friday continuation also looked for. Summary line: Wednesday reversal,
Thursday continuation, strong Thursday close → Friday continuation.

**Hygiene.** Clean.

**Library.** Matches `midweek-reversal-week` in mechanics (Wed C2 + H1 CISD → Thu, strong Thu
close → Fri). **Different:** the early-week shape. The library requires Monday and Tuesday to
both close against the bias; here Monday expands *with* the eventual bias and only Tuesday
opposes. This partly resolves the library's open ambiguity ("whether both Monday and Tuesday
must oppose") toward "not both". Flagged `new_claim`.

## Intraweek Reversal → Expansion Higher (UoEA2aJqz9Q, 56 s)

**Taught.** Prior Friday has failure swings on the lows → let Monday open. Monday expands away.
Tuesday: a *small* candle 2 closure opposing Monday → only a retracement / previous-day-low run
is expected. Next day: candle 2 closure, hourly change in the state of delivery and a new
continuation; the low must not be taken as it expands higher. It continues higher. He looks for
the next day to continue too but warns it may consolidate — it moves up but comes back into
the range.

**Hygiene.** "how really change in the state of delivery" = hourly CISD. "...previous day low to
get taken out, which is a new fair value gap" is garbled; meaning unrecoverable.

**Library.** Title says intraweek reversal; mechanically this is closer to a retracement-day
then continuation (Tuesday is the opposing day, Wednesday resumes Monday's direction). The
"small opposing C2 = retracement only" read overlaps `reversal-candle-target-adjustment`.
Recorded under `intraweek-reversal-week` with that tension noted; `new_claim` false.

## Daily Bias Invalidation (agFEDu61u3c, 55 s)

**Taught.** Daily: V-shape reversal, strong close into highs = bullish candle 2 closure. Expected:
open, trade lower into the point of interest (a fair value gap), respect the EQ, trade higher.
Actual: price consolidates in the POI ("does not look good for a reversal to continue higher"),
then a very aggressive close below the EQ, disrespects the FVG, not bought back → anticipate
continuation lower into the candle 2 low. Named a "failed candle two": cannot form a bullish
setup, therefore just a bearish setup.

**Hygiene.** Clean.

**Library.** Repeats `invalidation-trade` (EQ close + no reclaim; failed-C2 targets its own low —
already in the entry). Small additions: consolidation inside the POI as an early warning, and the
alias "failed candle two". `new_claim` false.

## Trading From Relevant Lows to Relevant Highs (ngpzd047kjU, 59 s)

**Taught.** Crude oil, daily. Stacked failure swings: the lows are relevant lows with small
reactions; the highs are all failure swings. Would not short off a high that leaves another
above it; even a high with "a bit of separation" is still a failure swing. The relevant high is
beyond the cluster. Price finally hits the relevant low → look for a reversal back to the
relevant highs. Failure swings = stacked highs = stacked liquidity = the target; the stop side
should hold high resistance liquidity / no failure swings.

**Hygiene.** Clean. Instrument is oil, not gold/indices.

**Library.** Repeats `failure-swing`, `high-vs-low-resistance-liquidity`,
`trade-away-from-manipulation`. One point worth recording: visible separation alone does not
make a stacked high relevant — in tension with `relevant-swing-separation`. Recorded as an
ambiguity under `failure-swing`.

## Thursday Counter Profile → Friday Bias (wbhjwy2A3UU, 56 s)

**Taught.** "Not a perfect example." Mon/Tue/Wed expand higher; Thursday does not take out
Wednesday's high but still counts as a Thursday counter (it counters the range). Even if you
miss the reversal day, the profile gives Friday's bias: trade toward the weekly open and the
current week's low — which it does. Intermarket: on ES / NQ the reversal formed Wednesday, so it
is really a Thursday continuation of a midweek reversal, and one could have looked for the
reversal on Wednesday in this asset too.

**Hygiene.** Clean. The traded asset is not named.

**Library.** The relaxation (Thursday need not take Wednesday's high) and the Friday targets
are already in `thursday-counter-week`. **New:** the intermarket reclassification — a
correlated index's earlier weekly reversal day re-labels the profile and moves the expected
reversal a day earlier in the traded asset. This is a one-day *lead*, distinct from
`cross-asset-reversal-confirmation` (same-time), and conflicts with
`intermarket-correlation-not-used`. Flagged `new_claim`.

---

## Cross-video: new vs repeat

**Nothing genuinely new as a concept.** All seven Shorts map to existing entries; seven drafts
reuse existing ids.

Material additions to existing concepts:
1. `midweek-reversal-week` — Monday may expand with the bias; only Tuesday need oppose before
   the Wednesday C2 + H1 CISD (testable relaxation of a precondition).
2. `thursday-counter-week` — intermarket reclassification: if ES/NQ reversed Wednesday, treat
   the week as a midweek reversal and look for the reversal on Wednesday in the traded asset.

Repeats (sources/aliases only): `macros-are-htf-opens`, `consolidation-reversal-week`,
`intraweek-reversal-week` (with a note that this example looks more like retracement →
continuation), `invalidation-trade` (alias "failed candle two"; POI consolidation as warning),
`failure-swing` (separation alone is not enough).

Common thread across the four weekly-profile Shorts: every profile is gated by the same
daily candle 2 closure + hourly CISD, and the "strong close → next-day continuation" rule
keeps appearing without a threshold.
