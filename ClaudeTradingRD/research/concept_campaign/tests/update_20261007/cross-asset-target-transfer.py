"""cross-asset-target-transfer, reading u1007a: the DXY -> GBP/EUR exit transfer.

The new claim (KBJAGgkXdeI) is an FX version of the rule. He is bullish the dollar into a
daily gap on the DXY chart, and that frames bearish continuations on EURUSD / GBPUSD (he
prefers GBP, entered off a 5m sweep). A GBP/EUR short is exited when DXY tags that gap, or
on an expansion day held to the close. Every element lives on instruments the campaign does
not hold. The probe below lists the correlate files: XAG and EURUSD at H1/D1 only. There is
no dollar-index series and no GBP series, and EURUSD has no intraday resolution finer than H1.

Rejected substitutions (vault: XAUUSD Data Inventory, Backtest Methodology Traps 7):
- inverted EURUSD as "DXY": the vault forbids calling it DXY, and for a EUR short it turns
  the exit into the traded asset's OWN level, which erases the cross-asset content;
- gold as the traded leg: the source never applies the dollar target to gold (in the same
  stream he says he uses no dollar correlation for indices), and the gold/silver analogue
  of the general rule is already tested as readings a (NEGATIVE) and b (NULL). Re-running
  that analogue with a EUR proxy would repeat it, not test the new claim.
The measurable ("R of GBP shorts exited at DXY target vs at the close") is also a variant-
vs-variant exit comparison, which the harness has no test for.
"""
import sys
from pathlib import Path
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

# probe, not inference (trap 7): which instruments does the campaign actually hold?
DATA = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper")
held = sorted(p.stem for p in DATA.glob("*.parquet"))
assert not any(k in s for s in held for k in ("dxy", "usdx", "gbp")), held
assert not any(s.startswith("eur_") and not s.split("_")[1].startswith(("h1", "d1")) for s in held), held

p = cl.write_untestable(
    "cross-asset-target-transfer",
    "needs a DXY series (to mark its daily gap and detect the tag) and intraday GBPUSD/EURUSD "
    f"5m/M1 (the traded shorts). Probe of the campaign data dir finds only {held}: no dollar "
    "index, no GBP, EURUSD at H1/D1 only. Inverted EURUSD is not DXY (vault data inventory) and "
    "as the exit for a EUR short it becomes the traded asset's own level, erasing the cross-asset "
    "claim. Gold is not the instrument the claim is about; its silver analogue is readings a/b",
    reading="u1007a",
    params_source={"source": "corpus: KBJAGgkXdeI 'dollar like I said is reaching for daily gap "
                   "there. But if you're short into pound or euro I prefer pound then you can "
                   "hold until the dollar hits that level a good profit taking target' / 'can "
                   "generally hold till the close' / 'that would frame any sort of bearish "
                   "continuation on euro or pound'"},
    script=__file__,
    notes="Rerun with vault context (2026-10-07). Gold-traded, silver-correlate analogue of the "
          "general target-transfer rule already tested as readings a (NEGATIVE, diff -0.084R) and "
          "b (NULL); not repeated here. This reading records only the new DXY->FX claim. Same "
          "data limit as dxy-yields-smt-pair (UNTESTABLE).")
print(p)
