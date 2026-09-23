"""mmxm-hedging-program (guest: The MMXM Trader, Ibw4saRtYMk) — declared before the first run.

The causal story (central banks hedging, net-long at the low) is not observable from price.
What the concept makes checkable is its trading consequence: the up-close candles on the
SELL side of a buy model's curve (the "institutional buying") are extended to the BUY side
as mitigation blocks that hold. Tested as an entry rule on 1H (sell model mirrored):

  * curve split: a 1H 2/2 swing low that is the lowest low of the last 48 bars; the model's
    range high H = highest high of the 48 bars before it; sell side = bars between H and the low.
  * mitigation blocks = every up-close candle on the sell side; zone = the candle's range.
  * buy side: after the swing low is confirmed, a block is 'extended' once a 1H bar closes
    above its high (within 48 bars of the low). Its first M1 return to the block high
    (before price has traded to H, within 48 1H bars of the low) is a LONG, decided at that
    M1 bar's close; stop at the block low; 2R; hold 10h trading time.
  * clustered by model (several blocks of one curve share the same move).
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

TF = "1h"
N_RANGE = 48
WIN = 48
RR = 2.0
HOLD = "10h"


def _cands(o, h, l, c, idx):
    tmp = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=idx)
    sw = swing_points(tmp, 2, 2)
    n = len(c)
    out = []
    for pL in np.flatnonzero(sw["swing_low"].to_numpy()):
        if pL < N_RANGE or pL + 2 >= n:
            continue
        if l[pL] > np.min(l[pL - N_RANGE + 1:pL + 1]):
            continue
        seg = slice(pL - N_RANGE, pL)
        pH = pL - N_RANGE + int(np.argmax(h[seg]))
        H = h[pH]
        end = min(n, pL + WIN + 1)
        for q in range(pH + 1, pL):
            if not c[q] > o[q]:
                continue
            bh, bl = h[q], l[q]
            a = None
            for i in range(pL + 2, end):
                if c[i] > bh:
                    a = i
                    break
            if a is None:
                continue
            out.append((pL, q, a, end - 1, bh, bl, H))
    return out


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    b = b[b["n_m1"] > 0]
    ct = pd.DatetimeIndex(b["close_time"])
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "model_id"]
    frames = []
    for sgn in (1, -1):
        f = float(sgn)
        o, c = f * b["open"].to_numpy(), f * b["close"].to_numpy()
        if sgn == 1:
            h, l = b["high"].to_numpy(), b["low"].to_numpy()
        else:
            h, l = -b["low"].to_numpy(), -b["high"].to_numpy()
        cc = _cands(o, h, l, c, b.index)
        if not cc:
            continue
        pL, q, a, last, bh, bl, H = map(np.array, zip(*cc))
        t_act = ct[a]
        until = ct[last]
        # real-price levels
        lvl = f * bh
        side_back = "below" if sgn == 1 else "above"
        side_tgt = "above" if sgn == 1 else "below"
        tb = cl.touch(t_act, lvl, side_back, m1=m1, until=until)
        tH = cl.touch(t_act, f * H, side_tgt, m1=m1, until=until)
        hit = tb["hit"].to_numpy()
        ht = pd.DatetimeIndex(tb["hit_time"])
        hH = pd.DatetimeIndex(tH["hit_time"])
        ok = hit & (~tH["hit"].to_numpy() | (hH > ht))
        dec = ht[ok] + pd.Timedelta(minutes=1)
        frames.append(pd.DataFrame({
            "decision_time": dec, "available_at": dec, "direction": sgn,
            "stop_px": f * bl[ok], "rr": RR,
            "model_id": [f"{sgn}_{b.index[p].value}" for p in pL[ok]]}))
    if not frames:
        return pd.DataFrame(columns=cols)
    ev = pd.concat(frames)[cols]
    # the stop must be on the losing side of the level (block with zero range dropped)
    return ev.sort_values(["decision_time", "direction", "stop_px"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("mmxm_hedging_prog_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev.model_id.nunique(), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=HOLD, hold_basis="bars", cluster="model_id", claim="+")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap")})
    op = {"rules": [
        "1H: curve split = 2/2 swing low that is the lowest low of 48 bars; range high = highest "
        "high of the 48 bars before it; sell side = bars between them",
        "mitigation blocks = up-close candles on the sell side, zone = candle high..low",
        "block extended to the buy side once a 1H close above its high (from the low's confirmation, "
        "within 48 bars)",
        "first M1 return to the block high before price reaches the range high, within 48 1H bars of "
        "the low: long at the next M1 open, stop block low, 2R, 10h trading time; mirrored for sell models",
        "clustered by model"],
        "params": {"tf": TF, "range_bars": N_RANGE, "window_bars": WIN, "zone": "candle range",
                   "rr": RR, "max_hold": HOLD, "hold_basis": "bars", "swing": "2/2"}}
    src = {"tf": "corpus: Ibw4saRtYMk concept ltf 4H/1H/15m — 1H declared-before-run",
           "range_bars": "declared-before-run: the model's range = two trading days of 1H bars",
           "window_bars": "declared-before-run: buy side considered for two trading days",
           "zone": "declared-before-run: whole candle as the block (source gives no boundary)",
           "rr": "phase3: 2R target (no target stated in the source)",
           "max_hold": "phase3: 10 entry-TF bars",
           "hold_basis": "declared-before-run: trading-time hold across halts (trap 7)",
           "swing": "phase3: 2/2 fractal swing"}
    p = cl.write_result("mmxm-hedging-program", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="The central-bank hedging mechanism itself is not observable in OHLC "
                              "(and the source offers one COT chart); tested is its stated trading "
                              "consequence, the hold of extended sell-side up-close candles.")
    print(p)
