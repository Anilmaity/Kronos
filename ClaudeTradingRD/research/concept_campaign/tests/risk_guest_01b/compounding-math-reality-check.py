"""compounding-math-reality-check (guest: STRATalorian) -> UNTESTABLE (arithmetic)."""
import sys, math
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

# Arithmetic check of the quoted ladder (for the notes only; not a market test).
days = {m: math.log(m) / math.log(1.01) for m in (10, 100, 1000, 10000, 100000)}
chk = ", ".join(f"x{m}: {d:.1f} d" for m, d in days.items())
REASON = ("An arithmetic reductio about compounding (1%/day ladder, 250 trading days/year) and "
          "an evidentiary caution about P&L screenshots. It makes no claim about price "
          "behaviour, so there is no event, gate or level to test against XAUUSD OHLC.")
cl.write_untestable("compounding-math-reality-check", REASON, script=__file__,
                    notes=("Arithmetic verified: ln(multiple)/ln(1.01) gives " + chk +
                           " -> the quoted 232/463/695/926/~1160 days are exactly x10..x100000, "
                           "i.e. a $1,000 starting balance (the unstated start in yaml ambiguity 1)."))
print(chk)
