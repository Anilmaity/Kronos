"""excluded-tooling — UNTESTABLE: a list of tools deliberately left out of the model."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("A list of exclusions (kill zones, macros, midnight open, breakers, IFVG, Silver Bullet, CRT, OTE, "
          "order flow/footprint/DOM/TPO, seasonals, intraday fundamentals, 'time distortion', Sunday SD projections, "
          "CFDs, the Russell, scalping) that asserts no direction for price: 'an implementation should contain none "
          "of these' is a design choice, and its only measurable ('how many candidate signals depend on an excluded "
          "tool') is a count, not an outcome. Testing 'excluding X costs nothing' is a no-effect hypothesis the "
          "locked +/- verdict cannot confirm; each excluded tool with a price rule is tested under its own concept "
          "id (killzones, macros, optimal-trade-entry, breaker-block, ...). Several items need data the harness does "
          "not have (order flow, DOM, TPO, footprint, news content) or are venue/instrument choices (futures vs CFD, "
          "no Russell) that OHLC on one gold series cannot decide.")

if __name__ == "__main__":
    print(cl.write_untestable("excluded-tooling", REASON, script=__file__,
                              notes="Scope statement; see ttfm-minimal-toolkit for the positive list."))
