"""cl.bars() returns the SAME memoised DataFrame to every caller in the process. An
agent that edits its copy in place (here: re-stamping availability at bar start, a
common mistake for "use the daily open") silently changes what prior_hilo returns for
the rest of the process: 'prior day high' becomes TODAY's high, read mid-session."""
import sys; sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import pandas as pd
import concept_lab as cl
t = pd.DatetimeIndex([pd.Timestamp("2020-03-12 14:00", tz="UTC")])
before = cl.prior_hilo(t, "1D")[["high", "available_at"]]
d = cl.bars("1D")                          # agent's "own" frame
d["close_time"] = d.index                  # agent-local edit ...
after = cl.prior_hilo(t, "1D")[["high", "available_at"]]
print("PDH before edit:\n", before, "\nPDH after an unrelated in-place edit:\n", after)
print("same object:", cl.bars("1D") is d)
td = cl.trading_day(t)[0]
print("today's session high (full day):", cl.bars("1D").set_index("trading_day").loc[td, "high"] if "trading_day" in d else None)
