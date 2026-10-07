"""Does the u1007a 'yes' effect live on daily extremes set in the 18:00 NY reopen hour (gap artefact)?
For each row: is the stop (running extreme) the low/high of the day's FIRST 1h bar?
Split gate diff (harness adj = R - matched control) by that flag. Ledger redirected."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["CONCEPT_LAB_LEDGER"] = str(HERE / "wtt_u1007a_impl_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402
import concept_lab as cl      # noqa: E402

ev = pd.read_pickle(HERE / "wtt_u1007a_impl_events.pkl")
h1 = cl.bars("1h")
td = np.asarray(cl.trading_day(pd.DatetimeIndex(h1.index)))
first = pd.DataFrame({"td": td, "lo": h1.low.to_numpy(), "hi": h1.high.to_numpy()}).groupby("td").first()
r = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold="10h", keep_trades=True)
tr = r["_trades"]
tr["adj"] = tr.net_R - tr.ctrl_mean_R
tr["td"] = np.asarray(cl.trading_day(pd.DatetimeIndex(tr.decision_time)))
f = first.reindex(pd.DatetimeIndex(tr.td))
tr["reopen_ext"] = np.where(tr.direction.to_numpy() == 1, f.lo.to_numpy() == tr.stop.to_numpy(),
                            f.hi.to_numpy() == tr.stop.to_numpy())
tr = tr[np.isfinite(tr.adj)]
print(tr.groupby(["reopen_ext", "gate"]).adj.agg(["mean", "count"]).round(4))
for flag in (True, False):
    s = tr[tr.reopen_ext == flag]
    print(f"reopen_ext={flag}: gate diff {s[s.gate].adj.mean() - s[~s.gate].adj.mean():+.4f} "
          f"(yes n={int(s.gate.sum())})")
