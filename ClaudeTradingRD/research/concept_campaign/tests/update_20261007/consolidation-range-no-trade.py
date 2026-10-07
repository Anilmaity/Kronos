"""consolidation-range-no-trade, reading u1007a: the cross-asset 'reset the chop' gate.

The new claim (9H15ZZvaKPQ, live NY open) is about the US index futures NQ/ES/YM on 5m/15m
charts: while their relative strength flips minute to minute ("YM just got stronger. You see
that?"), it is chop and not traded; it resets when ONE of those assets runs out a low.
The rule needs (a) the named index futures, or at least three correlated assets, at sub-hourly
resolution so a strength flip is visible, and (b) a 'run out a low' trigger on any of them.

Data probe (2026-10-07, not inferred from file extents, per vault trap 7):
  - NQ/ES/YM (or any index future): no file anywhere in the workspace.
  - Gold correlates at H1 only: XAG_USD 2010-01-03 ->, XAU_EUR / XAU_GBP 2015-12-01 -> 2026-07-23.
  - Sub-hourly correlates: silver M15 2024-12-30 -> 2026-05-22 (market_structure/data/
    cont_xag_M15.parquet) and silver ticks 2025-01 -> 2026-05 (KronosStrategies/.history_data);
    < 2 years and entirely inside H2 (2021->), so the H1/H2 rule cannot be met.
A gold-family transfer at H1 would replace both the instruments and the timeframe and need
unsourced choices for 'strength', 'rotation', 'chop' and 'which low' (the draft's own ambiguity),
so it would be a reconstruction, not this claim. Same treatment as the sibling sub-hourly
cross-asset claims today (smt-divergence u1007b, cross-asset-reversal-confirmation live_01/08).
The single-instrument range stand-aside part is already covered by readings a (NULL) and b
(UNDERPOWERED) and is not re-tested.

AUDIT 2026-10-07: verdict unchanged; the reason previously said 'harness has XAUUSD M1 only',
which is false (H1 correlates exist). Reason corrected to the probed limit.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("needs the index futures NQ/ES/YM (or >=3 correlated assets) at sub-hourly resolution to see "
          "minute-scale strength rotation and which asset runs out a low; probe 2026-10-07: no index "
          "data in the workspace, gold correlates (XAG_USD, XAU_EUR, XAU_GBP) only at H1, sub-hourly "
          "silver only 2024-12 -> 2026-05 (< 2 years, all in H2)")

p = cl.write_untestable(
    "consolidation-range-no-trade",
    REASON,
    reading="u1007a",
    params_source={"source": "corpus: 9H15ZZvaKPQ 'Normally we want one of these assets to run "
                   "out a low because then that kind of resets the chop' / 'when the strengths "
                   "are kind of jumping around'"},
    script=__file__,
    notes="AUDIT 2026-10-07 (vault context): verdict unchanged; reason corrected - the earlier "
          "'harness has XAUUSD M1 only' was a data limit not taken from a probe (trap 7): H1 "
          "correlates exist (XAG 2010-, XAU_EUR/XAU_GBP 2015-12-). Gold-only analogue "
          "(single-instrument range stand-aside) already tested as readings a (NULL) and b "
          "(UNDERPOWERED); not re-tested.")
print(p)
