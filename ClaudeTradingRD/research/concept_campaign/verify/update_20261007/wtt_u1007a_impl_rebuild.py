"""Implementation-lens verifier for wick-trust-test u1007a (independent rebuild).

Own CISD (locked rung-0 definition: swing 2/2, series_open, max_wait 3, run <= 10, run end
within 2 bars of the swing) and own per-closure yes/no loop, written from the draft YAML and
transcript (RX8vtP3PLYk), NOT imported from the tested script or structure_own_02b/_common.
Ledger is redirected to a scratch file; nothing is written to results/ or the campaign ledger.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["CONCEPT_LAB_LEDGER"] = str(HERE / "wtt_u1007a_impl_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")

import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402
import concept_lab as cl      # noqa: E402

PKL = HERE / "wtt_u1007a_impl_events.pkl"


def my_cisd(o, h, l, c):
    """-> dict (confirm bar j, sign) -> list of (protected swing price, swing bar i)."""
    n = len(o)
    out = {}
    for sgn in (1, -1):
        x = l if sgn == 1 else -h                    # treat both as a 'low' search
        q = (c < o) if sgn == 1 else (c > o)         # opposing (series) candles
        for i in range(2, n - 2):
            if not (x[i] < x[i - 1] and x[i] < x[i - 2] and x[i] <= x[i + 1] and x[i] <= x[i + 2]):
                continue
            end = i
            while end >= 0 and not q[end] and i - end <= 2:
                end -= 1
            if end < 0 or i - end > 2 or not q[end]:
                continue
            start = end
            while start > 0 and q[start - 1] and end - start + 1 < 10:
                start -= 1
            lvl = o[start]
            for j in range(i + 3, min(n, i + 6)):     # after swing confirmed (i+2), wait 3 bars
                if (c[j] > lvl) if sgn == 1 else (c[j] < lvl):
                    out.setdefault((j, sgn), []).append((l[i] if sgn == 1 else h[i], i))
                    break
    return out


def build():
    h1 = cl.bars("1h")
    d1 = cl.bars("1D")
    o, h, l, c = (h1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    st = pd.DatetimeIndex(h1.index).tz_convert("UTC")
    ct = pd.DatetimeIndex(h1["close_time"]).tz_convert("UTC")
    cis = my_cisd(o, h, l, c)
    tday = np.asarray(cl.trading_day(st))                # trading day of each 1h bar (start)
    dct = pd.Series(pd.DatetimeIndex(d1["close_time"]).tz_convert("UTC").to_numpy(),
                    index=pd.DatetimeIndex(d1["trading_day"]))
    day_close = dct.reindex(pd.DatetimeIndex(tday)).to_numpy()
    first_day = tday[0]
    rows = []
    # group consecutive bars by trading day
    brk = np.flatnonzero(tday[1:] != tday[:-1]) + 1
    starts = np.r_[0, brk]
    ends = np.r_[brk, len(tday)]
    for s, e in zip(starts, ends):
        if tday[s] == first_day:
            continue
        last_ok = ct[s:e] < (pd.Timestamp(day_close[s]).tz_convert("UTC") - pd.Timedelta("1h"))
        for d in (1, -1):
            holding, ps, run = False, np.nan, np.nan
            for jj, j in enumerate(range(s, e)):
                x = l[j] if d == 1 else h[j]
                run = x if np.isnan(run) else (min(run, x) if d == 1 else max(run, x))
                if holding and ((run < ps) if d == 1 else (run > ps)):
                    holding = False
                if holding:
                    continue
                yes = False
                for p, i in cis.get((j, d), ()):
                    if i >= s and p == run:           # swing bar inside this day, swing = day extreme
                        yes = True
                if yes:
                    holding, ps = True, run
                if last_ok[jj]:
                    rows.append((ct[j].value, d, run, yes))
    a = np.array(rows, dtype=object)
    t = pd.DatetimeIndex(pd.to_datetime(a[:, 0].astype(np.int64), utc=True))
    ev = pd.DataFrame({"decision_time": t, "available_at": t, "direction": a[:, 1].astype(int),
                       "stop_px": a[:, 2].astype(float), "rr": 2.0, "trusted": a[:, 3].astype(bool)})
    return ev.sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    if PKL.exists():
        ev = pd.read_pickle(PKL)
    else:
        ev = build()
        ev.to_pickle(PKL)
    print("rows", len(ev), "trusted", int(ev.trusted.sum()), round(ev.trusted.mean(), 4))
    res = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold="10h")
    keys = ("verdict", "n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde", "ctrl_overlap")
    print("REBUILD default:", {k: res.get(k) for k in keys})
    print("  blocks", {k: round(v["diff"], 4) for k, v in res["blocks"].items()},
          "halves", {k: round(res["halves"][k]["diff"], 4) for k in ("H1", "H2")})
    print("  gated_vs_own_control", res.get("gated_vs_own_control"))
    print("  complement vs own", res["complement"]["vs_own_control"])
