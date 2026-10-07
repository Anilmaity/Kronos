"""ttfm-favorite-daily-4h-15m -- update 2026-10-07 (draft edu_02, video tUbrCewFdCU,
"How to Trade London Using TTrades Fractal Model").

New claims vs the library entry (prior reading = all same-direction 4h C2s of the day,
UNDERPOWERED n=242, -0.022R):
  * London window: the 4h reversal / C2 closure is "usually the 2200 candle or the 2:00 a.m.
    candle" (futures grid); "the timings will be off by an hour" on forex.
  * hold: "for the duration of this higher time frame candle and potentially even the next".
  * SMT gates: a 4h C2 that is a failure swing (swept the prior candle but failed to take the
    previous high) is traded only with more confirmation, preferably SMT; a very deep 15m run
    only with SMT on the low.

Everything else is the library reading unchanged (daily C2 bias from the previous session,
same-direction 4h C2, first 15m CISD inside the 4h C3 with its extreme formed in C3 and
holding the relevant half of the C2 = the intra-candle CISD, stop = protected swing, 2R).

Readings (the grid is the one open interpretation; README trap 8 / vault: 4H grid is a knob):
  u1007a: forex grid, C2 = the 21:00 or 01:00 NY candle (his futures 22/02 shifted an hour).
  u1007b: futures grid, C2 = the 22:00 or 02:00 NY candle (literal).
Both: failure-swing 4h C2s kept only with 4h gold/silver SMT (XAG H1 aggregated onto gold's
4h bars). The deep-15m-run SMT gate is NOT applied: it needs 15m silver (holdings are XAG
H1/D1) and "very deep" is unquantified. Time exit = close of the 4h candle after C3.
claim '+'.
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402

import concept_lab as cl                 # noqa: E402
import _common as C                      # noqa: E402
from detectors.primitives import swing_points   # noqa: E402

CID = "ttfm-favorite-daily-4h-15m"
RR = 2.0
H4 = pd.Timedelta("4h")
XAG_PATH = "/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xag_h1_full.parquet"
READINGS = {"u1007a": ("forex", (21, 1)), "u1007b": ("futures", (22, 2))}
_XAG = None


def xag_for(m1):
    """Silver H1 bars fully closed by the end of the gold slice."""
    global _XAG
    if _XAG is None:
        x = pd.read_parquet(XAG_PATH)
        x.index = pd.to_datetime(x.index, utc=True)
        x = x[["high", "low"]].astype(float).sort_index()
        _XAG = x[~x.index.duplicated(keep="first")]
    end = pd.DatetimeIndex(m1.index).max() + pd.Timedelta(minutes=1)
    start = pd.DatetimeIndex(m1.index).min().floor("1h")
    return _XAG[(_XAG.index >= start) & (_XAG.index + pd.Timedelta(hours=1) <= end)]


def make_detect(grid, c2_hours):
    def detect(m1):
        cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold",
                "fail_swing", "c2_hour"]
        # daily bias: previous complete session is a daily C2
        d = C.daily(m1).reset_index(drop=True)
        pl, ph = d["low"].shift(1), d["high"].shift(1)
        dbull = (d["low"] < pl) & (d["close"] > pl)
        dbear = (d["high"] > ph) & (d["close"] < ph)
        dmap = dict(zip(d["td"], np.where(dbull & ~dbear, 1, np.where(dbear & ~dbull, -1, 0))))
        # 4h C2s on the chosen grid
        f = cl.build_bars(m1, "4h", grid4h=grid).reset_index()
        f["td"] = cl.trading_day(f["time"])
        hi, lo = f["high"].to_numpy(float), f["low"].to_numpy(float)
        fb = (f["low"] < f["low"].shift(1)) & (f["close"] > f["low"].shift(1))
        fs = (f["high"] > f["high"].shift(1)) & (f["close"] < f["high"].shift(1))
        c2dir = np.where(fb & ~fs, 1, np.where(fs & ~fb, -1, 0))
        prev_td = C.prev_day_levels(d.set_index("td", drop=False).rename_axis(None),
                                    f["td"])["pd_td"].to_numpy()
        bias = np.array([dmap.get(pd.Timestamp(x), 0) for x in prev_td])
        hour = pd.DatetimeIndex(f["grid_open_local"]).hour.to_numpy()
        cand = np.flatnonzero((c2dir != 0) & (c2dir == bias) & np.isin(hour, c2_hours))
        if len(cand) == 0:
            return pd.DataFrame(columns=cols)
        # failure swing: C2's extreme does not exceed the extreme since the most recent
        # 4h 2/2 swing confirmed before C2 opened (p + 2 <= i - 1)
        sw = swing_points(f.set_index("time")[["open", "high", "low", "close"]], left=2, right=2)
        pos = np.arange(len(f), dtype=float)
        last_sh = pd.Series(np.where(sw["swing_high"].to_numpy(), pos, np.nan)).ffill().shift(3).to_numpy()
        last_sl = pd.Series(np.where(sw["swing_low"].to_numpy(), pos, np.nan)).ffill().shift(3).to_numpy()
        xs = xag_for(m1)
        xt = xs.index.as_unit("ns").asi8
        xh, xl = xs["high"].to_numpy(), xs["low"].to_numpy()
        st = pd.DatetimeIndex(f["time"]).as_unit("ns").asi8
        ct = pd.DatetimeIndex(f["close_time"]).as_unit("ns").asi8
        keep, fail = [], []
        for i in cand:
            dr = c2dir[i]
            p = last_sh[i] if dr == -1 else last_sl[i]
            if np.isnan(p):
                keep.append(False); fail.append(False); continue      # not evaluable -> drop
            p = int(p)
            if dr == -1:
                is_fail = hi[i] <= hi[p:i].max()
            else:
                is_fail = lo[i] >= lo[p:i].min()
            ok = True
            if is_fail:     # gold failed to take the previous high/low: require silver SMT
                a, b = np.searchsorted(xt, st[p]), np.searchsorted(xt, st[i])
                c = np.searchsorted(xt, ct[i])
                if a >= b or b >= c:
                    ok = False                                      # silver missing -> fail
                elif dr == -1:
                    ok = bool(xh[b:c].max() > xh[a:b].max())        # silver took its high
                else:
                    ok = bool(xl[b:c].min() < xl[a:b].min())        # silver took its low
            keep.append(ok); fail.append(bool(is_fail))
        keep = np.array(keep)
        cand, fail = cand[keep], np.array(fail)[keep]
        if len(cand) == 0:
            return pd.DataFrame(columns=cols)
        c3s = pd.DatetimeIndex(f["close_time"].to_numpy()[cand]).tz_convert("UTC")
        w = pd.DataFrame({"c3_start": c3s, "c3_close": c3s + H4, "dir": c2dir[cand],
                          "mid": (hi[cand] + lo[cand]) / 2, "fail": fail,
                          "hour": hour[cand]}).sort_values("c3_start").reset_index(drop=True)
        c15 = C.cisd_table(C.complete_bars(m1, "15min"))
        if c15.empty:
            return pd.DataFrame(columns=cols)
        ws = pd.DatetimeIndex(w["c3_start"]).as_unit("ns").asi8
        we = pd.DatetimeIndex(w["c3_close"]).as_unit("ns").asi8
        tt = pd.DatetimeIndex(c15["t"]).as_unit("ns").asi8
        k = np.searchsorted(ws, tt - 1, side="right") - 1          # window with start < t
        kk = np.clip(k, 0, None)
        inwin = (k >= 0) & (tt <= we[kk])
        inwin &= pd.DatetimeIndex(c15["extreme_start"]).as_unit("ns").asi8 >= ws[kk]  # intra-C3
        c = c15[inwin].assign(win=kk[inwin])
        c = c.merge(w[["dir", "mid", "fail", "hour", "c3_close"]], left_on="win",
                    right_index=True, suffixes=("", "_w"))
        good = (c["dir"] == c["dir_w"]) & np.where(c["dir"] == 1, c["extreme_price"] >= c["mid"],
                                                   c["extreme_price"] <= c["mid"])
        q = c[good].sort_values("t").groupby("win", sort=True).head(1).sort_values("t")
        t = pd.DatetimeIndex(q["t"])
        hold = (pd.DatetimeIndex(q["c3_close"]) + H4) - t        # through C3 and the next 4h
        return pd.DataFrame({"decision_time": t, "available_at": t,
                             "direction": q["dir"].astype(int).to_numpy(),
                             "stop_px": q["stop"].to_numpy(float), "rr": RR,
                             "max_hold": hold.to_numpy(),
                             "fail_swing": q["fail"].astype(bool).to_numpy(),
                             "c2_hour": q["hour"].astype(int).to_numpy()}).reset_index(drop=True)
    return detect


def run(reading):
    grid, hours = READINGS[reading]
    detect = make_detect(grid, hours)
    ev = cl.cache_frame(f"ttfm_fav_london_{reading}_{grid}_{hours[0]}_{hours[1]}_v1",
                        lambda: detect(cl.load_m1()))
    m1 = cl.load_m1()
    entry = m1["open"].reindex(pd.DatetimeIndex(ev["decision_time"]), method="bfill")
    sd = np.abs(entry.to_numpy() - ev["stop_px"].to_numpy())
    print(reading, "events", len(ev), ev["direction"].value_counts().to_dict(),
          "fail_swing", int(ev["fail_swing"].sum()), "by C2 hour", ev["c2_hour"].value_counts().to_dict(),
          "stop pt median", round(float(np.nanmedian(sd)), 2), "share<1pt", round(float(np.nanmean(sd < 1)), 3))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, claim="+", ctrl_tod_tol_min=30)
    for kx in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
               "ties", "exposure_bars", "ctrl_overlap"):
        print(" ", kx, res.get(kx))
    c2s = "21:00 or 01:00" if grid == "forex" else "22:00 or 02:00"
    rules = [
        "bias: the previous complete session (>=600 M1) is a daily C2: low < prior-day low and "
        "close > it (bull); mirror bear; two-sided skipped",
        f"4h ({grid} grid, NY, DST): a same-direction 4h C2 (low < previous 4h low, close > it; "
        f"mirror) whose candle opens at {c2s} NY (the London-model reversal candle)",
        "failure swing: the C2's extreme does not exceed the highest high (bear) / lowest low "
        "(bull) of the 4h bars since the most recent 2/2 4h swing confirmed before C2 opened; "
        "a failure-swing C2 is kept only with 4h SMT: silver (XAG H1 on gold's 4h bar span) "
        "took its own corresponding high/low during the C2 candle; missing silver = dropped",
        "inside 4h C3 (the next 4h candle): first 15m CISD in that direction, confirmed in C3, "
        "extreme formed in C3 (intra-candle CISD), extreme holding the upper (bull) / lower "
        "(bear) half of the C2 range",
        "enter next M1 open after the 15m confirm close; stop = protected swing; 2R; time exit "
        "at the close of the 4h candle after C3",
        "control: matched random entries, NY clock held within +-30 min",
        "not applied: the deep-15m-run SMT gate (needs 15m silver; 'very deep' unquantified), "
        "the daily-range-left wick allowance (eyeballed 100 pt), daily C3 bias"]
    params = {"daily_bias": "previous session daily C2", "grid4h": grid,
              "c2_open_hours_ny": list(hours), "h4_c2": "sweep previous 4h extreme, close back inside",
              "failure_swing": "C2 extreme not beyond the 4h extreme since the last confirmed 2/2 swing",
              "smt": "XAG_USD H1 aggregated to gold 4h bar spans; silver takes its reference extreme",
              "half_rule": "15m CISD extreme holds the upper (bull) / lower (bear) half of the 4h C2",
              "cisd": "15m, series_open, swing 2/2, max_wait 3; first per 4h C3, extreme in C3",
              "rr": RR, "max_hold": "per-row: until the close of the 4h candle after C3",
              "ctrl_tod_tol_min": 30}
    src = {"daily_bias": "corpus: tUbrCewFdCU 'using a candle two or a candle three closure' "
                         "(C2 kept as in the library reading; C3 not part of the new claim)",
           "grid4h": ("corpus: tUbrCewFdCU 'the timings will be off by an hour due to their "
                      "higher time frame opens'; session_window_fit: forex grid for gold, knob "
                      "recorded") if grid == "forex" else
                     ("corpus: tUbrCewFdCU 'usually the 2200 candle or the 2:00 a.m. candle' "
                      "(literal futures grid); phase3: 4H grid is a knob"),
           "c2_open_hours_ny": "corpus: tUbrCewFdCU 'usually the 2200 candle or the 2:00 a.m. "
                               "candle' (forex = one hour earlier)",
           "h4_c2": "corpus: tUbrCewFdCU 'swept out its previous candle and then close below'",
           "failure_swing": "corpus: tUbrCewFdCU 'it did fail to take out this previous high'; "
                            "phase3: locked 2/2 swing",
           "smt": "corpus: tUbrCewFdCU 'I would prefer there to be SMT here'; correlate held at "
                  "H1 only (smt-divergence u1007a precedent)",
           "half_rule": "corpus: zJLaABC_hM8 'The lower half of this 4-hour candle' (library reading)",
           "cisd": "phase3: locked CISD config; corpus: tUbrCewFdCU 'waiting for the intra-candle "
                   "change in the state of delivery'",
           "rr": "corpus: tUbrCewFdCU 'Right there we hit our 2R'",
           "max_hold": "corpus: tUbrCewFdCU 'hold this for the duration of this higher time "
                       "frame candle and potentially even the next'",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9; events are confined by "
                               "construction to the 01:00-13:00 NY C3/C4 span, and the source "
                               "puts the edge in the HTF wick alignment, not the clock ('I "
                               "don't really care too much about kill zones')"}
    p = cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes=f"London-window + 4h failure-swing SMT version of the library "
                              f"reading (ttfm-favorite-daily-4h-15m.json, UNDERPOWERED n=242). "
                              f"Events {len(ev)}, failure-swing C2s kept with SMT "
                              f"{int(ev['fail_swing'].sum())}; median stop "
                              f"{float(np.nanmedian(sd)):.2f} pt, {float(np.nanmean(sd < 1)):.1%} "
                              f"under 1 pt. Control matches stop distance, not placement at a "
                              f"fresh extreme (campaign lesson 1). Deep-15m-run SMT not applied "
                              f"(no 15m silver).")
    print("wrote", p)


if __name__ == "__main__":
    for r in (sys.argv[1:] or list(READINGS)):
        run(r)
