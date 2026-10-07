"""thursday-counter-week, reading u1007a: the ES/NQ one-day-lead reclassification.

New claim (wbhjwy2A3UU, a 56 s Short, "not a perfect example"): "if you use intermarket analysis
and take a look at ... ES or NQ here, you can see that reversal was formed on Wednesday. So, it's
actually a Thursday continuation of a midweek reversal ... you could also be looking for a
reversal on this day as the other assets reversed on Wednesday."

The relaxation ("Thursday need not take out Wednesday's high") and the Friday targets (weekly open,
week's opposite extreme) are already in the library entry and were tested as readings a/b
(UNDERPOWERED, n=35 / 52). Only the cross-asset lead is new, and its trigger is a reversal in the
equity-index futures ES/NQ. The probe below lists every series the campaign holds: XAU M1, plus
XAG and EUR_USD at H1/D1. There is no equity-index series.

Rejected substitutions (vault: XAUUSD Data Inventory, Backtest Methodology Traps 7, Concept
Campaign bounds "correlates were H1 silver/EURUSD only"):
- silver as "the other assets": the source names ES/NQ, and his own library entry
  intermarket-correlation-not-used confines correlation to within a class (YM/ES/NQ triad; gold vs a
  correlated metal). A gold/silver one-day lead would be a different claim, and the same-time
  gold/silver version is already cross-asset-reversal-confirmation u1007a;
- gold as the traded asset: the transcript never names the traded asset (draft ambiguity 1), and
  the triad wording implies another index, so gold-vs-ES is not what he claims either.
Fetching an OANDA index CFD (SPX500_USD / NAS100_USD) would be new data outside the locked campaign
inventory, so it is not done here.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

# probe, not inference (trap 7): which instruments does the campaign actually hold?
DATA = Path("/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper")
held = sorted(p.stem for p in DATA.glob("*.parquet"))
INDEX_KEYS = ("es", "nq", "spx", "nas", "us500", "us100", "ym", "us30", "ndx")
assert not any(s.split("_")[0] in INDEX_KEYS for s in held), held

p = cl.write_untestable(
    "thursday-counter-week",
    "the new claim's trigger is a Wednesday reversal in the equity-index futures ES/NQ, transferred "
    f"one day later to the traded asset. Probe of the campaign data dir finds only {held}: no "
    "equity-index series. Silver is not the named correlate (his intermarket-correlation-not-used "
    "entry keeps correlation within a class: YM/ES/NQ, or gold vs a metal), and the traded asset in "
    "the example is unnamed. The relaxation and Friday-target parts are readings a/b",
    reading="u1007a",
    params_source={"source": "corpus: wbhjwy2A3UU 'take a look at, you know, ES or NQ here, you "
                   "can see that reversal was formed on Wednesday' / 'looking for a reversal on "
                   "this day as the other assets reversed on Wednesday'"},
    script=__file__,
    notes="Rerun with vault context (2026-10-07). Prior readings a (UNDERPOWERED, n=35) and b "
          "(UNDERPOWERED, n=52) already cover the Mon-Wed run, Thursday counter and Friday weekly-open "
          "target; not repeated. Same data limit as cross-asset-target-transfer u1007a (UNTESTABLE). "
          "Testable later only if an ES/NQ (or SPX500/NAS100 CFD) daily series is added.")
print(p)
