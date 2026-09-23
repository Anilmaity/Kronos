"""order-block-requires-bos (guest: AP, gjoRPszj-Qk) -> gate_test.

Claim: only the candle that PRODUCED the break of structure (closed above the previous
swing high, bullish) is a valid order block; the generic 'last opposing candle' is not.
Measurable: "hit rate of order blocks that satisfy the break-of-structure requirement
versus those that do not". claim '+': returns into the BOS candle beat returns into the
generic last-opposing-candle block of the same break.

Reading (declared before the first run):
  * 15m bars; swings fractal 2/2 (known two bars after the swing); a break of structure =
    the first 15m close beyond a swing high (bullish) / low (bearish) within 96 bars of the
    swing's confirmation; swings broken by one bar = one break.
  * BOS order block (mask True): the breaking candle itself, if it closed in the break
    direction (bullish: close > open).
  * Generic order block (mask False): the last opposing candle (bullish: close < open)
    between the most recent broken swing bar and the breaking bar.
  * Entry, both arms (execution: 'on the return into the unmitigated order block'): a limit
    at the block's near body edge (bullish: body top) resting from the break bar's close for
    48 bars (12h), cancelled if 2R trades first; the touch minute must not also trade
    through the block's far wick extreme (the stop, 'beyond the block'); entry at the next
    M1 open; 2R; hold 10 bars = 150 min.
  * cluster = the break id (both arms come from one break).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _common import swings22, m1_arrays, from_ns, ONE_MIN  # noqa: E402

CID = "order-block-requires-bos"
TF = "15min"
WATCH = 96
FILL = pd.Timedelta("12h")
RR = 2.0
MAX_HOLD = "150min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "is_bos_ob",
        "break_id", "lim_px"]


def _bull_breaks(o, h, l, c, n):
    """Bullish breaks of swing highs; returns (j, s_last) per breaking bar."""
    sh, _ = swings22(h, l)
    brk = {}
    for i in np.flatnonzero(sh):
        j0, j1 = i + 3, min(n, i + 3 + WATCH)
        if j0 >= j1:
            continue
        hit = np.flatnonzero(c[j0:j1] > h[i])
        if len(hit):
            j = j0 + int(hit[0])
            brk[j] = max(brk.get(j, -1), i)
    return sorted(brk.items())


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    if len(b) < 10:
        return pd.DataFrame(columns=COLS)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = b["close_time"].values.astype("datetime64[ns]").astype(np.int64)
    n = len(b)
    mt, MH, ML = m1_arrays(m1)
    out = []
    for sgn, (oo, hh, ll, cc) in ((1, (o, h, l, c)), (-1, (-o, -l, -h, -c))):
        # mirrored M1 for bearish: high' = -low, low' = -high
        mh, ml = (MH, ML) if sgn == 1 else (-ML, -MH)
        for j, s in _bull_breaks(oo, hh, ll, cc, n):
            blocks = []
            if cc[j] > oo[j]:
                blocks.append((True, cc[j], ll[j]))          # BOS candle: body top, wick low
            opp = np.flatnonzero(cc[s:j] < oo[s:j])
            if len(opp):
                g = s + int(opp[-1])
                blocks.append((False, oo[g], ll[g]))         # last down candle: body top, low
            a = np.searchsorted(mt, ct[j], "left")
            e = np.searchsorted(mt, ct[j] + FILL.value, "left")
            if a >= e:
                continue
            for is_bos, ent, stp in blocks:
                risk = ent - stp
                if not (risk > 0):
                    continue
                tgt = ent + RR * risk
                seg_l, seg_h = ml[a:e], mh[a:e]
                f = np.flatnonzero(seg_l <= ent)
                if not len(f):
                    continue
                k = int(f[0])
                t = np.flatnonzero(seg_h[:k] >= tgt)
                if len(t):
                    continue                                   # ran to target first: cancelled
                if seg_l[k] < stp:
                    continue                                   # touch minute through the stop
                out.append((int(mt[a + k]), sgn, stp * sgn, is_bos, int(ct[j]) * sgn,
                            ent * sgn))
    if not out:
        return pd.DataFrame(columns=COLS)
    o_ = pd.DataFrame(out, columns=["t", "direction", "stop_px", "is_bos_ob", "break_id", "lim"])
    dec = from_ns(o_["t"].to_numpy()) + ONE_MIN
    ev = pd.DataFrame({"decision_time": dec, "available_at": dec,
                       "direction": o_["direction"].astype(int).to_numpy(),
                       "stop_px": o_["stop_px"].to_numpy(float), "rr": RR,
                       "is_bos_ob": o_["is_bos_ob"].astype(bool).to_numpy(),
                       "break_id": o_["break_id"].astype(np.int64).to_numpy(),
                       "lim_px": o_["lim"].to_numpy(float)})
    return ev.sort_values(["decision_time", "break_id", "is_bos_ob"]).reset_index(drop=True)[COLS]


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}_w{WATCH}_12h", lambda: detect(cl.load_m1()))
    print(len(ev), ev["is_bos_ob"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "is_bos_ob", mask_available_at="decision_time", max_hold=MAX_HOLD,
                       cluster="break_id")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap", "complement"):
        print(k, res.get(k))
    op = {"rules": [
        "15m bars; fractal 2/2 swings; break = first 15m close beyond a swing within 96 bars",
        "BOS block = the breaking candle (must close in the break direction); generic block = "
        "last opposing candle between the most recent broken swing and the break",
        "limit at the block's near body edge from the break close for 12h, cancelled if 2R "
        "trades first; stop at the block's far wick extreme; touch minute through the stop "
        "skipped; entry next M1 open; 2R; hold 150 min",
        "gate_test: BOS-candle rows vs generic-block rows, control-adjusted, clustered by break"],
        "params": {"tf": TF, "watch_bars": WATCH, "fill_window": "12h", "rr": RR,
                   "max_hold": MAX_HOLD, "swing": "fractal 2/2", "entry": "near body edge",
                   "stop": "block far wick extreme"}}
    src = {"tf": "declared-before-run: 15m from the concept's ltf list (htf 1H); fractal: true",
           "watch_bars": "declared-before-run: a swing is live for 96 bars (24h)",
           "fill_window": "declared-before-run: limit rests 48 entry bars",
           "rr": "declared-before-run: target 'the GB level the block coincides with' needs the "
                 "GB fib anchor; 2R (phase3 primary)",
           "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13)",
           "swing": "phase3: swing fractal left=2, right=2 (preregistration 1.16)",
           "entry": "corpus: gjoRPszj-Qk execution 'on the return into the unmitigated order "
                    "block' -> first touch of the body's near edge (declared-before-run)",
           "stop": "corpus: gjoRPszj-Qk execution 'Beyond the block' -> the block's wick extreme"}
    notes = ("The GB-level coincidence (rule 4) and the undefined CSS / S&D variants are not "
             "tested. BOS-candle entries at its close fill almost immediately (a market entry "
             "after the break with the stop at the break candle's far extreme).")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
