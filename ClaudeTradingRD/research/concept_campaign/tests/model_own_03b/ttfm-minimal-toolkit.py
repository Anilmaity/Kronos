"""ttfm-minimal-toolkit — UNTESTABLE: an inventory of what is on the speaker's chart."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("Scope/inventory statement with no directional claim about price: it lists the chart objects he "
          "keeps (highs/lows, FVG, CISD, SMT, EQ, OHLC profile overlays, watermarks, a sessions indicator) and "
          "the tools he dropped, and the corpus itself flags the refusals as personal preference, not claims that "
          "the tools fail ('use whatever you want as long as you follow rules'). Its only 'measurable' ('a detector "
          "restricted to the five primitives vs one with additional arrays') is a no-difference hypothesis with an "
          "unspecified comparison set, which the locked verdict (claim +/-) cannot express; the individual kept "
          "primitives (CISD, FVG, SMT, EQ, protected swing) and dropped tools (killzones, OTE, CRT, breakers, macros) "
          "are each tested under their own concept ids. Chart layout/watermark/platform items are not price rules.")

if __name__ == "__main__":
    print(cl.write_untestable("ttfm-minimal-toolkit", REASON, script=__file__,
                              notes="Five definition variants (incl. an early-era template video) all describe tooling, not a trade rule."))
