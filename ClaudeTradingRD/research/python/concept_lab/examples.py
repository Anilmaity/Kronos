"""Worked examples, one per test type — the README's snippets, runnable.

    cd research/python && ../../.venv/bin/python -m concept_lab.examples [--write DIR]

Results are only written when --write is given, and then to DIR (never to the
campaign's results directory — these are demonstrations, not campaign results).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402


# ── 1. trade_test: bare 1h CISD, entered on the confirming bar's close ─────────
def detect_cisd(m1: pd.DataFrame, tf: str = "1h", killzone: bool = False) -> pd.DataFrame:
    """Pure detector: M1 in -> events out. Builds its bars FROM ITS INPUT, so
    probe_lookahead can re-run it on truncated data. Every column that is scored
    (including a gate column) is emitted HERE, so the probe checks all of it."""
    b = cl.build_bars(m1, tf)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if ev.empty:
        return pd.DataFrame(columns=cols + (["in_kz"] if killzone else []))
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    out = pd.DataFrame({
        "decision_time": close,            # decide when the confirming bar CLOSES
        "available_at": close,             # latest input = that bar (swings are older)
        "direction": np.where(ev["direction"] == "bullish", 1, -1),
        "stop_px": ev["protected_swing"].to_numpy(),
        "rr": 2.0,
    })
    if killzone:                           # a clock gate, known at the decision
        out["in_kz"] = cl.in_window(out["decision_time"], *cl.KILLZONES["fx_ny_am"])
    return out


def example_trade():
    ev = cl.cache_frame("example_cisd_1h", lambda: detect_cisd(cl.load_m1()))
    probe = cl.probe_lookahead(detect_cisd, ev, lookback="20D")      # raises if it peeks
    res = cl.trade_test(ev, max_hold="10h")
    op = {"rules": ["1h UTC-aligned bars; CISD = close through the opening price of the "
                    "opposing candle series after a 2/2 swing, within 3 bars",
                    "decide at the confirming bar's close; enter next M1 open",
                    "stop at the protected swing; target 2R; exit after 10h"],
          "params": {"tf": "1h", "level_rule": "series_open", "swing": "2/2",
                     "max_wait": 3, "rr": 2.0, "max_hold": "10h"}}
    src = {k: "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked config)"
           for k in op["params"]}
    return res, op, src, probe, None


# ── 2. gate_test: does the forex NY-AM killzone improve 15m CISD? ─────────────
def example_gate():
    def detect(m):
        return detect_cisd(m, "15min", killzone=True)
    ev = cl.cache_frame("example_cisd_15min_kz", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="10D")   # checks the in_kz column too
    res = cl.gate_test(ev, "in_kz", mask_available_at="decision_time",  # clock gate
                       max_hold="150min")
    op = {"rules": ["baseline: 15m bare CISD (as example 1, 15m bars)",
                    "gate: decision time inside 07:00-10:00 New York (DST-aware)"],
          "params": {"window": "07:00-10:00", "baseline_tf": "15min", "max_hold": "150min"}}
    src = {"window": "session_window_fit: forex NY AM killzone, killzones.yaml (verbatim)",
           "baseline_tf": "phase3: primary stack entry TF",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    return res, op, src, probe, None


# ── 3. rate_test: is the prior day's high taken during the next day? ─────────
def example_rate():
    """Horizon in TRADING time: a wall-clock '23h' from a Friday close spans the
    weekend and holds no tradable minute, which would depress the observed rate
    and fake a NEGATIVE. The next session's M1-bar count is used for the real
    event AND its nulls, so both get the same tradable exposure."""
    mkt = cl.get_market()
    d = cl.bars("1D")
    d = d[d["n_m1"] > 600]                                   # skip stub/holiday days
    t = pd.DatetimeIndex(d["close_time"].iloc[:-1])          # each day's close = decision
    pdh = d["high"].iloc[:-1].to_numpy()                     # level known at that close
    nxt = d["n_m1"].iloc[1:].to_numpy()                      # next session's length, bars
    first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    obs = cl.touch(t, pdh, "above", horizon_bars=nxt)["hit"].to_numpy()
    dist = pdh - first_px                                    # geometry to preserve
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)      # matched random moments

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        px = mkt.o[mkt.pos_at_or_after(tk[ok])]
        out[ok] = cl.touch(tk[ok], px + dist[ok], "above",
                           horizon_bars=nxt[ok])["hit"].to_numpy()
        return out

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn)
    op = {"rules": ["at each NY trading-day close (18:00 NY roll), take that day's high",
                    "hit = any M1 high >= it during the next session (its M1-bar count)",
                    "null = same distance above price, same bar count, at matched "
                    "random moments (+/-30d)"],
          "params": {"horizon": "next session, in M1 bars", "day_open_hour": 18}}
    src = {"horizon": "declared-before-run: one trading session",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    return res, op, src, None, ("pure level rule: the prior trading day's high, read "
                                "from bars('1D') at that bar's close_time; no detector")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", default=None, help="directory to write example JSONs to")
    a = ap.parse_args(argv)
    for name, fn, cid in (("trade", example_trade, "cisd"),
                          ("gate", example_gate, "killzones"),
                          ("rate", example_rate, "previous-period-high-low")):
        t0 = time.time()
        res, op, src, probe, no_det = fn()
        wall = round(time.time() - t0, 1)
        keys = ("n", "avg_R", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p",
                "mde", "verdict", "verdict_detail")
        print(f"\n== {name} ({wall}s wall) ==")
        for k in keys:
            if res.get(k) is not None:
                print(f"  {k:15s} {res[k]}")
        if a.write:
            p = cl.write_result(cid, f"example_{name}", res, operationalization=op,
                                params_source=src, script=__file__, probe=probe,
                                no_detector=no_det,
                                results_dir=Path(a.write), allow_unknown_id=True)
            print("  wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
