#!/usr/bin/env python
"""Independent cross-check of xmr3_backtest.py: the same spec written again as a plain bar-by-bar streaming loop.

It shares only the data plumbing (load_stitched, quotes) with the main script. Indicators, trigger, sizing, exits and
brakes are re-implemented here one bar at a time, in the order a live runner would see them, so nothing can read ahead:
bar i is handled (exits), then added to the indicator state, then a decision is taken at its close for the next open.
The trade list must equal the vectorised engine's for the default cell at spec base cost.

Run:  /Users/anil/Projects/Kronos/ClaudeTradingRD/.venv/bin/python verify_naive.py
"""
from collections import deque

import numpy as np

import xmr3_backtest as bt
from xmr3_backtest import DAY, HOUR, MIN

TP_ATR, SL_ATR, K = bt.DEFAULT


def naive(df, q):
    t = q["t"]
    sh, sl_, sc = df.s_high.to_numpy(), df.s_low.to_numpy(), df.s_close.to_numpy()
    n = len(t)
    hi, lo, cl, tm = deque(maxlen=15), deque(maxlen=15), deque(maxlen=6), deque(maxlen=15)
    b5 = None                      # M5 bucket in progress: [open_ns, high, low, close]
    prev5c, atr, n5, n_tr = None, None, 0, 0
    pos, pend_in, pend_out = None, None, None
    day, stops, realised, halted, cool = -1, 0, 0.0, False, -1
    trades = []

    def in_clock(x):
        tod, dow = x % DAY, (x // DAY + 3) % 7
        if dow >= 5 or tod < HOUR or tod >= 21 * HOUR:
            return False
        return not any(a <= tod < b for a, b in bt.NEWS)

    def close_pos(i, px, how, when):
        nonlocal pos, day, stops, realised, halted, cool
        pts = (px - pos["entry"]) * pos["side"]
        if when // DAY != day:
            day, stops, realised, halted = when // DAY, 0, 0.0, False
        realised += pts * 100 * pos["lot"]
        stops += how == "stop"
        halted = how == "kill" or stops >= bt.DAILY_STOPS
        cool = when + bt.COOLDOWN * MIN
        trades.append((pos["sig"], pos["ent"], i, pos["side"], round(pos["entry"], 6), round(px, 6), how))
        pos = None

    for i in range(n):
        # ---- the open of bar i: orders decided at the previous close
        if pend_out is not None:
            close_pos(i, q["bo"][i] if pos["side"] > 0 else q["ao"][i], pend_out, t[i])
            pend_out = None
        if pend_in is not None:
            sig, side, a = pend_in
            pend_in = None
            lot = np.floor(bt.RISK_MAX / (100 * (SL_ATR * a + 0.30)) * 100 + 1e-9) / 100
            if lot >= 0.01 and in_clock(t[i]):
                entry = q["ao"][i] if side > 0 else q["bo"][i]
                d0 = t[i] // DAY * DAY
                news = next((d0 + s for s, _ in bt.NEWS if d0 + s > t[i]), None)
                pos = dict(sig=sig, ent=i, side=side, lot=lot, entry=entry, stop=entry - side * SL_ATR * a, tgt=entry + side * TP_ATR * a,
                           t_time=t[i] + bt.T_MAX * MIN, t_eod=d0 + 21 * HOUR, news=news)
        if pos is not None and pos["news"] is not None and t[i] >= pos["news"] and i > pos["ent"]:
            close_pos(i, q["bo"][i] if pos["side"] > 0 else q["ao"][i], "news", t[i])
        # ---- inside bar i: resting stop first, then target
        if pos is not None:
            if pos["side"] > 0:
                if q["bl"][i] <= pos["stop"]:
                    close_pos(i, min(pos["stop"], q["bo"][i]) - q["slip"], "stop", t[i] + MIN)
                elif q["bh"][i] >= pos["tgt"]:
                    close_pos(i, pos["tgt"], "tp", t[i] + MIN)
            else:
                if q["ah"][i] >= pos["stop"]:
                    close_pos(i, max(pos["stop"], q["ao"][i]) + q["slip"], "stop", t[i] + MIN)
                elif q["al"][i] <= pos["tgt"]:
                    close_pos(i, pos["tgt"], "tp", t[i] + MIN)
        # ---- the close of bar i: add the bar to the indicator state
        c_t = t[i] + MIN
        k5 = t[i] // (5 * MIN) * (5 * MIN)
        if b5 is not None and b5[0] != k5:                       # an older bucket whose last minute never printed
            prev5c, atr, n5, n_tr = finish5(b5, prev5c, atr, n5, n_tr)
            b5 = None
        b5 = [k5, sh[i], sl_[i], sc[i]] if b5 is None else [k5, max(b5[1], sh[i]), min(b5[2], sl_[i]), sc[i]]
        if c_t >= k5 + 5 * MIN:                                  # the M5 bar is closed exactly now
            prev5c, atr, n5, n_tr = finish5(b5, prev5c, atr, n5, n_tr)
            b5 = None
        hi.append(sh[i]); lo.append(sl_[i]); cl.append(sc[i]); tm.append(t[i])
        if i + 1 >= n:
            break
        # ---- decisions at c(i)
        if pos is not None:
            fl = (((q["bc"][i] if pos["side"] > 0 else q["ac"][i]) - pos["entry"]) * pos["side"]) * 100 * pos["lot"]
            if realised + fl <= bt.KILL_USD:
                pend_out = "kill"
            elif c_t >= pos["t_time"] and c_t >= pos["t_eod"]:
                pend_out = "eod" if (pos["t_eod"] - MIN) <= (pos["t_time"] - MIN) else "time"
            elif c_t >= pos["t_time"]:
                pend_out = "time"
            elif c_t >= pos["t_eod"]:
                pend_out = "eod"
            if pend_out == "eod" and t[i + 1] - c_t > 5 * MIN:  # market shut: last quote of the session
                close_pos(i + 1, q["bc"][i] if pos["side"] > 0 else q["ac"][i], "eod", c_t)
                pend_out = None
            continue
        if c_t // DAY != day:
            day, stops, realised, halted = c_t // DAY, 0, 0.0, False
        usable = atr is not None and n_tr >= 14 and n5 > 100
        if halted or c_t < cool or not in_clock(c_t) or not usable or atr < bt.MIN_ATR5 or len(tm) < 15 or tm[-1] - tm[0] > 30 * MIN:
            continue
        ret5, h15, l15 = cl[-1] - cl[0], max(hi), min(lo)
        if h15 <= l15:
            continue
        p15 = (cl[-1] - l15) / (h15 - l15)
        if ret5 >= K * atr and p15 >= 2 / 3:
            pend_in = (i, -1, atr)
        elif ret5 <= -K * atr and p15 <= 1 / 3:
            pend_in = (i, 1, atr)
    return trades


def finish5(b, prev_c, atr, n5, n_tr):
    """Close one M5 bar: Wilder recursion atr += (tr - atr) / 14, seeded with the first true range."""
    if prev_c is not None:
        tr = max(b[1] - b[2], abs(b[1] - prev_c), abs(b[2] - prev_c))
        atr = tr if atr is None else atr + (tr - atr) / 14
        n_tr += 1
    return b[3], atr, n5 + 1, n_tr


if __name__ == "__main__":
    df = bt.load_stitched()
    q = bt.quotes(df, **bt.COSTS["spec_base"])
    nv = naive(df, q)
    ind = bt.indicators(df.time, df.s_high.to_numpy(), df.s_low.to_numpy(), df.s_close.to_numpy())
    sell, buy, _ = bt.trigger(ind, K)
    el = bt.clock_ok(q["t"] + MIN)
    ve = bt.run(q, np.where(el & sell, -1, np.where(el & buy, 1, 0)).astype(np.int8), ind.atr5.to_numpy(), TP_ATR, SL_ATR)
    vv = [(int(r.sig_i), int(r.ent_i), int(r.exit_i), int(r.side), round(r.entry, 6), round(r.exit, 6), r.how) for r in ve.itertuples()]
    same = sum(a == b for a, b in zip(nv, vv))
    print(f"naive streaming engine: {len(nv)} trades; vectorised engine: {len(vv)} trades; identical rows in order: {same}")
    for a, b in zip(nv, vv):
        if a != b:
            print("first difference:\n  naive     ", a, "\n  vectorised", b)
            break
    assert len(nv) == len(vv) == same, "engines disagree"
    pts = np.array([(x[5] - x[4]) * x[3] for x in nv])
    print(f"recomputed from the naive list: net points {pts.sum():+.1f}, win rate {(pts > 0).mean():.1%}, points PF {pts[pts > 0].sum() / -pts[pts < 0].sum():.3f}")
    print("PASS: the two implementations produce the same trades")
