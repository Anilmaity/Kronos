"""One comparison table: raw sweep logic vs each filter/exit layer, 3 months XAU 5m.

All rows share: retest limit entry at the swept level, tight stop
(extreme + 10% pen), $0.30 round-trip cost, 4h time exit.

Rows:
  RAW                all confirmed sweeps, overlapping trades allowed
  RAW 1-pos          same but one position at a time
  FAST               + sweep reached its extreme in <=3 bars
  FAST+SIZE          + swing sweeps above expanding 25th pctl (the standard set)
  FAST+SIZE 2xBE     same set, TP 2x pen + breakeven move at +1R
  FAST+SIZE LIQ+BE   same set, TP nearest liquidity + BE move

Run: python backtest_compare.py
"""

import numpy as np
import pandas as pd

import backtest_sweep_reversal as bt

COST = 0.30
STOP_BUF = 0.10


def htf_masks(df, sweeps, minutes):
    """Per-sweep HTF-wick validity, no lookahead.

    contained: the whole manipulation (break -> confirmation) sits inside one
               HTF candle, so it prints there as a wick through the level.
    wick:      the previous COMPLETED HTF candle swept the level and closed
               back through it (the wick-rejection is already on the chart).
    """
    tsec = df["time"].astype("int64").values
    if tsec[0] > 10**15:            # ns -> s
        tsec = tsec // 10**9
    bucket = tsec // (minutes * 60)
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    contained, wick = [], []
    for ev in sweeps:
        brk = ev.conf_i - ev.manip_bars + 1
        contained.append(bucket[brk] == bucket[ev.conf_i])
        bprev = bucket[ev.conf_i] - 1
        i0 = np.searchsorted(bucket, bprev, side="left")
        i1 = np.searchsorted(bucket, bprev, side="right")
        w = False
        if i1 > i0:
            hh, ll, cc = h[i0:i1].max(), l[i0:i1].min(), c[i1 - 1]
            w = (hh > ev.level and cc < ev.level) if ev.direction == "down" \
                else (ll < ev.level and cc > ev.level)
        wick.append(w)
    return np.array(contained), np.array(wick)


def compute_legs(df, sweeps):
    """Manipulation leg per sweep: origin (within 3 bars of the break) to the
    sweep extreme — same definition the chart draws. 1 SD = this leg."""
    h, l = df["high"].values, df["low"].values
    legs = []
    for ev in sweeps:
        brk = ev.conf_i - ev.manip_bars + 1
        lo0 = max(0, brk - 3)
        origin = l[lo0: brk + 1].min() if ev.direction == "down" \
            else h[lo0: brk + 1].max()
        legs.append(abs(ev.extreme - origin))
    return np.array(legs)


def simulate(df, sweeps, fast=False, size=False, single_pos=True,
             tp_mode="1.5", be=False, hours=None, allow=None,
             sd_mult=None, legs=None):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    hour_of = df["time"].dt.hour.values
    n = len(df)
    rows = []
    busy_until = -1
    pen_hist = []
    for k, ev in enumerate(sweeps):
        ok_size = (ev.kind in ("PD", "session") or len(pen_hist) < bt.WARMUP_EVENTS
                   or ev.m_pen >= np.quantile(pen_hist, bt.PEN_PCTL))
        pen_hist.append(ev.m_pen)
        if single_pos and ev.conf_i <= busy_until:
            continue
        if fast and ev.manip_bars > bt.FAST_BARS:
            continue
        if size and not ok_size:
            continue
        if hours is not None and hour_of[ev.conf_i] not in hours:
            continue
        if allow is not None and not allow[k]:
            continue

        sign = -1 if ev.direction == "down" else 1
        stop = ev.extreme - sign * STOP_BUF * ev.m_pen
        entry = ev.level
        fill_i = None
        for x in range(ev.conf_i + 1, min(ev.conf_i + 1 + bt.ENTRY_TTL, n)):
            if (sign < 0 and h[x] >= entry) or (sign > 0 and l[x] <= entry):
                fill_i = -1 if (h[x] >= stop if sign < 0 else l[x] <= stop) else x
                break
        if fill_i in (None, -1):
            continue
        risk = abs(stop - entry)
        if risk <= 0:
            continue
        if sd_mult is not None:
            tp = ev.extreme + sign * sd_mult * legs[k]
        elif tp_mode == "liquidity":
            if ev.target is None:
                continue
            tp = ev.target
        else:
            tp = entry + sign * float(tp_mode) * ev.m_pen
        if abs(tp - entry) / risk < bt.MIN_RR:
            continue

        be_trigger = entry + sign * risk
        cur_stop = stop
        outcome, exit_px, exit_i = None, None, min(fill_i + bt.HORIZON, n - 1)
        for x in range(fill_i + 1, min(fill_i + bt.HORIZON, n)):
            if (h[x] >= cur_stop if sign < 0 else l[x] <= cur_stop):
                outcome, exit_px, exit_i = "SL", cur_stop, x
                break
            if (l[x] <= tp if sign < 0 else h[x] >= tp):
                outcome, exit_px, exit_i = "TP", tp, x
                break
            if be and cur_stop == stop:
                if (l[x] <= be_trigger if sign < 0 else h[x] >= be_trigger):
                    cur_stop = entry
        if outcome is None:
            outcome, exit_px = "TIME", c[exit_i]
        rows.append({"time": df["time"].iloc[fill_i],
                     "r": (sign * (exit_px - entry) - COST) / risk})
        busy_until = exit_i
    return pd.DataFrame(rows)


def row(name, tr, n_signals, days):
    if tr.empty:
        return {"config": name, "trades": 0}
    wr = (tr.r > 0).mean()
    pf = tr.r[tr.r > 0].sum() / max(1e-9, -tr.r[tr.r <= 0].sum())
    eq = tr.r.cumsum()
    monthly = {f"{m}": round(g.r.sum(), 1) for m, g in
               tr.groupby(tr.time.dt.tz_localize(None).dt.to_period("M"))}
    return {"config": name, "signals": n_signals, "trades": len(tr),
            "per_day": round(len(tr) / days, 1), "WR%": round(100 * wr),
            "avgR": round(tr.r.mean(), 3), "netR": round(tr.r.sum(), 1),
            "PF": round(pf, 2), "maxDD_R": round((eq - eq.cummax()).min(), 1),
            **monthly}


if __name__ == "__main__":
    m1 = pd.read_parquet("xau_m1_oanda.parquet").set_index("time")
    df = m1.resample("5min").agg(open=("open", "first"), high=("high", "max"),
                                 low=("low", "min"), close=("close", "last")
                                 ).dropna().reset_index()
    days = (df["time"].iloc[-1] - df["time"].iloc[0]).days
    sweeps = bt.detect_sweeps(df)
    print(f"XAU 5m: {len(df):,} bars, {days} days, {len(sweeps)} raw sweeps\n")

    c15, w15 = htf_masks(df, sweeps, 15)
    legs = compute_legs(df, sweeps)
    LOCKED = dict(single_pos=False, be=True, allow=c15 | w15)
    configs = [
        ("LOCKED tp=2x pen",  LOCKED | dict(tp_mode="2.0")),
        ("tp=1.5 SD leg",     LOCKED | dict(sd_mult=1.5, legs=legs)),
        ("tp=2.0 SD leg",     LOCKED | dict(sd_mult=2.0, legs=legs)),
        ("tp=2.5 SD leg *",   LOCKED | dict(sd_mult=2.5, legs=legs)),
        ("tp=3.0 SD leg",     LOCKED | dict(sd_mult=3.0, legs=legs)),
    ]
    rows = [row(name, simulate(df, sweeps, **kw), len(sweeps), days)
            for name, kw in configs]
    res = pd.DataFrame(rows)
    pd.set_option("display.width", 160)
    print(res.to_string(index=False))
    res.to_csv("compare_results.csv", index=False)
    print("\nsaved compare_results.csv")

    # hour-of-day profile of the baseline, to ground-truth session intuitions
    tr = simulate(df, sweeps, **(LOCKED | dict(sd_mult=2.5, legs=legs)))
    tr["hour"] = tr.time.dt.hour
    prof = tr.groupby("hour").r.agg(["count", "mean", "sum"]).round(2)
    print("\nRAW 2xBE by UTC hour (count / avgR / netR):")
    print(prof.to_string())
