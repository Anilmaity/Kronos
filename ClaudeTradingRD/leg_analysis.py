"""Which manipulation-leg definition matches the 1x-2.5x distribution model?

For each candidate leg measure, on the HTF15-valid signal set:
  - P(distribution reaches k * leg) for k = 1.0 .. 3.0, measured from the
    sweep extreme, within the 240-bar horizon after confirmation
  - backtest TP = 2.0 and 2.5 SD of that leg (retest entry, BE on)

Leg candidates (short-side wording; mirrored for longs):
  pen      level -> extreme                      (penetration only)
  brk1     lowest low of the break bar only -> extreme
  run3     lowest low within 3 bars before break -> extreme   (current chart def)
  run1     lowest low within 1 bar before break -> extreme
  swing12  lowest low within 12 bars before break -> extreme  (bigger swing leg)
"""

import numpy as np
import pandas as pd

import backtest_sweep_reversal as bt
from backtest_compare import htf_masks, simulate

REACH_KS = (1.0, 1.5, 2.0, 2.5, 3.0)


def leg_defs(df, sweeps):
    h, l = df["high"].values, df["low"].values
    out = {name: [] for name in ("pen", "brk1", "run1", "run3", "swing12")}
    for ev in sweeps:
        brk = ev.conf_i - ev.manip_bars + 1
        if ev.direction == "down":
            base = {"pen": ev.level,
                    "brk1": l[brk],
                    "run1": l[max(0, brk - 1): brk + 1].min(),
                    "run3": l[max(0, brk - 3): brk + 1].min(),
                    "swing12": l[max(0, brk - 12): brk + 1].min()}
            for k, v in base.items():
                out[k].append(ev.extreme - v)
        else:
            base = {"pen": ev.level,
                    "brk1": h[brk],
                    "run1": h[max(0, brk - 1): brk + 1].max(),
                    "run3": h[max(0, brk - 3): brk + 1].max(),
                    "swing12": h[max(0, brk - 12): brk + 1].max()}
            for k, v in base.items():
                out[k].append(abs(ev.extreme - v))
    return {k: np.array(v) for k, v in out.items()}


if __name__ == "__main__":
    m1 = pd.read_parquet("xau_m1_oanda.parquet").set_index("time")
    df = m1.resample("5min").agg(open=("open", "first"), high=("high", "max"),
                                 low=("low", "min"), close=("close", "last")
                                 ).dropna().reset_index()
    h, l = df["high"].values, df["low"].values
    n = len(df)
    sweeps = bt.detect_sweeps(df)
    c15, w15 = htf_masks(df, sweeps, 15)
    valid = c15 | w15
    legs = leg_defs(df, sweeps)

    # distribution distance actually travelled from the extreme (within horizon)
    dist = []
    for ev in sweeps:
        end = min(ev.conf_i + bt.HORIZON, n)
        if ev.direction == "down":
            dist.append(ev.extreme - l[ev.conf_i + 1: end].min()
                        if end > ev.conf_i + 1 else 0.0)
        else:
            dist.append(h[ev.conf_i + 1: end].max() - ev.extreme
                        if end > ev.conf_i + 1 else 0.0)
    dist = np.array(dist)

    idx = np.where(valid)[0]
    print(f"HTF15-valid signals: {len(idx)}\n")
    print("── how often the distribution reaches k x leg (from extreme) ──")
    print(f"{'leg def':9s} {'median$':>8s} " +
          " ".join(f"P>={k}x" for k in REACH_KS))
    for name, lg in legs.items():
        with np.errstate(divide="ignore", invalid="ignore"):
            mult = np.where(lg[idx] > 0, dist[idx] / lg[idx], np.nan)
        probs = " ".join(f"{100 * np.nanmean(mult >= k):5.0f}%" for k in REACH_KS)
        print(f"{name:9s} {np.median(lg[idx]):8.2f} {probs}")

    print("\n── backtest: TP = 2.0 / 2.5 SD per leg definition (BE on) ──")
    LOCKED = dict(single_pos=False, be=True, allow=valid)
    print(f"{'config':18s} {'n':>4s} {'WR%':>4s} {'avgR':>7s} {'netR':>7s} "
          f"{'PF':>5s} {'maxDD':>7s}")
    for name, lg in legs.items():
        for sd in (2.0, 2.5):
            tr = simulate(df, sweeps, **(LOCKED | dict(sd_mult=sd, legs=lg)))
            if tr.empty:
                continue
            pf = tr.r[tr.r > 0].sum() / max(1e-9, -tr.r[tr.r <= 0].sum())
            eq = tr.r.cumsum()
            print(f"{name} x{sd:<13} {len(tr):4d} {100 * (tr.r > 0).mean():4.0f} "
                  f"{tr.r.mean():+7.3f} {tr.r.sum():+7.1f} {pf:5.2f} "
                  f"{(eq - eq.cummax()).min():7.1f}")
