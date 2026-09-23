"""smt-two-chart-layout — a TradingView pane/sync configuration for SEEING SMT. Recorded
UNTESTABLE: it is charting-UI procedure with no market claim of its own."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("Charting-UI procedure, not a market claim: the rules are TradingView settings (symbol sync off, "
          "interval/crosshair/time sync on, data-range sync off, a saved layout, watch-list arrow keys). "
          "Their only substantive content, 'SMT = one instrument took the extreme and the other did not, on "
          "the same candle', is the timestamp-aligned SMT definition that every OHLC SMT test already uses "
          "(tested in this batch as smt-reversal-continuation-double a/b and gold-correlated-assets). The "
          "concept's own measurable ('how often a visually-spotted SMT survives a strict same-timestamp "
          "check') needs a record of visually-spotted SMTs, which does not exist; the corpus has no dated "
          "chart calls (RESUME phase 2: zero of 56 narrated calls tie to a bar).")

if __name__ == "__main__":
    print(cl.write_untestable("smt-two-chart-layout", REASON, script=__file__))
