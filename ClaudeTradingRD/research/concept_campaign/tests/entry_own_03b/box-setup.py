"""box-setup — contested (evolution): two TTrades readings, both trade_test, claim '+'.

Core (HFfChGFHD44 / E6bpY4dQvlE): resting liquidity (an old high/low) is taken by an
AGGRESSIVE move OUT, met by an AGGRESSIVE move BACK IN; mark the deviated level by the
BODIES ('I generally mark out the bodies'); trade the retest of that deviation; stop
beyond the manipulation extreme; '2R before runners'. 'Aggressive' is evidenced by a
fair value gap each way (E6bpY4dQvlE: the out/in FVG pair is the important part).

reading a (canonical, HFfChGFHD44): limit at the deviated body level on its RETEST.
reading b (earlier E6bpY4dQvlE: 'I prefer to catch them right away'): enter at once,
  at the close of the candle that moved aggressively back inside the range.

Bearish case (bullish mirrors):
  old high = latest confirmed 2/2 swing high at bar p; box_level = the highest BODY
  (max(open, close)) of the swing's fractal window p-2..p+2;
  OUT = the first later bar k (within 96 bars) whose high exceeds the swing high, with a
  bullish FVG stamped between k-1 and the deviation extreme bar;
  IN = the first bar q (k < q <= k+8) that CLOSES below box_level, with a bearish FVG
  stamped after the deviation extreme bar and by q;
  deviation extreme = max high over k..q (the stop).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import _batch_common as bc    # noqa: E402
from _batch_common import cl, fair_value_gaps  # noqa: E402

CID = "box-setup"
RR = 2.0
MAX_HOLD = "150min"
LIQ_LIFE = 96          # an old high stays 'resting liquidity' for 96 bars (1 day)
IN_BARS = 8            # the move back in must close inside within 8 bars of the take
LIVE_BARS = 16         # reading a: retest limit live 16 bars after the close back in
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]
TD = pd.Timedelta(minutes=bc.TF_MIN)


def setups(b: pd.DataFrame) -> pd.DataFrame:
    is_sh, is_sl = bc.swing_arrays(b)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    fv = fair_value_gaps(b[["open", "high", "low", "close"]])
    bull = fv["bullish_fvg"].to_numpy()
    bear = fv["bearish_fvg"].to_numpy()
    n = len(b)
    bt = np.maximum(o, c)
    bb = np.minimum(o, c)
    rows = []
    for d, pos, ext in ((-1, np.flatnonzero(is_sh), h), (1, np.flatnonzero(is_sl), l)):
        for p in pos:
            if p < 2 or p + 3 >= n:
                continue
            lvl_ext = ext[p]
            box = bt[p - 2:p + 3].max() if d == -1 else bb[p - 2:p + 3].min()
            s = p + bc.SW_R + 1                      # first bar that may take it
            e = min(n, s + LIQ_LIFE)
            took = np.flatnonzero(h[s:e] > lvl_ext) if d == -1 else \
                np.flatnonzero(l[s:e] < lvl_ext)
            if len(took) == 0:
                continue
            k = s + int(took[0])
            qe = min(n, k + 1 + IN_BARS)
            back = np.flatnonzero(c[k + 1:qe] < box) if d == -1 else \
                np.flatnonzero(c[k + 1:qe] > box)
            if len(back) == 0:
                continue
            q = k + 1 + int(back[0])
            if d == -1:
                x = k + int(np.argmax(h[k:q + 1]))
                dev = h[x]
                out_ok = bull[max(0, k - 1):x + 1].any()
                in_ok = bear[x + 1:q + 1].any()
            else:
                x = k + int(np.argmin(l[k:q + 1]))
                dev = l[x]
                out_ok = bear[max(0, k - 1):x + 1].any()
                in_ok = bull[x + 1:q + 1].any()
            if not (out_ok and in_ok):
                continue
            rows.append((q, d, box, dev))
    return pd.DataFrame(rows, columns=["q", "d", "box", "dev"])


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    b = bc.bars(m1)
    if len(b) < 50:
        return bc.empty(COLS)
    s = setups(b)
    if s.empty:
        return bc.empty(COLS)
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")[s["q"].to_numpy()]
    ev = pd.DataFrame({"decision_time": ct, "available_at": ct,
                       "direction": s["d"].to_numpy(), "stop_px": s["dev"].to_numpy(),
                       "rr": RR})
    return bc.finish(ev)


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    b = bc.bars(m1)
    if len(b) < 50:
        return bc.empty(COLS)
    s = setups(b)
    if s.empty:
        return bc.empty(COLS)
    start = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")[s["q"].to_numpy()]
    hit, dt = bc.touch_sided(m1, start, s["box"].to_numpy(), s["d"].to_numpy(),
                             start + LIVE_BARS * TD)
    s = s[hit]
    dt = dt[hit]
    ev = pd.DataFrame({"decision_time": dt, "available_at": dt,
                       "direction": s["d"].to_numpy(), "stop_px": s["dev"].to_numpy(),
                       "rr": RR})
    return bc.finish(ev)


BASE_RULES = [
    "15m bars, 2/2 swings. Bearish: old high = latest confirmed swing high; box_level = "
    "highest body (max(open,close)) of bars p-2..p+2 around it (bodies by default)",
    "OUT: first later bar (within 96 bars of confirmation) trading above the swing high, "
    "with a bullish FVG stamped from k-1 to the deviation-extreme bar (aggressive out)",
    "IN: first bar within 8 bars of the take that CLOSES below box_level, with a bearish "
    "FVG stamped after the deviation extreme and by that close (aggressive back in)",
    "stop at the deviation extreme (max high from the take to the close back in); 2R; "
    "exit 150 min. Bullish mirrors on swing lows"]
PARAMS = {"tf": bc.TF, "swing": "2/2", "box_level": "highest/lowest body of the swing window",
          "aggressive": "FVG out and FVG in", "liq_life": LIQ_LIFE, "in_bars": IN_BARS,
          "rr": RR, "max_hold": MAX_HOLD}
SRC = {"tf": "corpus: box-setup.yaml ltf 15m/5m/1m; phase3 primary entry TF",
       "swing": "phase3: locked 2/2 fractal",
       "box_level": "corpus: HFfChGFHD44 'I generally Mark out the bodies for this setup'",
       "aggressive": "corpus: E6bpY4dQvlE 'consolidation aggressive down aggressive up' + box-setup.yaml 'often evidenced by a fair value gap'",
       "liq_life": "declared-before-run: an old high counts as resting liquidity for 96 bars (1 day)",
       "in_bars": "declared-before-run: the aggressive move back in must close inside within 8 bars (2h) of the take",
       "rr": "corpus: box-setup.yaml targets '2R before runners in one example'",
       "max_hold": "phase3: 10 entry-TF bars (§1.13)"}


def show(res):
    for k in ["n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "verdict",
              "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "dropped"]:
        print(" ", k, res.get(k))


def run_a():
    ev = cl.cache_frame("box_a_15m_retest", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    show(res)
    op = {"rules": BASE_RULES + ["reading a: limit at box_level on its retest (first M1 "
                                 "touch within 16 bars after the close back in; decide at "
                                 "that M1 close)"],
          "params": {**PARAMS, "live_bars": LIVE_BARS}}
    src = {**SRC, "live_bars": "declared-before-run: the retest limit is live 16 bars (4h)"}
    return cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                           script=__file__, probe=probe,
                           notes="Reading a = canonical HFfChGFHD44: retest of the deviated body level.")


def run_b():
    ev = cl.cache_frame("box_b_15m_early", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev))
    probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    show(res)
    op = {"rules": BASE_RULES + ["reading b: enter immediately at the next M1 open after "
                                 "the candle that closed back inside"],
          "params": dict(PARAMS)}
    return cl.write_result(CID, "b", res, operationalization=op, params_source=dict(SRC),
                           script=__file__, probe=probe,
                           notes="Reading b = earlier E6bpY4dQvlE 'I prefer to catch them right "
                                 "away': entry at the close back inside instead of the retest.")


if __name__ == "__main__":
    which = sys.argv[1:] or ["a", "b"]
    if "a" in which:
        print(run_a())
    if "b" in which:
        print(run_b())
