# Study notes: unit `update_20261008_shorts_01` (Shorts, update pass 2026-10-08, batch 1 of 2)

Seven YouTube Shorts, 35 to 55 s each, about 5 min in total. All seven transcripts are on disk (auto-en)
and were read in full. They are auto-captions with **no timestamps**, so no `approx_time` is recorded.
Every clip is in TTrades' own voice (voice = ttrades). No guests appear. No price levels are spoken.

**The key fact about this batch:** each Short is a word-for-word cut of a long video that the library
already cites. A phrase search over all transcripts found the parent of every clip:

| Short | parent (already in library) | library id that already holds it |
|---|---|---|
| 4UVVK6Gavrs | A4NasIa371c *How to Set Price Targets Using the Fractal Model* | `smt-swing-point-substitute` (target variant, same quote) |
| 6IBR6kZ9nrU | SF61vCsBl1A *TTrades Ideal Formation* | `ideal-formation` (late completion for candle 4) |
| AIexWKldGU4 | -ocfPuD_oqE *How To Use SMT Divergence* | `smt-reversal-continuation-double` ("it has to support expansion lower") |
| JuLkLoAv3PM | uW55Tuk-ngY *New York Open Live Q&A* | `smt-requires-framework` ("SMT is a confirmation to a setup.") |
| MrNfRoNeL1I | Mo9QMtotQyo *How to Confirm Daily Profile* | `daily-wick-confirmation-timeframes` ("both checked off") |
| hWwyr-rTFW4 | -ocfPuD_oqE *How To Use SMT Divergence* | `smt-reversal-continuation-double`, `smt-requires-framework` |
| vtreLT_8v8I | rVRk4MLTJSs *New York Open Live Q&A* | `cisd` (OB vs CISD variant, same quotes) |

So the batch can only add new sources to existing ids. It cannot add new claims.

---

## Using SMT With Correlated Assets to Target Previous Highs (4UVVK6Gavrs, 37 s)
**Taught:** price was expected to reach a low as its target. The one case where price need not reach
it is an SMT, meaning a correlated asset takes the low out. On gold he uses silver ("because we're on
gold"), and silver took the low, so the target "has been hit". The move higher is now "backed with SMT"
and the next targets are the previous highs. He marks them and drops to the lower timeframe, where his
indicator marks them too.
**Library:** this repeats the target variant of `smt-swing-point-substitute`, which already cites the parent
with the same quote. It is also a usage example of silver as gold's correlate (`gold-correlated-assets`).
The silver claim was tested on 2026-10-07: u1007a (4h) was UNDERPOWERED and u1007b (1D) was NEGATIVE
(−0.35R, n=127). So nothing new is left to test.

## Ideal Formation to Support Expansion Higher (6IBR6kZ9nrU, 55 s)
**Taught:** a candle 2 closure reaches into an FVG and closes outside it. It is *not* ideal, because it did not
close over the down-close candle that reached into the gap. Candle 3 then closes over candle 2's high
and that level, which creates a protected swing. Candle 2 closure + strong candle 3 + protected swing makes
candle 4 the ideal trade ("a variation of an ideal formation"). He marks the level and candle 3's EQ.
Candle 4 holds there and expands.
**Library:** this repeats `ideal-formation`. The library rule already says that a non-ideal C2 followed by a C3 that closes
through the series is ideal for C4, and it lists the two marked levels. `ideal-formation` a/b were tested in
September (both UNDERPOWERED).

## If You're Trading a Reversal With SMT, It Needs to Support Expansion (AIexWKldGU4, 36 s)
**Taught:** the reversal is off the previous day's high. A small wick supports expansion, then comes a CISD, then a
reversal SMT of gold against gold-euro and gold-pound. If you use SMT on candle 2, or inside the reversal
candle before it closes, the candle "has to support expansion lower". In the example, price expands to the EQ,
fails it and takes the previous lows.
**Library:** this repeats `smt-reversal-continuation-double` (the "small wick before the SMT counts" rule, same
parent and same quote) and the gold-euro/gold-pound reading of `gold-correlated-assets`.

## Stop Trying to Force a Setup with SMT (JuLkLoAv3PM, 45 s)
**Taught:** people use SMT to force setups. SMT is a confirmation to a setup, and it cannot rescue
"garbage structure". He turns SMT off on the chart, and the setup off the previous day high "remains the
exact same". With SMT on, it is an added confirmation of a framework he already has.
**Library:** this repeats `smt-requires-framework`, where the parent is already the source of "removing SMT leaves the
setup unchanged". The `smt-requires-framework` claims from 10-07 (external vs internal SMT) were NULL /
UNDERPOWERED.

## Wait for the Daily Wick to Form Before Trading Intraday Reversals (MrNfRoNeL1I, 51 s)
**Taught:** a daily candle 2 closure with a CISD raises the question "has the daily wick formed?". Working into
London, price reaches an FVG. He waits for an hourly CISD, gets the close through and says yes. He can
get on side on the hourly. Once the 06:00 4-hour candle opens, he finds a 4-hour candle 2 closure too, so he could
trade on the 15-minute. Price holds and expands lower.
**Library:** this repeats `daily-wick-confirmation-timeframes`, the "hourly CISD + 4-hour closure, both checked off"
state from the parent. The Short drops the parent's preceding line ("don't use hourly candle two closures
earlier into the day"). **Hygiene / inference:** a 4H candle that opens at 06:00 is the futures grid
(02/06/10/14 NY), not the forex grid that the vault locks for gold. The asset is not named. Recorded as an ambiguity.
`daily-wick-confirmation-timeframes` a/b were tested in September (NULL / UNDERPOWERED).

## Using SMT as Extra Confirmation for a Reversal (hWwyr-rTFW4, 35 s)
**Taught:** a candle 2 closure with a CISD, plus a reversal SMT of NQ against YM from candle 2 to candle 1,
gives "extra confirmation" for expansion lower in candle 3. The bullish reading of the same candle is rejected.
"Follow the low, find the high": the down-close series has not been closed through, so only the
short is valid. Price sells off to target.
**Library:** this repeats `smt-reversal-continuation-double` (the C1–C2 location of a reversal SMT) and the
`smt-requires-framework` rule "trust only the side that also has a CISD". It is index futures, not gold.

## What's the Difference Between an OB & CISD? (vtreLT_8v8I, 37 s)
**Taught:** a CISD is the order block that changes the trend. An order block in line with the trend is just an
order block, or a continuation. After a bearish CISD, later bearish protected swings or OBs are not CISDs.
The next CISD would be a bullish one lower down.
**Library:** this repeats the `cisd` variant from rVRk4MLTJSs word for word, with the same quotes. `cisd` has been tested
four times (a/b and u1007a/b), and all four were NULL.

---

## Cross-video summary

**What is genuinely new:** nothing. Every clip is a verbatim cut of a long video that the library already cites for
the same rule. No new ids and no new claims.

**Repeats the library (new sources only, 7 drafts):** `smt-swing-point-substitute` (4UVVK6Gavrs),
`gold-correlated-assets` (4UVVK6Gavrs silver; AIexWKldGU4 gold-euro/gold-pound), `smt-reversal-continuation-double`
(AIexWKldGU4, hWwyr-rTFW4), `smt-requires-framework` (JuLkLoAv3PM, hWwyr-rTFW4), `ideal-formation` (6IBR6kZ9nrU),
`daily-wick-confirmation-timeframes` (MrNfRoNeL1I), `cisd` (vtreLT_8v8I).

**Psychology:** none in this batch.

**Hygiene across the unit:** there are no timestamps and no spoken levels. The assets are often not named. "Candle to" is a caption
error for "candle 2" (in hWwyr-rTFW4). Two of the clips (AIexWKldGU4, hWwyr-rTFW4) come from the same parent. The
06:00 4H candle in MrNfRoNeL1I implies the futures grid. That matters only if someone reads it as a gold
rule, and the asset is unnamed.

**Implication for the update pass:** Shorts that are clips of already-studied long videos add no information.
A cheap pre-filter for future passes is to phrase-match each new Short against the existing transcripts before
studying it.
