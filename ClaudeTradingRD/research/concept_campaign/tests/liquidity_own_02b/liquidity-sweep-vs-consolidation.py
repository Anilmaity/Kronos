"""liquidity-sweep-vs-consolidation — after a level is taken, an immediate V-shaped
displacement back through it marks a real sweep (trade the reversal); a lethargic reaction
marks consolidation. gate_test: V-shape vs lethargic, on the same reversal book.

Fixed BEFORE the first run.
15m bars. Level = latest confirmed 2/2 swing high/low; event = the FIRST bar j that trades
through it. Reaction window = bars j, j+1, j+2 ('he prefers one, two, maybe three' candles);
decide at the close of j+2 for every event, V or not.
Baseline trade (all events): opposite the swept side, enter next M1 open after j+2 close,
stop beyond the sweep extreme (max high / min low over j..j+2), 2R, 10 bars trading time.
Gate v_shape (high-sweep case; lows mirrored), threshold_fits displacement magnitude applied
over the 3-bar window with pre_range = high-low range of the 3 bars before j:
   close[j+2] < level                         (structural: closed back through, grade A)
   (level - close[j+2]) / pre_range >= 0.65   (distance, d)
   window range / pre_range >= 1.5            (range, r)
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/liquidity_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
from _common import swings, last_confirmed_level

CID = "liquidity-sweep-vs-consolidation"
TF = "15min"
W = 3
R_CUT, D_CUT = 1.5, 0.65
RR = 2.0
HOLD = "150min"


def detect(m1):
    b = cl.build_bars(m1, TF)
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    n = len(b)
    ish, isl = swings(b)
    sh, sh_id = last_confirmed_level(ish, h)
    sl, sl_id = last_confirmed_level(isl, l)
    rows = []
    for d, through, sid, lvl in ((-1, h > sh, sh_id, sh), (1, l < sl, sl_id, sl)):
        j_all = np.flatnonzero(through & (sid >= 0))
        if not len(j_all):
            continue
        first = pd.Series(j_all).groupby(sid[j_all]).min().to_numpy()
        first = first[(first >= W) & (first + W - 1 < n)]
        for j in first:
            e = j + W - 1
            pre = h[j - W:j].max() - l[j - W:j].min()
            wh, wl = h[j:e + 1].max(), l[j:e + 1].min()
            if not pre > 0:
                continue
            L = lvl[j]
            if d < 0:
                back = c[e] < L
                dist = (L - c[e]) / pre
                stop = wh
            else:
                back = c[e] > L
                dist = (c[e] - L) / pre
                stop = wl
            if (stop - c[e]) * d >= 0:          # stop not beyond the close: no risk defined
                continue
            v = bool(back and dist >= D_CUT and (wh - wl) / pre >= R_CUT)
            rows.append((e, d, stop, v))
    if not rows:
        return pd.DataFrame(columns=["decision_time", "available_at", "direction", "stop_px", "rr", "v_shape"])
    r = pd.DataFrame(rows, columns=["e", "d", "stop", "v"]).sort_values("e", kind="stable")
    close = pd.DatetimeIndex(b["close_time"].to_numpy()[r["e"].to_numpy()]).tz_convert("UTC")
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": r["d"].to_numpy().astype(int), "stop_px": r["stop"].to_numpy(),
                         "rr": RR, "v_shape": r["v"].to_numpy().astype(bool)})


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["v_shape"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "v_shape", mask_available_at="decision_time", max_hold=HOLD,
                       hold_basis="bars")
    rules = ["15m bars; level = latest confirmed 2/2 swing high/low; event = first bar j trading through it",
             "decide at the close of bar j+2 (3-candle reaction window) for every event",
             "baseline: trade opposite the swept side, stop beyond the window's sweep extreme, 2R, 10 bars trading time",
             "gate v_shape: close[j+2] back through the level AND (distance back / pre-range) >= 0.65 AND window range / pre-range >= 1.5 (pre-range = 3 bars before j)"]
    params = {"tf": TF, "swing": "2/2", "window_bars": W, "r_cut": R_CUT, "d_cut": D_CUT,
              "rr": RR, "max_hold": HOLD, "hold_basis": "bars"}
    src = {"tf": "declared-before-run: 15m, first ltf of the concept",
           "swing": "phase3: 2/2 fractal swings",
           "window_bars": "corpus: v-shape-reversal-speed 'he prefers one, two, maybe three' candles (method_spec §4.2)",
           "r_cut": "threshold_fits: displacement magnitude r=1.5",
           "d_cut": "threshold_fits: displacement magnitude d=0.65",
           "rr": "phase3: locked 2R target (§1.13)",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "hold_basis": "declared-before-run: trading-time holds (trap 7)"}
    notes = (f"v_shape fires on {ev['v_shape'].mean():.1%} of {len(ev)} sweeps. Magnitude cut uses N=3 "
             "(the corpus's speed preference) rather than the fit's N=4; the fit reports N insensitive 2-8.")
    p = cl.write_result(CID, None, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "exposure_bars", "ties")})
    print(p)
