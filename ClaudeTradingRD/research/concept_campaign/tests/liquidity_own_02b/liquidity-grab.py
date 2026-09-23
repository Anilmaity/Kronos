"""liquidity-grab — 'a failure to displace over structure': price reaches over an old high
(under an old low), produces no close beyond it, comes back in -> look to the opposite side of
the range for the draw. trade_test.

Fixed BEFORE the first run.
1h bars (UTC hours). Old high/low = latest confirmed 2/2 fractal swing (confirmed 2 bars later).
Grab (bearish): the FIRST bar to trade above that swing high closes at or below it (no close
beyond = no displacement; a first bar that closes beyond is a shift, not a grab, and is not an
event). Decide at that bar's close; short at the next M1 open; stop at the grab bar's high;
target = the opposite side of the range = latest confirmed swing low (must be below the close).
Mirrored for lows. max_hold 10 bars (10h) trading time.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
from _common import swings, last_confirmed_level

CID = "liquidity-grab"
TF = "1h"
HOLD = "10h"


def detect(m1):
    b = cl.build_bars(m1, TF)
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    ish, isl = swings(b)
    sh, sh_id = last_confirmed_level(ish, h)
    sl, sl_id = last_confirmed_level(isl, l)
    js, ds = [], []
    for d, through, sid, grab in ((-1, h > sh, sh_id, (c <= sh) & (sl < c)),
                                  (1, l < sl, sl_id, (c >= sl) & (sh > c))):
        j_all = np.flatnonzero(through & (sid >= 0))
        if not len(j_all):
            continue
        first = pd.Series(j_all).groupby(sid[j_all]).min().to_numpy()
        j = first[grab[first]]
        js.append(j); ds.append(np.full(len(j), d))
    j = np.concatenate(js).astype(int) if js else np.array([], int)
    d = np.concatenate(ds).astype(int) if ds else np.array([], int)
    o = np.argsort(j, kind="stable"); j, d = j[o], d[o]
    close = pd.DatetimeIndex(b["close_time"].to_numpy()[j]).tz_convert("UTC") if len(j) \
        else pd.DatetimeIndex([], tz="UTC")
    return pd.DataFrame({"decision_time": close, "available_at": close, "direction": d,
                         "stop_px": np.where(d < 0, h[j], l[j]),
                         "target_px": np.where(d < 0, sl[j], sh[j])})


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=HOLD, hold_basis="bars")
    rules = ["1h bars; latest confirmed 2/2 swing high/low",
             "grab = the first bar trading through the swing closes back inside (no close beyond)",
             "trade toward the opposite side: enter next M1 open after the grab bar close",
             "stop at the grab bar extreme; target the latest confirmed opposite swing; 10 bars trading time"]
    params = {"tf": TF, "swing": "2/2", "max_hold": HOLD, "hold_basis": "bars",
              "target": "latest confirmed opposite swing", "stop": "grab bar extreme"}
    src = {"tf": "declared-before-run: 1H, from the concept's htf list (4H/1H); 1H for sample size",
           "swing": "phase3: 2/2 fractal swings (locked swing definition)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "hold_basis": "declared-before-run: trading-time holds (trap 7)",
           "target": "corpus: ynFA6E3qHj0 detection rule 'Look to the opposite side of the range for the draw'",
           "stop": "declared-before-run: beyond the grab extreme (the level whose reclaim would make it a shift)"}
    notes = ("'No large aggressive candle closes beyond' is read with threshold_fits' grade-A structural gate: "
             "any close beyond = displacement. The invalidation (a LATER aggressive close beyond -> MSS) is "
             "covered by the stop at the grab extreme.")
    p = cl.write_result(CID, None, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "exposure_bars", "ties")})
    print(p)
