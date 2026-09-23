"""internal-external-liquidity-model — trade test of the daily / hourly / 5-minute model.

Stated model (mwmWNCTEYtY): HTF level -> one TF down the internal/external rotation gives
the draw -> on the execution TF require, in order, kill zone, stop raid, market structure
shift, fair value gap; enter at the FVG; stop over the opposing candles; fixed 2R.

Operationalisation (his preferred daily / hourly / 5-minute ladder):
  HTF level  = previous day low (bull) / previous day high (bear) — 'previous period
               high/low' from the preconditions. (A daily FVG below price can only be reached
               after PDL is taken, so PDL/PDH is the first HTF level price meets.)
  draw       = the rotation away from swept external liquidity (sell-side taken -> draw up).
  kill zone  = the raid bar starts inside forex London 02:00-05:00 or NY AM 07:00-10:00 NY.
  stop raid  = a 5m bar makes a new low of the day BELOW the PDL (deeper new lows inside the
               kill zone re-arm the raid at the new extreme).
  MSS        = within 12 5m bars (60 min) of the raid low, a 5m CLOSE above the most recent
               2/2 swing high confirmed before the raid low; a lower low first re-arms.
  FVG        = the latest bullish 5m FVG whose middle bar lies in (raid, MSS) and whose
               third bar is at or before the MSS bar (known at the MSS close).
  entry      = first M1 bar trading back to the FVG's top ('start of the gap') within 60 min
               after the FVG is known; decide at that M1 close, enter next M1 open.
  stop       = the raid low (the opposing candles' extreme); target 2R; hold to the daily
               candle close. First setup per side per day (the MSS consumes the day's raid).
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from _common import in_progress, utc  # noqa: E402

CID = "internal-external-liquidity-model"
MSS_MAX_BARS = 12
ENTRY_WAIT_MIN = 60
KZ = ("fx_london", "fx_ny_am")


def _bull_setups(o, h, l, c, day, pdl, in_kz, m1_low, m1_start, b5_close, b5_start):
    """Bullish setups on (possibly negated) arrays. Returns list of
    (decision_ns, stop, day_pos)."""
    n = len(h)
    # 2/2 swing highs, known at close of bar s+2
    sh = np.zeros(n, bool)
    for s in range(2, n - 2):
        if h[s] > h[s - 1] and h[s] > h[s - 2] and h[s] > h[s + 1] and h[s] > h[s + 2]:
            sh[s] = True
    out = []
    cur_day = -2
    run_lo = np.inf
    armed = False
    done = False
    last_sh = -1          # most recent swing high index confirmed by the current bar
    L = Lpos = ref = None
    for i in range(n):
        if i - 2 >= 0 and sh[i - 2]:
            last_sh = i - 2
        if day[i] != cur_day:
            cur_day, run_lo, armed, done = day[i], np.inf, False, False
        if day[i] < 1 or np.isnan(pdl[i]):
            run_lo = min(run_lo, l[i])
            continue
        if not done:
            newlow = l[i] < run_lo and l[i] < pdl[i]
            if newlow:
                if in_kz[i]:
                    # raid (or deeper raid): swing high confirmed before this bar
                    cand = last_sh if last_sh < i else -1
                    if cand >= 0:
                        armed, L, Lpos, ref = True, l[i], i, h[cand]
                    else:
                        armed = False
                else:
                    armed = False
            elif armed and (i - Lpos) > MSS_MAX_BARS:
                armed = False
            elif armed and c[i] > ref:
                # MSS at i: latest bullish FVG with middle bar in (Lpos, i], third <= i+1
                fv = None
                for k in range(i - 1, Lpos, -1):          # third bar k+1 <= i: known now
                    if l[k + 1] > h[k - 1]:
                        fv = (k, h[k - 1])
                        break
                done = True
                armed = False
                if fv is not None:
                    k, top = fv
                    known = b5_close[i]
                    a = np.searchsorted(m1_start, known, side="left")
                    lim = known + np.int64(ENTRY_WAIT_MIN) * 60_000_000_000
                    bnd = np.searchsorted(m1_start, lim, side="left")
                    hit = np.flatnonzero(m1_low[a:bnd] <= top)
                    if len(hit):
                        q = a + hit[0]
                        out.append((m1_start[q] + 60_000_000_000, L, day[i]))
        run_lo = min(run_lo, l[i])
    return out


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold"]
    b5 = cl.build_bars(m1, "5min")
    bd = cl.build_bars(m1, "1D")
    if len(b5) < 10 or len(bd) < 2:
        return pd.DataFrame(columns=cols)
    st5 = utc(b5.index)
    day = in_progress(bd, st5)
    dc = np.clip(day, 1, None)
    pdl = np.where(day >= 1, bd["low"].to_numpy()[dc - 1], np.nan)
    pdh = np.where(day >= 1, bd["high"].to_numpy()[dc - 1], np.nan)
    in_kz = np.zeros(len(b5), bool)
    for z in KZ:
        in_kz |= cl.in_window(st5, *cl.KILLZONES[z])
    o, h, l, c = (b5[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    b5_close = cl.data.utc_ns(utc(b5["close_time"].to_numpy())).astype("int64")
    b5_start = cl.data.utc_ns(st5).astype("int64")
    m1_start = cl.data.utc_ns(utc(m1.index)).astype("int64")
    rows = []
    for sgn in (1, -1):
        if sgn > 0:
            args = (o, h, l, c, day, pdl, in_kz, m1["low"].to_numpy(float))
        else:
            args = (-o, -l, -h, -c, day, -pdh, in_kz, -m1["high"].to_numpy(float))
        for dec, stop, dpos in _bull_setups(*args, m1_start, b5_close, b5_start):
            rows.append((dec, sgn, sgn * stop, dpos))
    if not rows:
        return pd.DataFrame(columns=cols)
    r = pd.DataFrame(rows, columns=["dec", "direction", "stop_px", "dpos"])
    t = pd.DatetimeIndex(pd.to_datetime(r["dec"].to_numpy(), utc=True))
    dclose = utc(bd["close_time"].to_numpy())[r["dpos"].to_numpy()]
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": r["direction"].to_numpy(),
                        "stop_px": r["stop_px"].to_numpy(), "rr": 2.0,
                        "max_hold": pd.Series(dclose - t).to_numpy()})
    out = out[out["max_hold"] > pd.Timedelta(0)]
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    ev = cl.cache_frame("ielm_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev)
    print({k: res.get(k) for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p",
                                    "verdict", "verdict_detail", "exposure_bars", "ties")})
    op = {"rules": [
        "ladder daily / hourly / 5-minute; daily = 18:00 NY trading day",
        "HTF level: previous day low (bull) / high (bear); draw = rotation away from the swept "
        "external liquidity",
        "kill zone: raid 5m bar starts in forex London 02:00-05:00 or NY AM 07:00-10:00 NY",
        "stop raid: 5m bar makes a new day low below PDL (mirror); deeper lows in the kill zone "
        "re-arm at the new extreme; a new low outside the kill zone disarms",
        "MSS: within 12 5m bars of the raid low, a 5m close above the latest 2/2 swing high "
        "confirmed before the raid bar",
        "FVG: latest bullish 5m FVG with middle bar after the raid bar and third bar <= the MSS bar",
        "entry: first M1 bar trading back to the FVG top within 60 min of the FVG being known; "
        "decide at that M1 close; enter next M1 open",
        "stop: raid low; target 2R fixed; hold to the daily candle close; one setup per side "
        "per day (the first MSS consumes it)"],
        "params": {"exec_tf": "5min", "killzones": "fx_london 02-05, fx_ny_am 07-10 NY",
                   "htf_level": "PDH/PDL", "mss_max_bars": MSS_MAX_BARS, "swing": "2/2",
                   "fvg_entry": "gap start (top for bull)", "entry_wait_min": ENTRY_WAIT_MIN,
                   "rr": 2.0, "max_hold": "to daily close", "one_per_side_day": True,
                   "day_open_hour": 18}}
    src = {"exec_tf": "corpus: mwmWNCTEYtY 'I personally prefer a daily hour and 5 minute setups'",
           "killzones": "session_window_fit: killzones.yaml forex London / NY AM windows "
                        "(the video uses London and New York)",
           "htf_level": "corpus: mwmWNCTEYtY preconditions 'previous period high/low'",
           "mss_max_bars": "declared-before-run: a V-shape MSS within one hour of the raid "
                           "(method_spec §4.2 'fast V-shape')",
           "swing": "method_spec: §1.1 three-candle fractal; phase3 2/2",
           "fvg_entry": "corpus: mwmWNCTEYtY 'enter at the fair value gap (start of the gap)'",
           "entry_wait_min": "declared-before-run: retrace into the FVG within 60 minutes",
           "rr": "corpus: mwmWNCTEYtY 'then I will Target to R' (2R fixed)",
           "max_hold": "method_spec: §5.5 time-based exit at the HTF (daily) candle close",
           "one_per_side_day": "declared-before-run: the first MSS after a raid consumes it",
           "day_open_hour": "method_spec: §1.4 18:00 canon"}
    print("wrote", cl.write_result(CID, None, res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe,
                                   notes="trade_test vs matched random entries."))


if __name__ == "__main__":
    main()
