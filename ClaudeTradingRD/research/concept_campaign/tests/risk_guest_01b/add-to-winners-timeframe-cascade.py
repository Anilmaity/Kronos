"""add-to-winners-timeframe-cascade (guest: Alex's Options, 1XWyy6Q-_8Q, TheSTRAT).

Claim: 'take the 15-minute 2-2, and if that 15-minute target is reached it triggers the
30-minute 2-2, so add on the 30 ... we always want to add to Winners'.

Operationalisation (trade_test, claim '+'): the ADD itself.
  initial  = 15m STRAT 2-2 reversal with timeframe continuity (trigger close above the
             trading-day open and the hour open for longs), stop at the prior 2's other
             side, target = the magnitude (extreme of the bar before the 2), resolved on M1
             (stop first on ties) within 10 x 15m.
  add      = a same-direction 30m 2-2 reversal trigger that fires in the same 30m bar in
             which (at/after) a live 15m trade reached its target - i.e. the winner is
             what triggered the higher timeframe. Enter at that trigger; stop at the prior
             30m 2's other side; target the 30m magnitude; 10 x 30m time exit.
  => do the adds beat a matched random entry (same direction/stop/target distance)?
Only the first rung (15m -> 30m) is tested; the hour 2-1-2 rung is not (one example only).
All parameters were fixed before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

TF1, TF2 = "15min", "30min"   # corpus 1XWyy6Q-_8Q worked sequence 15m -> 30m
H1_BARS = 10                  # declared-before-run: 15m trade resolved within 10 bars
HOLD_ADD = "5h"               # declared-before-run: 10 x 30m bars (phase-3 10-bar convention)


def strat_types(b):
    H, L = b["high"].to_numpy(), b["low"].to_numpy()
    up = np.r_[False, H[1:] > H[:-1]]
    dn = np.r_[False, L[1:] < L[:-1]]
    return up & ~dn, dn & ~up


def strat_22_triggers(m1, tf):
    b = cl.build_bars(m1, tf)
    H, L = b["high"].to_numpy(), b["low"].to_numpy()
    is2u, is2d = strat_types(b)
    fl = m1.index.floor(tf)
    pos = b.index.searchsorted(fl, "right") - 1
    valid = (pos >= 2) & (b.index[np.clip(pos, 0, None)] == fl)
    p = np.clip(pos, 2, None)
    mh, ml = m1["high"].to_numpy(), m1["low"].to_numpy()
    longc = valid & is2d[p - 1] & (mh > H[p - 1]) & (H[p - 2] > H[p - 1])
    shortc = valid & is2u[p - 1] & (ml < L[p - 1]) & (L[p - 2] < L[p - 1])
    rows = []
    for d, c in ((1, longc), (-1, shortc)):
        idx = np.flatnonzero(c)
        if not len(idx):
            continue
        s = pd.Series(idx).groupby(p[idx]).first()
        k, i = s.index.to_numpy(), s.to_numpy()
        rows.append(pd.DataFrame({
            "m1_pos": i, "bar": k, "direction": d,
            "bar_start": b.index[k],
            "stop_px": np.where(d == 1, L[k - 1], H[k - 1]),
            "target_px": np.where(d == 1, H[k - 2], L[k - 2])}))
    cols = ["m1_pos", "bar", "direction", "bar_start", "stop_px", "target_px"]
    if not rows:
        return pd.DataFrame(columns=cols)
    tr = pd.concat(rows).sort_values("m1_pos").reset_index(drop=True)
    c = m1["close"].to_numpy()[tr["m1_pos"].to_numpy()]
    d = tr["direction"].to_numpy()
    ok = ((tr["stop_px"].to_numpy() - c) * d < 0) & ((tr["target_px"].to_numpy() - c) * d > 0)
    tr = tr[ok].reset_index(drop=True)
    tr["t"] = m1.index[tr["m1_pos"].to_numpy()] + pd.Timedelta(minutes=1)   # trigger close
    return tr


def tfc_ok(m1, tr):
    o = m1["open"].to_numpy()
    td = pd.Series(cl.trading_day(m1.index).to_numpy())
    day_open = pd.Series(o).groupby(td).transform("first").to_numpy()
    hour_open = pd.Series(o).groupby(m1.index.floor("1h").to_numpy()).transform("first").to_numpy()
    i = tr["m1_pos"].to_numpy()
    c = m1["close"].to_numpy()[i]
    d = tr["direction"].to_numpy()
    return (np.sign(c - day_open[i]) == d) & (np.sign(c - hour_open[i]) == d)


def win_times(m1, tr, bars_):
    """M1-close time at which each trade's target is hit before its stop (NaT otherwise)."""
    hz = pd.Timedelta(TF1) * bars_
    out = np.full(len(tr), np.datetime64("NaT"), dtype="datetime64[ns]")
    for d, up, dn in ((1, "above", "below"), (-1, "below", "above")):
        sel = np.flatnonzero(tr["direction"].to_numpy() == d)
        if not len(sel):
            continue
        t = pd.DatetimeIndex(tr["t"].iloc[sel])
        tg = cl.touch(t, tr["target_px"].to_numpy()[sel], up, horizon=hz, m1=m1)
        st = cl.touch(t, tr["stop_px"].to_numpy()[sel], dn, horizon=hz, m1=m1)
        tt = pd.DatetimeIndex(tg["hit_time"]).tz_convert("UTC")
        ss = pd.DatetimeIndex(st["hit_time"]).tz_convert("UTC")
        win = tg["hit"].to_numpy() & (~st["hit"].to_numpy() | (tt < ss))
        w = (tt + pd.Timedelta(minutes=1)).tz_localize(None).to_numpy()
        out[sel] = np.where(win, w, np.datetime64("NaT"))
    return pd.DatetimeIndex(out).tz_localize("UTC")


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    t1 = strat_22_triggers(m1, TF1)
    t2 = strat_22_triggers(m1, TF2)
    if t1.empty or t2.empty:
        return pd.DataFrame(columns=cols)
    t1 = t1[tfc_ok(m1, t1)].reset_index(drop=True)
    w = win_times(m1, t1, H1_BARS)
    rows = []
    for d in (1, -1):
        wd = np.sort(w[(t1["direction"].to_numpy() == d) & ~w.isna()].asi8)
        a = t2[t2["direction"] == d]
        if a.empty or not len(wd):
            continue
        lo = pd.DatetimeIndex(a["bar_start"]).asi8
        hi = pd.DatetimeIndex(a["t"]).asi8
        n_le_hi = np.searchsorted(wd, hi, "right")
        n_lt_lo = np.searchsorted(wd, lo, "left")
        rows.append(a[(n_le_hi - n_lt_lo) > 0])
    if not rows:
        return pd.DataFrame(columns=cols)
    ad = pd.concat(rows).sort_values("t").reset_index(drop=True)
    return pd.DataFrame({"decision_time": pd.DatetimeIndex(ad["t"]),
                         "available_at": pd.DatetimeIndex(ad["t"]),
                         "direction": ad["direction"].to_numpy(),
                         "stop_px": ad["stop_px"].to_numpy(),
                         "target_px": ad["target_px"].to_numpy()})


if __name__ == "__main__":
    ev = cl.cache_frame(f"addwin_strat22_{TF1}_{TF2}_h{H1_BARS}", lambda: detect(cl.load_m1()))
    print("add events", len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=HOLD_ADD, claim="+")
    print({k: res.get(k) for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "verdict", "verdict_detail", "exposure_bars",
                                   "ties", "ctrl_overlap")})
    op = {"rules": [
        "STRAT bar types vs prior bar; 2-2 reversal = prior bar 2d (2u), triggered intrabar "
        "when an M1 high (low) takes its high (low); decision at that M1 close; stop = other "
        "side of the prior 2; target = extreme of the bar before it (magnitude), which must "
        "lie beyond the trigger close",
        "initial 15m trade requires timeframe continuity: trigger close above (below) the "
        "trading-day open and the hour open",
        "15m trade is a winner if its target is hit (M1) before its stop within 10 x 15m; "
        "stop first on a shared minute",
        "ADD event: a same-direction 30m 2-2 trigger whose 30m bar contains (at/before the "
        "trigger close) the target-hit close of a winning 15m trade",
        "add trade: 30m stop/target as above, 5h (10 x 30m) time exit"],
        "params": {"tf1": TF1, "tf2": TF2, "h1_bars": H1_BARS, "max_hold": HOLD_ADD,
                   "tfc": "1D+1h opens"}}
    src = {"tf1": "corpus: 1XWyy6Q-_8Q 'take the 15-minute 2-2'",
           "tf2": "corpus: 1XWyy6Q-_8Q 'it triggers the 30-minute 2-2, so add on the 30'",
           "h1_bars": "declared-before-run: 10 entry-TF bars (phase-3 hold convention)",
           "max_hold": "declared-before-run: 10 x 30m bars (phase-3 hold convention)",
           "tfc": "corpus: 1XWyy6Q-_8Q precondition 'in the direction of higher-timeframe "
                  "continuity' (yaml htf 1D, 1H)"}
    p = cl.write_result("add-to-winners-timeframe-cascade", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Tests whether the add entry itself has edge; add size and "
                              "aggregate-stop handling are unspecified (yaml ambiguities).")
    print("wrote", p)
