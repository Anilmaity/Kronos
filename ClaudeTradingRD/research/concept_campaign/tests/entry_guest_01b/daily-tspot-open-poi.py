"""daily-tspot-open-poi (DTR, guest) — gate_test.

Claim: after a daily C2 closure, the daily T-spot is a sufficient stand-alone point of
interest: a 5m unicorn taken where price engages it (in the C2 direction, while no
hourly candle has closed past it) trades better than unicorns elsewhere.

The T-spot is never defined in the DTR video (indicator output). The only OHLC
construction in the corpus is the own-voice `t-spot` example "it is just the
equilibrium" (method spec 3.7: "in one example, simply 'the equilibrium'"), i.e. 50%
of the C2 candle's range. That single reading is tested; the other construction
(overlap of 0.5 of the HTF wick with 0.5 of a CISD) needs the unexplained indicator
pairing and is not attempted.

Baseline book: every 5m unicorn (same as unicorn-candle-count-filter).
Gate: the most recent daily C2 closed before the formation began, has the unicorn's
direction, is <= 5 trading days old, no 1H close beyond its EQ has occurred by the
unicorn's completion, and the formation's sweep extreme reached the EQ.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _common import unicorn_book  # noqa: E402

CID = "daily-tspot-open-poi"
P = dict(tf="5min", W=48, fill_min=60, rr=2.0, max_hold="50min", tspot="C2 range EQ (0.5)",
         max_age_days=5, c2="prior-candle sweep, close back inside, reversal close",
         day_open_hour=18)


def tspots(m1):
    d = cl.build_bars(m1, "1D")
    h1 = cl.build_bars(m1, "1h")
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(d["close_time"])
    pl, ph = np.r_[np.nan, l[:-1]], np.r_[np.nan, h[:-1]]
    bull = (l < pl) & (c >= pl) & (c > o)
    bear = (h > ph) & (c <= ph) & (c < o)
    both = bull & bear            # swept both sides: ambiguous direction -> not a C2
    sgn = np.where(bull & ~both, 1, np.where(bear & ~both, -1, 0))
    k = np.flatnonzero(sgn != 0)
    eq = (h + l) / 2
    hc = h1["close"].to_numpy(float)
    hct = pd.DatetimeIndex(h1["close_time"]).as_unit("ns").asi8
    rows = []
    far = np.iinfo(np.int64).max
    ctn = ct.as_unit("ns").asi8
    for i in k:
        s = sgn[i]
        j0 = np.searchsorted(hct, ctn[i], "right")
        exp = ctn[i + P["max_age_days"]] if i + P["max_age_days"] < len(ctn) else far
        j1 = np.searchsorted(hct, exp, "right")
        seg = hc[j0:j1]
        bad = np.flatnonzero(s * (seg - eq[i]) < 0)
        inval = hct[j0 + bad[0]] if len(bad) else far
        rows.append((ctn[i], s, eq[i], min(inval, exp)))
    return pd.DataFrame(rows, columns=["active_from", "sgn", "eq", "end"])


def detect(m1):
    ev = unicorn_book(m1, tf=P["tf"], W=P["W"], fill_min=P["fill_min"], rr=P["rr"])
    ts = tspots(m1)
    gate = np.zeros(len(ev), bool)
    if len(ev) and len(ts):
        af = ts["active_from"].to_numpy()
        ta = pd.DatetimeIndex(ev["t_a"]).as_unit("ns").asi8
        cf = pd.DatetimeIndex(ev["confirm_time"]).as_unit("ns").asi8
        j = np.searchsorted(af, ta, "right") - 1        # latest C2 closed by formation start
        ok = j >= 0
        jj = np.clip(j, 0, None)
        s = ts["sgn"].to_numpy()[jj]
        eq = ts["eq"].to_numpy()[jj]
        end = ts["end"].to_numpy()[jj]
        dirn = ev["direction"].to_numpy()
        engaged = dirn * (ev["sweep_px"].to_numpy() - eq) <= 0
        gate = ok & (s == dirn) & (cf < end) & engaged
    ev["at_tspot"] = gate.astype(bool)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{P}", lambda: detect(cl.load_m1()))
    print(len(ev), ev["at_tspot"].sum())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "at_tspot", mask_available_at="confirm_time",
                       max_hold=P["max_hold"])
    op = {"rules": [
        "baseline: every 5m unicorn (breaker L1->H1->lower low->close through H1, zone = "
        "up-close bodies L1..H1, overlapping same-direction FVG), limit at the overlap's "
        "near edge for 60 min (cancelled if 2R trades first), stop at the breaker's far "
        "edge, 2R, 50 min time exit",
        "daily C2 (18:00 NY day): sweeps the prior day's low (high), closes back inside, "
        "closes up (down); days sweeping both sides excluded",
        "T-spot = 50% of the C2 candle's range; open from the C2 close until the first 1H "
        "close beyond it, at most 5 trading days",
        "gate: the latest C2 closed before the unicorn's first swing point has the "
        "unicorn's direction, its T-spot is still open at the unicorn's completion, and "
        "the unicorn's sweep extreme reached the T-spot"],
        "params": P}
    src = {
        "tf": "corpus: 07lOxv39LdY 'look for the unicorn on the 5-minute' (concept detection rule 4)",
        "W": "declared-before-run: unicorn formation window 48 bars, as the batch's base book",
        "fill_min": "declared-before-run: limit rests 12 entry-TF bars (60 min)",
        "rr": "corpus: 07lOxv39LdY worked example ~2.25R (low-hanging-fruit 2-2.5R)",
        "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13) = 50 min on 5m",
        "tspot": "method_spec: 3.7 T-spot 'in one example, simply the equilibrium' (own-voice "
                 "t-spot.yaml: 'the T-spot is just the equilibrium')",
        "max_age_days": "declared-before-run: the corpus says 'open until an hourly close past "
                        "it' with no age limit; capped at 5 trading days (one week)",
        "c2": "method_spec: fractal-model-c2 (detectors.fractal.c2_events defaults: "
              "prior_candle sweep, close inside, reversal close)",
        "day_open_hour": "session_window_fit: 18:00 NY daily roll"}
    notes = ("The DTR video never defines the T-spot (TTFM indicator output; derivation "
             "withheld in own-voice material too). Only the EQ construction is tested, so a "
             "NULL here speaks to 'C2 EQ as a standalone POI', not to the indicator's box. "
             "Direction = direction of the C2 closure (concept execution.bias).")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
    for k in ("n", "verdict", "verdict_detail", "diff", "ci_lo", "ci_hi", "p", "ties",
              "gated", "complement"):
        print(k, res.get(k))
