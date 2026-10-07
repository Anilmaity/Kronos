# Study notes: unit `update_20261007_shorts_01` (Shorts, update pass, batch 1 of 4)

Seven YouTube Shorts, 35 to 84 s each, about 6 min in total. All seven transcripts are on disk (auto-en)
and were read in full. They are auto-captions with **no timestamps**, so no `approx_time` is recorded.
Every clip is in TTrades' own voice (voice = ttrades). No guests appear.
The Shorts are cut from longer videos. They begin and end mid-thought, and the chart is only
described with "here" and "this", so **no actual price levels or times are spoken in any of them**.
Wherever a note below seems to give a level, it is only describing which way the chart moves.

---

## Breaking Down Relative Strength with SMT & Candle Closures (3ihK4q3axfI, 36 s)
**Taught:** this clip shows two ways to rank correlated assets.
(1) SMT at a shared low. One asset cannot take out its previous low (it makes a higher low) while the
other does (it makes a lower low). The higher-low asset is "propped higher", so it is the stronger one and the bullish read.
(2) Candle closures. On the upside, the asset that takes out its highs is "far more bullish" than one
that is held lower.
**Example:** two unnamed assets, bullish case, with no levels given.
**Hygiene:** the assets are never named. The clip cuts off before the closure comparison is finished.
**Library:** this repeats `relative-strength-asset-selection` (Tool 1 SMT and Tool 3 closures) and `smt-divergence`.

## Finding Points of Interest With Relevant Swings (91I_Pq2pZ2Y, 52 s)
**Taught:** highs that sit very close to earlier highs are failure swings. Even after all of them are taken out,
he would not trade away from them, because they are "not very relevant". A reversal off a low *is* trusted
because it has "valid separation" from the previous low. He says plainly: "I don't have a mechanical
reason to say … this is valid separation". It comes from experience and discernment.
**Example:** price reverses off the separated low and then trades through the high. No levels are given.
**Hygiene:** "I went too quick through it", so part of the walkthrough is not in the audio.
**Library:** this repeats `relevant-swing-separation` and `relevant-swings-separation`. It confirms again that there is
no numeric separation threshold.

## Using Continuation Candle Closures for Relative Strength (HIIxLzC1atE, 47 s)
**Taught:** relative strength read from the closure of the candle that should confirm a bearish CISD.
On one chart the candle "closes below, validating this change in the state of delivery". On the
other chart price "can't close below that level". The asset that closed below is weaker. Here that is
"gold GBP", which is taken to mean XAUGBP, and gold (XAUUSD) is "a slight bit stronger". Both then continue lower.
His general point is that the closures of the candles that create the CISD or the continuation
usually show you the relative strength.
**Hygiene:** the transcript stops mid-sentence ("…relative strength or"). "Gold GBP" is a guess from the caption.
**Library:** the closure method is already in `relative-strength-asset-selection` (Tool 3, and the
opposing-candle-series wording). **New:** this is the first time in the corpus that the method is
applied to gold, as XAUUSD against XAUGBP. That pairing is a strength filter that could be tested directly on XAUUSD.
Note that the weaker asset was not shown to pay more, since both moved lower.

## EURGBP Daily Candle Closures for Relative Strength (N8Wp_7vHYTk, 57 s)
**Taught:** this starts from "a sweep with a candle 2 closure" (the caption says "candle to closure").
With a bullish dollar, look for the most bearish foreign currency. EURGBP's daily candle is clearly bearish,
which means the euro is weak, and it should keep falling "as long as it remains in respect to 0.5 of this range".
So EURUSD is the pair to short. The cross-check is that EURUSD has a bearish daily closure while GBPUSD's
daily candle is bullish. On the lower timeframe he looks for a fractal model: a CISD, then price opens, then it sweeps a consolidation high.
That sweep is "where we'd want to see that wick of the daily candle form". Price then continues lower.
**Library:** this repeats `eurgbp-relative-strength-cross` and `dollar-gate-for-fx`. **New detail:** the EURGBP
read holds only while price respects 0.5 of the cross's daily range. This is `half-wick-respect`
applied to the cross itself, and the library's cross entry did not have it.

## A Loss Isn't a Bad Trade If You Followed Your System (ZhFAiV26Tqg, 84 s)
**Taught (psychology):** this is a Q&A answer. A loss is not the same as a bad trade, and a bad trade means not following
your rules. You need n to approach infinity before your results form a bell curve. Three losses do not make your win rate zero.
Fear leads to undertrading. If a setup meets your model, take it, and treat trading as data collection.
**Library:** this repeats `loss-is-not-a-bad-trade` almost word for word. It looks like a clip of m8xcjkOuBHU. Untestable.

## Midweek Reversal Profile: Expansion → Retracement → Expansion (lffsulC_Np4, 59 s)
**Taught:** Wednesday takes out a small high. There is no candle 2 closure ("candle to closure" in the caption), only a
"reversal looking candle". He could look for lower-timeframe confirmation but would rather have a closure.
He turns down a Thursday trade as "not super clean". Instead he waits for Thursday's daily candle to close.
A candle 3 closure plus a CISD confirms that Wednesday formed the high of the week, and he takes the
continuation short on Friday. He describes the week as expansion, then retracement, then a new expansion, and says "Monday,
Tuesday, Wednesday, they all oppose the weekly range".
**Library:** this repeats the fallback path of `midweek-reversal-week`, and the declined Thursday trade is
already listed in its ambiguities. The only new item is in the wording. Saying that Mon to Wed *all* oppose the range does not match
the library rule that only Monday and Tuesday oppose the bias. It is recorded as an ambiguity.

## Look for Price to React at Relevant Swings (vHvYT6bmaQM, 35 s)
**Taught:** do not look for a reversal off a gap that sits "so close to this high", because the
high is the relevant level. After that high is taken out, re-mark the relevant highs and lows. These are the levels to
"trade back into the range" or the other way. The low is relevant because "there is a lot of separation" from
the previous low, so he would look for a reaction there.
**Library:** this repeats `relevant-swing-separation` and `trade-away-from-manipulation`.

---

## Cross-video summary

**What is genuinely new (small):**
- XAUUSD against XAUGBP as the gold relative-strength pair. The test is which one closes through the CISD level.
  This was added to `relative-strength-asset-selection` (new_claim).
- The EURGBP cross read is held only while price respects 0.5 of the cross's daily range.
  This was added to `eurgbp-relative-strength-cross` (new_claim).

**Repeats the library (new sources only):** `relevant-swing-separation` (91I_Pq2pZ2Y and vHvYT6bmaQM, which say
outright that there is no mechanical rule for separation), `loss-is-not-a-bad-trade` (ZhFAiV26Tqg), `midweek-reversal-week`
(lffsulC_Np4, with one wording conflict added as an ambiguity). The SMT reading in 3ihK4q3axfI is already covered by
`relative-strength-asset-selection` and `smt-divergence`.

**No new concept ids were created.** This is consistent with the library being saturated.

**Hygiene across the unit:** there are no timestamps and no spoken levels. The assets are often not named.
"Candle to closure" is a caption error for "candle 2 closure". The HIIxLzC1atE transcript is truncated.
