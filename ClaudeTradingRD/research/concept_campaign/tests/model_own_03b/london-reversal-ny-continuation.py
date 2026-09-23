"""london-reversal-ny-continuation — A+ setup: daily C3 + London reversal + 15m New
York continuation entered before the 09:30 open, stop beyond the London-reversal
swing, target the previous day's extreme.

Reading a: daily C3 only (yesterday was a daily C2 closure in the bias direction).
Reading b: daily C3 or C4 (C4 = yesterday was a C3 that closed beyond the C2's
           extreme in the bias direction) — definition 1 allows "candle 3 or candle 4".
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

CID = "london-reversal-ny-continuation"
LONDON = ("02:00", "05:00")
ENTRY_WIN = ("06:00", "09:30")
TF, MAXW = "15min", 3


def _daily_bias(m1):
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= 600].copy()        # skip stub sessions
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    ph, pl = h.shift(1), l.shift(1)
    bull = (l < pl) & (c > pl)
    bear = (h > ph) & (c < ph)
    c2 = pd.Series(0, index=d.index)
    c2[bull & ~bear] = 1
    c2[bear & ~bull] = -1
    d["c2"] = c2
    # C3 that "closes well": day after a C2, closing beyond the C2's extreme
    prev_c2 = c2.shift(1).fillna(0)
    c3good = pd.Series(0, index=d.index)
    c3good[(prev_c2 == 1) & (c > ph)] = 1
    c3good[(prev_c2 == -1) & (c < pl)] = -1
    d["c3good"] = c3good
    return d


def detect(m1, allow_c4):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    d = _daily_bias(m1)
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=MAXW, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    inwin = cl.in_window(close, *ENTRY_WIN)
    ev = ev[inwin].reset_index(drop=True)
    close = close[inwin]
    y = cl.asof(d, close)                  # yesterday = last completed session
    bias = y["c2"].to_numpy(dtype=float)
    if allow_c4:
        bias = np.where(bias != 0, bias, y["c3good"].to_numpy(dtype=float))
    bias = np.nan_to_num(bias)
    # today's intraday bars
    bb = b.copy()
    bb["tday"] = cl.trading_day(bb.index)
    bb["in_lon"] = cl.in_window(bb.index, *LONDON)     # bar START inside 02:00-05:00
    rows = []
    tday_ev = cl.trading_day(pd.DatetimeIndex(ev["confirm_time"]))
    for i, r in ev.iterrows():
        dirn = 1 if r["direction"] == "bullish" else -1
        if bias[i] != dirn:
            continue
        # yesterday must be the session right before today
        td = tday_ev[i]
        if pd.isna(y["trading_day"].iloc[i]):
            continue
        day = bb[(bb["tday"] == td) & (bb.index <= r["confirm_time"])]
        lon = day[day["in_lon"]]
        if len(lon) < 10:
            continue
        if dirn == 1:
            lon_ext = lon["low"].min()
            ok = day["low"].min() >= lon_ext and r["protected_swing"] > lon_ext
            tgt = float(y["high"].iloc[i])
            ok = ok and tgt > r["confirm_close"]
        else:
            lon_ext = lon["high"].max()
            ok = day["high"].max() <= lon_ext and r["protected_swing"] < lon_ext
            tgt = float(y["low"].iloc[i])
            ok = ok and tgt < r["confirm_close"]
        if not ok:
            continue
        t = close[i]
        loc = t.tz_convert("America/New_York")
        end = (loc.normalize() + pd.Timedelta(hours=17)).tz_convert("UTC")
        rows.append({"decision_time": t, "available_at": t, "direction": dirn,
                     "stop_px": float(r["protected_swing"]), "target_px": tgt,
                     "max_hold": end - t, "tday": td})
    out = pd.DataFrame(rows, columns=cols + ["tday"])
    out = out.drop_duplicates("tday", keep="first").drop(columns="tday").reset_index(drop=True)
    out["max_hold"] = pd.to_timedelta(out["max_hold"])
    return out


def detect_a(m1):
    return detect(m1, False)


def detect_b(m1):
    return detect(m1, True)


RULES = [
    "daily bars roll 18:00 NY; stub sessions (<600 M1 bars) skipped",
    "daily C2 closure: bull = low < prior low and close > prior low; bear mirror; two-sided = none",
    "London window 02:00-05:00 NY (bar start inside); London extreme = London low (bull) / high (bear)",
    "at decision the day's extreme so far (since 18:00) is still the London extreme (London formed the reversal)",
    "entry trigger: a 15m CISD (series_open, 2/2 swing, max_wait 3) in the bias direction whose confirming bar closes 06:00-09:30 NY and whose protected swing is a higher low (bull) than the London low (a continuation, not the reversal itself)",
    "enter next M1 open; stop at the protected swing; target the previous day's high (bull) / low (bear), skipped if already beyond it; exit at 17:00 NY; first qualifying event per day",
]
PARAMS = {"london_window": "02:00-05:00", "entry_window": "06:00-09:30", "entry_tf": TF,
          "cisd": "series_open 2/2 max_wait 3", "target": "previous day high/low",
          "max_hold": "to 17:00 NY same day"}
SRC = {"london_window": "method_spec: §2.5 daily-profile-session-windows London 02:00-05:00",
       "entry_window": "corpus: N3Ml-r0X30o 'London reversal and 15 continuation prior to NYSE open'; 06:00 start of the stated expansion window",
       "entry_tf": "corpus: N3Ml-r0X30o '15 continuation'",
       "cisd": "phase3: locked bare-CISD config",
       "target": "corpus: execution.targets 'previous day low / high'",
       "max_hold": "declared-before-run: intraday setup, flat by the 17:00 NY halt"}


def run(reading, fn, key, c4):
    ev = cl.cache_frame(key, lambda: fn(cl.load_m1()))
    print(reading, len(ev))
    probe = cl.probe_lookahead(fn, ev, lookback="10D")
    res = cl.trade_test(ev, claim="+")
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties")})
    rules = RULES + (["bias day = C3 (yesterday a C2 closure) OR C4 (yesterday a C3 closing beyond the C2 extreme)"] if c4
                     else ["bias day = C3 only: yesterday was a daily C2 closure in the bias direction"])
    params = {**PARAMS, "bias_days": "C3+C4" if c4 else "C3"}
    src = {**SRC, "bias_days": ("corpus: N3Ml-r0X30o definition 'daily candle 3 or candle 4'" if c4
                                else "corpus: 00iZXPAdR5A 'Candle three on the daily, London forms a reversal'")}
    print(cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                          params_source=src, script=__file__, probe=probe,
                          notes="SMT and the hourly CISD on the daily C2 are not required (no correlated series)."))


def main():
    run("a", detect_a, "lrnc_a_v1", False)
    run("b", detect_b, "lrnc_b_v1", True)


if __name__ == "__main__":
    main()
