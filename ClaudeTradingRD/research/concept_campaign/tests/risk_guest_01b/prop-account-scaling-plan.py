"""prop-account-scaling-plan (guest: Trader Kane) -> UNTESTABLE."""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl

REASON = ("Capital/campaign structure across many funded prop accounts, not a chart rule: its "
          "claims are about trailing-drawdown mechanics, payout schedules (firm-specific, firm "
          "name unrecoverable) and account count, none of which exist in XAUUSD OHLC. The only "
          "chart-adjacent parts are unoperationalisable as stated: phase-1 'trade aggressively, "
          "grab impulsive expansion moves' has no entry, stop or size; phase-2 'close once it is "
          "profitable enough, ~100 ticks' has no entry model and an undefined early-exit "
          "threshold (100 NQ/ES futures ticks has no stated gold equivalent). Testing it would "
          "mean inventing the entry and the exit threshold, i.e. testing our rule, not his.")
cl.write_untestable("prop-account-scaling-plan", REASON, script=__file__,
                    notes="guest concept; self-contradicts his 1%-base scaling matrix (yaml ambiguity 1).")
print("written")
