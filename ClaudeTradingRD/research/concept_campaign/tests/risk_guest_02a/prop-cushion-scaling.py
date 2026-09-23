"""prop-cushion-scaling — UNTESTABLE (batch risk_guest_02a)."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = "Prop-firm account-ladder advice (pass an Apex evaluation, trade micros to a ~$2,000 cushion, step to ~20 micros then 1-5 ES). It is sizing arithmetic tied to a specific firm's drawdown rules and the trader's 'confidence in the setup'; no entry, exit or setup is defined, per-trade R on gold OHLC is unchanged by the ladder, and its measurables (account survival per size step) need prop-account equity records we do not have."

if __name__ == "__main__":
    p = cl.write_untestable("prop-cushion-scaling", REASON, script=__file__)
    print(p)
